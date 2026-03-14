import os
import sys
import requests
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import time

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# Setup logging
log_file = f"data/990_pull_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
os.makedirs("data", exist_ok=True)

def log(message):
    """Log to both console and file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    with open(log_file, 'a') as f:
        f.write(log_message + '\n')

def fetch_990_data(ein):
    """Fetch 990 data from ProPublica Nonprofit Explorer API"""
    url = f"https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log(f"  ✗ API Error for EIN {ein}: {str(e)}")
        return None
    except Exception as e:
        log(f"  ✗ Unexpected error for EIN {ein}: {str(e)}")
        return None

def extract_financials(data, org_id):
    """Extract financial data from 990 filings"""
    if not data or 'filings_with_data' not in data:
        return []
    
    financials = []
    for filing in data['filings_with_data'][:5]:  # Last 5 years
        try:
            # Extract year
            year = filing.get('tax_prd_yr')
            if not year:
                continue
                
            financials.append({
                'organization_id': org_id,
                'year': year,
                'revenue': filing.get('totrevenue') or 0,
                'expenses': filing.get('totfuncexpns') or 0,
                'assets': filing.get('totassetsend') or 0,
                'net_assets': filing.get('netassetsend') or 0,
                'liabilities': filing.get('totliabend') or 0,
                'source_url': f"https://projects.propublica.org/nonprofits/organizations/{filing.get('ein', '')}",
                'filed_date': filing.get('pdf_date')
            })
        except Exception as e:
            log(f"  ✗ Error extracting filing: {str(e)}")
            continue
    
    return financials

def main():
    log("="*60)
    log("Starting 990 Data Pull for All Organizations")
    log("="*60)
    
    # Get all orgs with EINs
    try:
        result = supabase.table('organizations')\
            .select('id, name, slug, ein')\
            .not_.is_('ein', 'null')\
            .order('name')\
            .execute()
    except Exception as e:
        log(f"✗ Failed to fetch organizations from Supabase: {str(e)}")
        sys.exit(1)
    
    total_orgs = len(result.data)
    log(f"\nFound {total_orgs} organizations with EINs")
    log(f"Log file: {log_file}")
    log("")
    
    # Statistics
    stats = {
        'total': total_orgs,
        'processed': 0,
        'success': 0,
        'no_data': 0,
        'errors': 0,
        'total_years': 0
    }
    
    start_time = time.time()
    
    for idx, org in enumerate(result.data, 1):
        stats['processed'] += 1
        
        # Progress indicator
        percent = (idx / total_orgs) * 100
        elapsed = time.time() - start_time
        avg_time = elapsed / idx if idx > 0 else 0
        remaining = avg_time * (total_orgs - idx)
        
        log(f"\n[{idx}/{total_orgs}] ({percent:.1f}%) {org['name']}")
        log(f"  EIN: {org['ein']} | ETA: {int(remaining/60)}m {int(remaining%60)}s")
        
        # Fetch 990 data
        data = fetch_990_data(org['ein'])
        
        if not data:
            stats['errors'] += 1
            continue
        
        # Extract and insert financials
        financials = extract_financials(data, org['id'])
        
        if not financials:
            log(f"  ⚠ No financial data found")
            stats['no_data'] += 1
            continue
        
        # Insert financials
        years_inserted = 0
        for f in financials:
            try:
                supabase.table('financials').upsert(f).execute()
                log(f"    ✓ {f['year']}: ${f['revenue']:,} revenue")
                years_inserted += 1
                stats['total_years'] += 1
            except Exception as e:
                log(f"    ✗ Error inserting {f['year']}: {str(e)}")
        
        if years_inserted > 0:
            stats['success'] += 1
        
        # Rate limiting - be nice to ProPublica
        time.sleep(0.5)  # Half second between requests
    
    # Final statistics
    elapsed_total = time.time() - start_time
    log("\n" + "="*60)
    log("SUMMARY")
    log("="*60)
    log(f"Total organizations: {stats['total']}")
    log(f"Successfully processed: {stats['success']}")
    log(f"No data found: {stats['no_data']}")
    log(f"Errors: {stats['errors']}")
    log(f"Total years of data: {stats['total_years']}")
    log(f"Time elapsed: {int(elapsed_total/60)}m {int(elapsed_total%60)}s")
    log(f"Average per org: {elapsed_total/total_orgs:.1f}s")
    log("")
    log(f"Log saved to: {log_file}")
    log("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n\n✗ Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        log(f"\n\n✗ Fatal error: {str(e)}")
        sys.exit(1)