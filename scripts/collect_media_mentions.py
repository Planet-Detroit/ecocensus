#!/usr/bin/env python3
"""
Media Mentions Collector for ECOcensus Project
Collects media mentions using Claude API with web search and stores in Supabase.

Improvements:
- Google News search for broader coverage
- Prioritizes orgs with EINs (larger, more newsworthy)
- Better deduplication
- Resume capability with --offset
- Verbose mode for debugging
"""

import json
import time
import re
import argparse
import requests
from datetime import datetime
from typing import List, Dict, Optional
import anthropic
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Michigan media outlets to search (specific outlets)
# NOTE: 'url' must match the exact value in Supabase outlets table
# 'domain' is used for filtering search results
MICHIGAN_OUTLETS = [
    {"name": "Bridge Michigan", "url": "https://www.bridgemi.com", "domain": "bridgemi.com", "outlet_type": "Nonprofit News"},
    {"name": "Detroit Free Press", "url": "https://www.freep.com", "domain": "freep.com", "outlet_type": "Daily Newspaper"},
    {"name": "The Detroit News", "url": "https://www.detroitnews.com", "domain": "detroitnews.com", "outlet_type": "Daily Newspaper"},
    {"name": "MLive", "url": "mlive.com", "domain": "mlive.com", "outlet_type": "News Website"},
    {"name": "Michigan Radio", "url": "https://www.michiganradio.org", "domain": "michiganradio.org", "outlet_type": "Public Radio"},
    {"name": "Crain's Detroit Business", "url": "https://www.crainsdetroit.com", "domain": "crainsdetroit.com", "outlet_type": "Business News"},
    {"name": "Planet Detroit", "url": "https://www.planetdetroit.org", "domain": "planetdetroit.org", "outlet_type": "Environmental News"},
    {"name": "Michigan Advance", "url": "michiganadvance.com", "domain": "michiganadvance.com", "outlet_type": "News Website"},
    {"name": "Detroit Metro Times", "url": "metrotimes.com", "domain": "metrotimes.com", "outlet_type": "Alternative Weekly"},
    {"name": "WDET", "url": "wdet.org", "domain": "wdet.org", "outlet_type": "Public Radio"},
    {"name": "Interlochen Public Radio", "url": "interlochenpublicradio.org", "domain": "interlochenpublicradio.org", "outlet_type": "Public Radio"},
    {"name": "Great Lakes Now", "url": "greatlakesnow.org", "domain": "greatlakesnow.org", "outlet_type": "Environmental News"},
]

# Google News as a catch-all source
GOOGLE_NEWS = {"name": "Google News", "domain": "news.google.com", "outlet_type": "Aggregator"}


class SupabaseClient:
    """Simple Supabase REST client."""

    def __init__(self):
        self.url = os.getenv("VITE_SUPABASE_URL")
        self.key = os.getenv("VITE_SUPABASE_ANON_KEY")
        if not self.url or not self.key:
            raise ValueError("Supabase credentials not found in .env file")
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def select(self, table: str, columns: str = "*", filters: Dict = None, limit: int = None, offset: int = None, order: str = None) -> List[Dict]:
        """Select from a table."""
        url = f"{self.url}/rest/v1/{table}?select={columns}"
        if order:
            url += f"&order={order}"
        if limit:
            url += f"&limit={limit}"
        if offset:
            url += f"&offset={offset}"
        if filters:
            for key, value in filters.items():
                url += f"&{key}=eq.{value}"

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def select_not_null(self, table: str, columns: str, field: str, limit: int = None, offset: int = None, order: str = None) -> List[Dict]:
        """Select from a table where a field is not null."""
        url = f"{self.url}/rest/v1/{table}?select={columns}&{field}=not.is.null"
        if order:
            url += f"&order={order}"
        if limit:
            url += f"&limit={limit}"
        if offset:
            url += f"&offset={offset}"

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def insert(self, table: str, data: Dict) -> Optional[Dict]:
        """Insert into a table."""
        url = f"{self.url}/rest/v1/{table}"
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code in (200, 201):
            result = response.json()
            return result[0] if result else None
        elif response.status_code == 409:
            # Duplicate
            return None
        else:
            response.raise_for_status()
            return None


