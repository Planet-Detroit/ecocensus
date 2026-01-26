#!/usr/bin/env python3
"""
Media Mentions Collector using Google Custom Search API
- 100 free queries/day
- Reliable, no rate limit issues at low volume
- Can restrict to specific sites

Setup:
1. Go to https://programmablesearchengine.google.com/
2. Create a search engine, add Michigan news sites (or search whole web)
3. Get your Search Engine ID (cx)
4. Go to https://console.cloud.google.com/apis/credentials
5. Create an API key
6. Add to .env:
   GOOGLE_API_KEY=your_key
   GOOGLE_CSE_ID=your_search_engine_id
"""

import json
import time
import argparse
import requests
from datetime import datetime
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()


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


class GoogleSearchCollector:
    """Collects media mentions using Google Custom Search API."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.cse_id = os.getenv("GOOGLE_CSE_ID")

        if not self.api_key or not self.cse_id:
            raise ValueError("GOOGLE_API_KEY and GOOGLE_CSE_ID required in .env file")

        self.db = SupabaseClient()
        self.outlet_ids: Dict[str, int] = {}
        self.queries_used = 0
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
                url = outlet["url"]
                domain = url.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
                self.outlet_ids[domain] = outlet["id"]
            print(f"  Loaded {len(self.outlet_ids)} outlets")
        except Exception as e:
            print(f"  Error loading outlets: {e}")

    def get_organizations(self, limit: Optional[int] = None, offset: int = 0, prioritize_ein: bool = True) -> List[Dict]:
        if prioritize_ein:
            return self.db.select_not_null("organizations", "id,name,slug,ein", "ein", limit=limit, offset=offset, order="name")
        else:
            return self.db.select("organizations", "id,name,slug", limit=limit, offset=offset, order="name")

    def get_all_existing_urls(self) -> set:
        try:
            result = self.db.select("media_mentions", "article_url")
            return {row["article_url"] for row in result} if result else set()
        except:
            return set()

    def search_google(self, org_name: str, num_results: int = 10) -> List[Dict]:
        """Search Google Custom Search for articles mentioning an organization."""

        # Search for org name + Michigan + news
        query = f'"{org_name}" Michigan'

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": min(num_results, 10),  # Max 10 per request
            "sort": "date"  # Sort by date
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            self.queries_used += 1

            if response.status_code == 429:
                print("(quota exceeded)", end=" ")
                return []

            if response.status_code != 200:
                if self.verbose:
                    print(f"(HTTP {response.status_code})", end=" ")
                return []

            data = response.json()
            items = data.get("items", [])

            # Convert to our format
            articles = []
            for item in items:
                articles.append({
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "domain": item.get("displayLink", "")
                })

            return articles

        except Exception as e:
            if self.verbose:
                print(f"(error: {e})", end=" ")
            self.stats["errors"] += 1
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
        try:
            result = self.db.insert("media_mentions", {
                "organization_id": org_id,
                "outlet_id": outlet_id,
                "article_url": article.get("url", ""),
                "headline": article.get("title", "")[:500],
                "published_date": None,  # Google doesn't always provide dates
                "excerpt": article.get("snippet", "")[:500],
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

        articles = self.search_google(org["name"])

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
        print("ECOCENSUS MEDIA MENTIONS COLLECTOR (Google Custom Search)")
        print("=" * 70)
        print("NOTE: Free tier = 100 queries/day. Each org = 1 query.")

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

        if len(orgs) > 100:
            print(f"\nWARNING: Processing {len(orgs)} orgs will exceed free quota (100/day)")
            print("Consider using --limit 100 or running over multiple days")

        print("=" * 70)

        for i, org in enumerate(orgs, 1):
            print(f"\n[{i}/{len(orgs)}]", end=" ")
            self.collect_for_org(org, global_urls)
            self.stats["orgs_processed"] += 1

            # Small delay to be nice
            time.sleep(1)

            # Check quota
            if self.queries_used >= 100:
                print("\n\nReached 100 query limit (free tier). Stopping.")
                print(f"Resume tomorrow with: --offset {offset + i}")
                break

        self.print_summary()

    def print_summary(self) -> None:
        print("\n" + "=" * 70)
        print("COLLECTION COMPLETE")
        print("=" * 70)
        print(f"Organizations processed: {self.stats['orgs_processed']}")
        print(f"Google queries used:     {self.queries_used}/100")
        print(f"Mentions found:          {self.stats['mentions_found']}")
        print(f"Mentions inserted:       {self.stats['mentions_inserted']}")
        print(f"Duplicates skipped:      {self.stats['duplicates_skipped']}")
        print(f"Errors:                  {self.stats['errors']}")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Collect media mentions using Google Custom Search API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Setup:
  1. Create a Custom Search Engine at https://programmablesearchengine.google.com/
  2. Get an API key at https://console.cloud.google.com/apis/credentials
  3. Add to .env:
     GOOGLE_API_KEY=your_key
     GOOGLE_CSE_ID=your_search_engine_id

Examples:
  python collect_media_google.py --test        # Test with 5 orgs
  python collect_media_google.py --limit 100   # Process 100 orgs (free daily limit)
  python collect_media_google.py --offset 100  # Resume from org 101
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
        collector = GoogleSearchCollector(verbose=args.verbose)
        collector.collect_all(limit=limit, offset=args.offset, prioritize_ein=prioritize_ein)
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nSetup instructions:")
        print("1. Create a Custom Search Engine at https://programmablesearchengine.google.com/")
        print("2. Get an API key at https://console.cloud.google.com/apis/credentials")
        print("3. Add to your .env file:")
        print("   GOOGLE_API_KEY=your_key")
        print("   GOOGLE_CSE_ID=your_search_engine_id")


if __name__ == "__main__":
    main()
