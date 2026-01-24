#!/usr/bin/env python3
"""
Media Mentions Collector for ECOcensus Project
"""

import csv
import json
import time
import re
from datetime import datetime
from typing import List, Dict
import anthropic
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Michigan media outlets to search
OUTLETS = [
    {"name": "Bridge Michigan", "domain": "bridgemi.com", "outlet_type": "Nonprofit News"},
    {"name": "Detroit Free Press", "domain": "freep.com", "outlet_type": "Daily Newspaper"},
    {"name": "The Detroit News", "domain": "detroitnews.com", "outlet_type": "Daily Newspaper"},
    {"name": "MLive - Detroit", "domain": "mlive.com/detroit", "outlet_type": "News Website"},
    {"name": "MLive - Grand Rapids", "domain": "mlive.com/grand-rapids", "outlet_type": "News Website"},
    {"name": "Michigan Radio", "domain": "michiganradio.org", "outlet_type": "Public Radio"},
    {"name": "Crain's Detroit Business", "domain": "crainsdetroit.com", "outlet_type": "Business News"},
    {"name": "Planet Detroit", "domain": "planetdetroit.org", "outlet_type": "Environmental News"}
]

# Test organizations to search for
TEST_ORGS = [
    {"name": "Michigan Environmental Council", "slug": "michigan-environmental-council"},
    {"name": "Transportation Riders United", "slug": "transportation-riders-united"},
    {"name": "Soulardarity", "slug": "soulardarity"},
    {"name": "Tip of the Mitt Watershed Council", "slug": "tip-of-the-mitt-watershed-council"},
    {"name": "Torch Conservation Center", "slug": "torch-conservation-center"},
    {"name": "Eastside Community Network", "slug": "eastside-community-network"},
    {"name": "Michigan League of Conservation Voters", "slug": "michigan-league-of-conservation-voters"},
    {"name": "Sierra Club Michigan Chapter", "slug": "sierra-club-michigan-chapter"},
    {"name": "Ecology Center", "slug": "ecology-center"},
    {"name": "Detroit Greenways Coalition", "slug": "detroit-greenways-coalition"}
]


class MediaMentionsCollector:
    """Collects media mentions using Claude with web search."""
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in .env file")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.mentions = []
        
    def search_org_in_outlet(self, org_name: str, outlet: Dict) -> List[Dict]:
        """Search for an organization in a specific outlet."""
        
        print(f"  Searching {outlet['name']} for {org_name}...")
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{
                    "role": "user",
                    "content": f"""Search for articles about "{org_name}" on {outlet['name']} ({outlet['domain']}).

Find up to 3 recent articles that mention this organization. For each article found, extract:
1. Article headline/title
2. Article URL
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

If no articles found, return empty array: []"""
                }]
            )
            
            result_text = ""
            for block in response.content:
                if block.type == "text":
                    result_text += block.text
            
            json_match = re.search(r'\[[\s\S]*\]', result_text)
            if json_match:
                articles = json.loads(json_match.group(0))
                return articles
            else:
                print(f"    No structured data found")
                return []
                
        except Exception as e:
            print(f"    Error: {e}")
            return []
    
    def collect_for_org(self, org: Dict) -> None:
        """Collect media mentions for one organization across all outlets."""
        
        print(f"\n{'='*60}")
        print(f"Collecting mentions for: {org['name']}")
        print(f"{'='*60}")
        
        org_mentions = 0
        
        for outlet in OUTLETS:
            articles = self.search_org_in_outlet(org['name'], outlet)
            
            for article in articles:
                mention = {
                    "org_slug": org['slug'],
                    "org_name": org['name'],
                    "outlet_name": outlet['name'],
                    "outlet_domain": outlet['domain'],
                    "article_url": article.get('url', ''),
                    "headline": article.get('headline', ''),
                    "published_date": article.get('published_date'),
                    "excerpt": article.get('excerpt', ''),
                    "collected_at": datetime.now().isoformat()
                }
                
                self.mentions.append(mention)
                org_mentions += 1
                
                print(f"    ✓ Found: {article.get('headline', 'No title')[:60]}...")
            
            time.sleep(2)
        
        print(f"\n  Total mentions found: {org_mentions}")
    
    def collect_all(self) -> None:
        """Collect mentions for all test organizations."""
        
        print("\n" + "="*60)
        print("MEDIA MENTIONS COLLECTOR")
        print("="*60)
        print(f"Organizations: {len(TEST_ORGS)}")
        print(f"Outlets: {len(OUTLETS)}")
        print(f"Max searches: {len(TEST_ORGS) * len(OUTLETS)}")
        print("="*60)
        
        for i, org in enumerate(TEST_ORGS, 1):
            print(f"\n[{i}/{len(TEST_ORGS)}]")
            self.collect_for_org(org)
            
            if i < len(TEST_ORGS):
                print("\n  Pausing 5 seconds...")
                time.sleep(5)
        
        print("\n" + "="*60)
        print(f"COLLECTION COMPLETE")
        print(f"Total mentions found: {len(self.mentions)}")
        print("="*60)
    
    def save_to_csv(self, filename: str = "media_mentions.csv") -> None:
        """Save collected mentions to CSV."""
        
        if not self.mentions:
            print("No mentions to save!")
            return
        
        fieldnames = [
            'org_slug', 'org_name', 'outlet_name', 'outlet_domain',
            'article_url', 'headline', 'published_date', 'excerpt', 'collected_at'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.mentions)
        
        print(f"\n✓ Saved {len(self.mentions)} mentions to {filename}")
    
    def save_to_json(self, filename: str = "media_mentions.json") -> None:
        """Save collected mentions to JSON for review."""
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.mentions, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved to {filename}")


def main():
    """Main execution."""
    
    try:
        collector = MediaMentionsCollector()
        collector.collect_all()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"media_mentions_{timestamp}.csv"
        json_file = f"media_mentions_{timestamp}.json"
        
        collector.save_to_csv(csv_file)
        collector.save_to_json(json_file)
        
        print("\n" + "="*60)
        print("Next steps:")
        print(f"1. Review {json_file} for quality")
        print(f"2. Import {csv_file} into Supabase")
        print("="*60)
        
    except ValueError as e:
        print(f"ERROR: {e}")
        print("Add ANTHROPIC_API_KEY to your .env file")


if __name__ == "__main__":
    main()