class MediaMentionsCollector:
    """Collects media mentions using Claude with web search and stores in Supabase."""

    def __init__(self, verbose: bool = False, include_google: bool = True):
        self.verbose = verbose
        self.include_google = include_google

        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in .env file")
        self.client = anthropic.Anthropic(api_key=api_key)

        # Initialize Supabase client
        self.db = SupabaseClient()

        # Cache for outlet IDs
        self.outlet_ids: Dict[str, int] = {}

        # Build outlet list
        self.outlets = MICHIGAN_OUTLETS.copy()
        if include_google:
            self.outlets.append(GOOGLE_NEWS)

        # Statistics
        self.stats = {
            "orgs_processed": 0,
            "mentions_found": 0,
            "mentions_inserted": 0,
            "duplicates_skipped": 0,
            "errors": 0
        }

    def ensure_outlets_exist(self) -> None:
        """Ensure all outlets exist in database and cache their IDs."""
        print("Checking outlets table...")

        for outlet in self.outlets:
            # Check if outlet exists (use 'url' field to match Supabase)
            try:
                result = self.db.select("outlets", "id", {"url": outlet["url"]})
                if result:
                    self.outlet_ids[outlet["domain"]] = result[0]["id"]
                    print(f"  ✓ Found: {outlet['name']} (id={result[0]['id']})")
                else:
                    # Insert new outlet
                    insert_result = self.db.insert("outlets", {
                        "name": outlet["name"],
                        "url": outlet["url"],
                        "outlet_type": outlet["outlet_type"]
                    })
                    if insert_result:
                        self.outlet_ids[outlet["domain"]] = insert_result["id"]
                        print(f"  + Created: {outlet['name']} (id={insert_result['id']})")
                    else:
                        print(f"  ✗ Failed to create: {outlet['name']}")
            except Exception as e:
                print(f"  ✗ Error with {outlet['name']}: {e}")

    def get_organizations(self, limit: Optional[int] = None, offset: int = 0, prioritize_ein: bool = True) -> List[Dict]:
        """Fetch organizations from Supabase, optionally prioritizing those with EINs."""
        if prioritize_ein:
            # Get orgs with EINs first (larger, more likely to have media coverage)
            return self.db.select_not_null("organizations", "id,name,slug,ein", "ein", limit=limit, offset=offset, order="name")
        else:
            return self.db.select("organizations", "id,name,slug", limit=limit, offset=offset, order="name")

    def get_existing_urls(self, org_id: str) -> set:
        """Get existing article URLs for an organization to avoid duplicates."""
        try:
            result = self.db.select("media_mentions", "article_url", {"organization_id": org_id})
            return {row["article_url"] for row in result} if result else set()
        except:
            return set()

    def get_all_existing_urls(self) -> set:
        """Get ALL existing article URLs to avoid duplicates across orgs."""
        try:
            result = self.db.select("media_mentions", "article_url")
            return {row["article_url"] for row in result} if result else set()
        except:
            return set()

    def search_org_in_outlet(self, org_name: str, outlet: Dict) -> List[Dict]:
        """Search for an organization in a specific outlet using Claude web search."""

        print(f"    Searching {outlet['name']}...", end=" ", flush=True)

        # Special handling for Google News - broader search
        if outlet["domain"] == "news.google.com":
            search_prompt = f"""Search Google News for recent news articles about "{org_name}" Michigan nonprofit.

Find up to 5 recent articles (from 2023-2026) that specifically mention this organization. For each article found, extract:
1. Article headline/title
2. Article URL (the actual news source URL, not the Google News URL)
3. Publication date (if available)
4. Brief excerpt mentioning the organization (1-2 sentences max)

Return ONLY a JSON array with this structure:
[
  {{
    "headline": "Article title",
    "url": "https://...",
    "published_date": "YYYY-MM-DD or null",
    "excerpt": "Brief excerpt..."
  }}
]

If no articles found, return empty array: []
Only include articles that specifically mention "{org_name}" by name."""
        else:
            search_prompt = f"""Search for news articles about "{org_name}" on {outlet['name']} ({outlet['domain']}).

Find up to 5 recent articles (from 2023-2026) that mention this organization. For each article found, extract:
1. Article headline/title
2. Article URL (must be from {outlet['domain']})
3. Publication date (if available)
4. Brief excerpt mentioning the organization (1-2 sentences max)

Return ONLY a JSON array with this structure:
[
  {{
    "headline": "Article title",
    "url": "https://...",
    "published_date": "YYYY-MM-DD or null",
    "excerpt": "Brief excerpt..."
  }}
]

If no articles found, return empty array: []
Do not include articles from other websites."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{
                    "role": "user",
                    "content": search_prompt
                }]
            )

            result_text = ""
            for block in response.content:
                if block.type == "text":
                    result_text += block.text

            if self.verbose:
                print(f"\n      Raw response: {result_text[:200]}...")

            json_match = re.search(r'\[[\s\S]*?\]', result_text)
            if json_match:
                articles = json.loads(json_match.group(0))
                # Filter to only include URLs from the correct domain (skip for Google News)
                if outlet["domain"] == "news.google.com":
                    valid_articles = articles  # Accept all URLs from Google News search
                else:
                    valid_articles = [a for a in articles if outlet['domain'] in a.get('url', '')]
                print(f"found {len(valid_articles)}")
                return valid_articles
            else:
                print("no results")
                return []

        except Exception as e:
            print(f"error: {e}")
            self.stats["errors"] += 1
            return []

    def save_mention_to_db(self, org_id: str, outlet_domain: str, article: Dict) -> bool:
        """Save a single mention to Supabase. Returns True if inserted, False if duplicate."""

        outlet_id = self.outlet_ids.get(outlet_domain)

        # For Google News results, try to match to a known outlet or use Google News ID
        if not outlet_id and outlet_domain == "news.google.com":
            # Try to find matching outlet from URL
            article_url = article.get("url", "")
            for domain, oid in self.outlet_ids.items():
                if domain in article_url:
                    outlet_id = oid
                    break
            # Fall back to Google News outlet
            if not outlet_id:
                outlet_id = self.outlet_ids.get("news.google.com")

        if not outlet_id:
            if self.verbose:
                print(f"      No outlet ID for {outlet_domain}")
            return False

        # Parse date
        published_date = None
        if article.get("published_date"):
            date_str = article["published_date"]
            if date_str and date_str != "null":
                published_date = date_str

        try:
            result = self.db.insert("media_mentions", {
                "organization_id": org_id,
                "outlet_id": outlet_id,
                "article_url": article.get("url", ""),
                "headline": article.get("headline", ""),
                "published_date": published_date,
                "excerpt": article.get("excerpt", ""),
                "mention_type": "mention"
            })
            return result is not None
        except Exception as e:
            if "duplicate" not in str(e).lower():
                print(f"      DB error: {e}")
                self.stats["errors"] += 1
            return False

    def collect_for_org(self, org: Dict, global_urls: set) -> int:
        """Collect media mentions for one organization across all outlets."""

        print(f"\n  {org['name']}")
        if org.get('ein'):
            print(f"  EIN: {org['ein']}")
        print(f"  {'-' * len(org['name'])}")

        # Get existing URLs for this org
        existing_urls = self.get_existing_urls(org["id"])
        # Combine with global URLs for deduplication
        all_known_urls = existing_urls | global_urls

        org_mentions = 0

        for outlet in self.outlets:
            articles = self.search_org_in_outlet(org["name"], outlet)

            for article in articles:
                url = article.get("url", "")

                # Normalize URL for comparison (remove trailing slashes, http vs https)
                normalized_url = url.rstrip('/').replace('http://', 'https://')

                # Skip if URL already exists (check normalized version too)
                if url in all_known_urls or normalized_url in all_known_urls:
                    self.stats["duplicates_skipped"] += 1
                    if self.verbose:
                        print(f"      (dup) {article.get('headline', 'No title')[:40]}...")
                    continue

                # Save to database
                if self.save_mention_to_db(org["id"], outlet["domain"], article):
                    self.stats["mentions_inserted"] += 1
                    org_mentions += 1
                    all_known_urls.add(url)
                    all_known_urls.add(normalized_url)
                    global_urls.add(url)  # Add to global set for cross-org deduplication
                    print(f"      + {article.get('headline', 'No title')[:55]}...")

            # Rate limiting
            time.sleep(1.5)

        self.stats["mentions_found"] += org_mentions
        return org_mentions

    def collect_all(self, limit: Optional[int] = None, offset: int = 0, prioritize_ein: bool = True) -> None:
        """Collect mentions for organizations."""

        print("\n" + "=" * 70)
        print("ECOCENSUS MEDIA MENTIONS COLLECTOR")
        print("=" * 70)
        print(f"Google News search: {'enabled' if self.include_google else 'disabled'}")
        print(f"Prioritize orgs with EIN: {'yes' if prioritize_ein else 'no'}")

        # Ensure outlets exist
        self.ensure_outlets_exist()

        # Load all existing URLs for global deduplication
        print("\nLoading existing URLs for deduplication...")
        global_urls = self.get_all_existing_urls()
        print(f"Found {len(global_urls)} existing URLs")

        # Get organizations
        print("\nFetching organizations...")
        orgs = self.get_organizations(limit=limit, offset=offset, prioritize_ein=prioritize_ein)
        print(f"Found {len(orgs)} organizations to process")

        if not orgs:
            print("No organizations found!")
            return

        print(f"Outlets: {len(self.outlets)}")
        print(f"Max API calls: {len(orgs) * len(self.outlets)}")
        print("=" * 70)

        for i, org in enumerate(orgs, 1):
            print(f"\n[{i}/{len(orgs)}]", end="")
            mentions = self.collect_for_org(org, global_urls)
            self.stats["orgs_processed"] += 1

            # Longer pause between organizations
            if i < len(orgs):
                time.sleep(3)

        self.print_summary()

    def print_summary(self) -> None:
        """Print collection summary."""
        print("\n" + "=" * 70)
        print("COLLECTION COMPLETE")
        print("=" * 70)
        print(f"Organizations processed: {self.stats['orgs_processed']}")
        print(f"Mentions found:          {self.stats['mentions_found']}")
        print(f"Mentions inserted:       {self.stats['mentions_inserted']}")
        print(f"Duplicates skipped:      {self.stats['duplicates_skipped']}")
        print(f"Errors:                  {self.stats['errors']}")
        print("=" * 70)


def main():
    """Main execution with CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Collect media mentions for ECOcensus organizations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python collect_media_mentions.py --test          # Test with 3 orgs
  python collect_media_mentions.py --limit 10      # Process first 10 orgs
  python collect_media_mentions.py --offset 50 --limit 20  # Process orgs 51-70
  python collect_media_mentions.py --no-google     # Skip Google News search
  python collect_media_mentions.py --all-orgs      # Include orgs without EINs
        """
    )
    parser.add_argument("--limit", type=int, help="Number of organizations to process")
    parser.add_argument("--offset", type=int, default=0, help="Starting offset (skip first N orgs)")
    parser.add_argument("--test", action="store_true", help="Test mode: process only 3 organizations")
    parser.add_argument("--no-google", action="store_true", help="Skip Google News search (faster)")
    parser.add_argument("--all-orgs", action="store_true", help="Include orgs without EINs (default: EIN-only)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output for debugging")

    args = parser.parse_args()

    limit = 3 if args.test else args.limit
    include_google = not args.no_google
    prioritize_ein = not args.all_orgs

    try:
        collector = MediaMentionsCollector(verbose=args.verbose, include_google=include_google)
        collector.collect_all(limit=limit, offset=args.offset, prioritize_ein=prioritize_ein)

    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nRequired environment variables:")
        print("  ANTHROPIC_API_KEY - Claude API key")
        print("  VITE_SUPABASE_URL - Supabase project URL")
        print("  VITE_SUPABASE_ANON_KEY - Supabase anon key")


if __name__ == "__main__":
    main()
