import os
import sys
import requests
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import time

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

log_file = f"data/990_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
os.makedirs("data", exist_ok=True)

def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    with open(log_file, 'a') as f:
        f.write(log_message + '\n')

def fetch_990_data(ein):
    url = f"https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"  ✗ Error: {str(e)}")
        return None

def extract_financials(data, org_id):
    if not data or 'filings_with_data' not in data:
        return []
    
    financials = []
    for filing in data['filings_with_data'][:5]:
        try:
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
            log(f"  ✗ Error extracting: {str(e)}")
    
    return financials

def main():
    log("="*60)
    log("TEST RUN - Processing 5 Organizations")
    log("="*60)
    
    result = supabase.table('organizations')\
        .select('id, name, slug, ein')\
        .not_.is_('ein', 'null')\
        .order('name')\
        .limit(5)\
        .execute()
    
    log(f"\nTesting with {len(result.data)} organizations\n")
    
    for idx, org in enumerate(result.data, 1):
        log(f"[{idx}/5] {org['name']} (EIN: {org['ein']})")
        
        data = fetch_990_data(org['ein'])
        if not data:
            continue
        
        financials = extract_financials(data, org['id'])
        
        if not financials:
            log(f"  ⚠ No financial data")
            continue
        
        for f in financials:
            try:
                supabase.table('financials').upsert(f).execute()
                log(f"  ✓ {f['year']}: ${f['revenue']:,} revenue, ${f['assets']:,} assets")
            except Exception as e:
                log(f"  ✗ Error: {str(e)}")
        
        time.sleep(0.5)
    
    log("\n" + "="*60)
    log("TEST COMPLETE - Check Supabase financials table")
    log("="*60)

if __name__ == "__main__":
    main()