#!/usr/bin/env python3
"""
Media Mentions Collector using GDELT API
Fast, free, no rate limits - searches global news archive.
"""

import json
import time
import argparse
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote
import os
from dotenv import load_dotenv

load_dotenv()

# Michigan-focused domains to prioritize
MICHIGAN_DOMAINS = [
    "bridgemi.com", "freep.com", "detroitnews.com", "mlive.com",
    "michiganradio.org", "crainsdetroit.com", "planetdetroit.org",
    "michiganadvance.com", "metrotimes.com", "wdet.org",
    "interlochenpublicradio.org", "greatlakesnow.org"
]


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
            return None
        else:
            response.raise_for_status()
            return None


class GDELTCollector:
    """Collects media mentions using GDELT DOC 2.0 API."""

    GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.db = SupabaseClient()
        self.outlet_ids: Dict[str, int] = {}
        self.stats = {
            "orgs_processed": 0,
            "mentions_found": 0,
            "mentions_inserted": 0,
            "duplicates_skipped": 0,
            "errors": 0
        }

    def load_outlets(self) -> None:
        """Load outlet IDs from database."""
        print("Loading outlets...")
        try:
            outlets = self.db.select("outlets", "id,url,name")
            for outlet in outlets:
                # Extract domain from URL
                url = outlet["url"]
                domain = url.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
                self.outlet_ids[domain] = outlet["id"]
                if self.verbose:
                    print(f"  {domain} -> {outlet['id']}")
            print(f"  Loaded {len(self.outlet_ids)} outlets")
        except Exception as e:
            print(f"  Error loading outlets: {e}")

    def get_organizations(self, limit: Optional[int] = None, offset: int = 0, prioritize_ein: bool = True) -> List[Dict]:
        """Fetch organizations from Supabase."""
        if prioritize_ein:
            return self.db.select_not_null("organizations", "id,name,slug,ein", "ein", limit=limit, offset=offset, order="name")
        else:
            return self.db.select("organizations", "id,name,slug", limit=limit, offset=offset, order="name")

    def get_all_existing_urls(self) -> set:
        """Get ALL existing article URLs to avoid duplicates."""
        try:
            result = self.db.select("media_mentions", "article_url")
            return {row["article_url"] for row in result} if result else set()
        except:
            return set()

    def search_gdelt(self, org_name: str, max_records: int = 50, max_retries: int = 5) -> List[Dict]:
        """Search GDELT for articles mentioning an organization."""

        # Build query - search for org name in Michigan context
        query = f'"{org_name}" Michigan'

        params = {
            "query": query,
            "mode": "ArtList",
            "maxrecords": max_records,
            "format": "json",
            "sort": "DateDesc"
        }

        for attempt in range(max_retries):
            try:
                response = requests.get(self.GDELT_API, params=params, timeout=30)

                if self.verbose:
                    print(f"      Status: {response.status_code}, Length: {len(response.text)}")

                if response.status_code == 429:
                    wait_time = 10 * (attempt + 1)  # 10s, 20s, 30s, 40s, 50s
                    print(f"(rate limit, wait {wait_time}s)", end=" ", flush=True)
                    time.sleep(wait_time)
                    continue

                if response.status_code != 200:
                    print(f"(HTTP {response.status_code})", end=" ")
                    return []

                # Handle empty response
                if not response.text or response.text.strip() == "":
                    return []

                data = response.json()
                articles = data.get("articles", [])

                return articles

            except requests.exceptions.Timeout:
                print("(timeout)", end=" ")
                return []
            except json.JSONDecodeError as e:
                if self.verbose:
                    print(f"      JSON error: {e}")
                    print(f"      Response: {response.text[:200]}")
                return []
            except Exception as e:
                print(f"(error: {e})", end=" ")
                self.stats["errors"] += 1
                return []

        print("(gave up)", end=" ")
        return []

    def get_outlet_id_for_url(self, url: str) -> Optional[int]:
        """Try to match URL to a known outlet."""
        url_lower = url.lower()
        for domain, outlet_id in self.outlet_ids.items():
            if domain in url_lower:
                return outlet_id
        return None

    def save_mention_to_db(self, org_id: str, article: Dict, outlet_id: Optional[int]) -> bool:
        """Save a mention to Supabase."""

        # Parse date from GDELT format (YYYYMMDDHHMMSS)
        published_date = None
        if article.get("seendate"):
            try:
                dt = datetime.strptime(article["seendate"][:8], "%Y%m%d")
                published_date = dt.strftime("%Y-%m-%d")
            except:
                pass

        # Use first 500 chars of title as excerpt if no excerpt
        excerpt = article.get("title", "")[:500]

        try:
            result = self.db.insert("media_mentions", {
                "organization_id": org_id,
                "outlet_id": outlet_id,  # Can be None for non-Michigan sources
                "article_url": article.get("url", ""),
                "headline": article.get("title", "")[:500],
                "published_date": published_date,
                "excerpt": excerpt,
                "mention_type": "mention"
            })
            return result is not None
        except Exception as e:
            if "duplicate" not in str(e).lower():
                if self.verbose:
                    print(f"      DB error: {e}")
                self.stats["errors"] += 1
            return False

    def collect_for_org(self, org: Dict, global_urls: set) -> int:
        """Collect media mentions for one organization."""

        print(f"  {org['name']}", end=" ", flush=True)

        articles = self.search_gdelt(org["name"])

        if not articles:
            print("- no results")
            return 0

        org_mentions = 0
        michigan_mentions = 0

        for article in articles:
            url = article.get("url", "")

            # Skip if already exists
            normalized_url = url.rstrip('/').replace('http://', 'https://')
            if url in global_urls or normalized_url in global_urls:
                self.stats["duplicates_skipped"] += 1
                continue

            # Try to match to Michigan outlet
            outlet_id = self.get_outlet_id_for_url(url)
            if outlet_id:
                michigan_mentions += 1

            # Save to database
            if self.save_mention_to_db(org["id"], article, outlet_id):
                self.stats["mentions_inserted"] += 1
                org_mentions += 1
                global_urls.add(url)
                global_urls.add(normalized_url)

        print(f"- {len(articles)} found, {org_mentions} new ({michigan_mentions} MI)")
        self.stats["mentions_found"] += org_mentions
        return org_mentions

    def collect_all(self, limit: Optional[int] = None, offset: int = 0, prioritize_ein: bool = True) -> None:
        """Collect mentions for all organizations."""

        print("\n" + "=" * 70)
        print("ECOCENSUS MEDIA MENTIONS COLLECTOR (GDELT)")
        print("=" * 70)

        # Load outlets
        self.load_outlets()

        # Load existing URLs
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

        print("=" * 70)

        for i, org in enumerate(orgs, 1):
            print(f"\n[{i}/{len(orgs)}]", end=" ")
            self.collect_for_org(org, global_urls)
            self.stats["orgs_processed"] += 1

            # Delay between orgs to avoid rate limits
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
    parser = argparse.ArgumentParser(
        description="Collect media mentions using GDELT (fast, free, no rate limits)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python collect_media_gdelt.py --test           # Test with 5 orgs
  python collect_media_gdelt.py --limit 50       # Process first 50 orgs
  python collect_media_gdelt.py                  # Process all orgs with EINs
  python collect_media_gdelt.py --all-orgs       # Include orgs without EINs
        """
    )
    parser.add_argument("--limit", type=int, help="Number of organizations to process")
    parser.add_argument("--offset", type=int, default=0, help="Starting offset")
    parser.add_argument("--test", action="store_true", help="Test mode: process only 5 orgs")
    parser.add_argument("--all-orgs", action="store_true", help="Include orgs without EINs")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    limit = 5 if args.test else args.limit
    prioritize_ein = not args.all_orgs

    try:
        collector = GDELTCollector(verbose=args.verbose)
        collector.collect_all(limit=limit, offset=args.offset, prioritize_ein=prioritize_ein)
    except ValueError as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
