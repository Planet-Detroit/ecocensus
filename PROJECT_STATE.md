# ECOcensus Michigan - Project State Document

**Last Updated:** January 25, 2026
**Repository:** https://github.com/Planet-Detroit/ecocensus
**Live Site:** https://ecocensus.vercel.app

---

## Project Overview

ECOcensus Michigan is a web application that provides analysis and visualization of Michigan's environmental and conservation nonprofit sector using IRS 990 data. The project is a collaboration between Planet Detroit and Michigan Environmental Council, with data support from the Johnson Center for Philanthropy at Grand Valley State University.

### Tech Stack

- **Frontend:** React + Vite
- **Styling:** Custom CSS (Arimo/Asap fonts from Google Fonts)
- **Database:** Supabase (PostgreSQL)
- **Mapping:** Leaflet / react-leaflet
- **Charts:** Recharts
- **Deployment:** Vercel

---

## Current Implementation vs. Project Proposal

| Proposal Goal | Status | Notes |
|--------------|--------|-------|
| **Phase 1: Data Collection** | ✅ Done | 732 orgs, 1197 financial records in Supabase |
| **Geographic mapping** | ✅ Done | 517 orgs geocoded, Leaflet map on landing page |
| **NTEE categorization** | ✅ Done | 47 NTEE codes with human-readable meanings on org cards |
| **Focus area tagging** | ✅ Done | 27 focus areas with dropdown filter on Organizations page |
| **Financial health assessment** | ✅ Done | 3-year rolling average methodology; healthy/stable/at-risk classification |
| **Economic impact (aggregate)** | ⚠️ Partial | Dashboard shows totals but no regional breakdowns yet |
| **Network maps** | ❌ Not started | Board member overlaps, issue-based clustering |
| **Messaging analysis** | ❌ Not started | NLP on mission/program descriptions from 990s |
| **Pay equity assessment** | ❌ Not started | CEO compensation analysis (requires Schedule J data) |
| **Funding structure analysis** | ❌ Not started | Revenue source patterns and success correlations |
| **Peer benchmarks** | ❌ Not started | Compare similar-sized organizations |
| **Media mentions** | ⚠️ UI Done, Collection Failed | UI integrated, but automated collection hit API limits |

---

## Application Structure

### Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/` | `Landing.jsx` | Home page with interactive map of all geocoded orgs |
| `/organizations` | `Home.jsx` | Searchable/filterable list of all organizations |
| `/dashboard` | `Dashboard.jsx` | Financial health rankings and aggregate statistics |
| `/org/:slug` | `OrgProfile.jsx` | Individual organization profile with financials and media mentions |

### Key Files

```
org-profiles/
├── src/
│   ├── App.jsx          # Main app with routing and header
│   ├── App.css          # All application styles
│   ├── index.css        # Base styles and CSS reset
│   └── components/
│       ├── Landing.jsx      # Map page with Leaflet
│       ├── Home.jsx         # Organizations list with filters (paginated financials fetch)
│       ├── Dashboard.jsx    # Financial health dashboard
│       └── OrgProfile.jsx   # Individual org profiles with media mentions
├── scripts/
│   ├── collect_media_mentions.py  # Claude API collector (rate limited)
│   ├── collect_media_gdelt.py     # GDELT collector (rate limited)
│   └── collect_media_google.py    # Google Custom Search (requires billing)
├── vercel.json          # Client-side routing config
└── PROJECT_STATE.md     # This file
```

---

## Database Schema (Supabase)

### Organizations Table
- `id` (UUID), `name`, `slug`
- `ein` (IRS Employer Identification Number) - 554 orgs have EINs
- `city`, `state`, `zip`
- `latitude`, `longitude` (517 orgs geocoded)
- `ntee_code` (National Taxonomy of Exempt Entities)
- `focus` (array of 27 possible areas)
- `website`, `mission_statement_text`

### Financials Table (1197 records)
- `id`, `organization_id` (foreign key)
- `year` (fiscal year), `revenue`, `expenses`, `assets`
- 286 organizations have financial data

### Outlets Table
- `id`, `name`, `url`, `outlet_type`, `region`
- 12 Michigan outlets configured

### Media Mentions Table
- `id`, `organization_id` (FK), `outlet_id` (FK, nullable)
- `article_url`, `headline`, `published_date`
- `excerpt`, `mention_type`, `created_at`
- Currently contains manually-added demo records

---

## Media Mentions System

### Current State: UI Complete, Automated Collection Failed

The org profile pages now display media mentions from Supabase, with outlet names extracted from URLs when `outlet_id` is null. However, automated collection hit roadblocks:

| Approach | Problem |
|----------|---------|
| **Claude API + Web Search** | 429 rate limits after ~20 calls, even with 5s delays |
| **GDELT API** | 429 rate limits, inconsistent results |
| **Google Custom Search API** | Requires billing account linked to project |

### Scripts Created (in `/scripts/`)

1. **collect_media_mentions.py** - Claude API with web search tool
2. **collect_media_gdelt.py** - GDELT news archive
3. **collect_media_google.py** - Google Custom Search API

### Recommended Alternative Approaches

Based on research, here are better options for collecting media mentions:

#### Option 1: NewsAPI.ai (RECOMMENDED)
- **Why:** Entity extraction built-in, can search by organization name
- **Historical:** Data since 2014
- **Free tier:** 1,000 API calls/month
- **Key feature:** Returns organizations mentioned in articles via NLP
- **URL:** https://newsapi.ai/

#### Option 2: NewsData.io
- **Why:** 7 years historical data, 84,000+ sources
- **Free tier:** 200 requests/day
- **Key feature:** Archive search for historical mentions
- **URL:** https://newsdata.io/

#### Option 3: Webz.io News API Lite
- **Why:** Semantic tagging of organizations, 30 days historical
- **Free tier:** Limited free access
- **Key feature:** Built for brand/organization monitoring
- **URL:** https://webz.io/

#### Option 4: Google Custom Search (with billing)
- **Why:** Already set up, just needs billing enabled
- **Cost:** $5 per 1,000 queries after free 100/day
- **To enable:** Link billing account to Google Cloud project `planetdetroit`
- **Existing script:** `collect_media_google.py` ready to use

#### Option 5: Manual Curation + Google Alerts
- **Why:** Free, no API limits, high quality
- **Process:**
  1. Set up Google Alerts for top 50 organizations
  2. Manually add mentions to Supabase as they come in
  3. Focus on quality over quantity
- **Best for:** Ongoing monitoring rather than historical backfill

### Domain Map for URL-Based Outlet Names

The `OrgProfile.jsx` component extracts outlet names from URLs when `outlet_id` is null:

```javascript
const domainMap = {
  'bridgemi.com': 'Bridge Michigan',
  'freep.com': 'Detroit Free Press',
  'detroitnews.com': 'The Detroit News',
  'mlive.com': 'MLive',
  'michiganradio.org': 'Michigan Radio',
  'michiganadvance.com': 'Michigan Advance',
  'wlns.com': 'WLNS',
  // ... etc
}
```

Add new outlets to this map as needed.

---

## Recent Fixes

### Supabase 1000-Row Limit
The Home.jsx component now paginates through all financial records to correctly show "Financial data available" badges:

```javascript
// Paginate to overcome 1000 row default limit
let allFinData = []
let offset = 0
const pageSize = 1000

while (true) {
  const finResponse = await fetch(
    `${SUPABASE_URL}/rest/v1/financials?select=organization_id&offset=${offset}&limit=${pageSize}`,
    { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
  )
  const finData = await finResponse.json()
  allFinData = allFinData.concat(finData)
  if (finData.length < pageSize) break
  offset += pageSize
}
```

### Vercel Client-Side Routing
Added `vercel.json` to fix 404 errors on page refresh:

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/" }
  ]
}
```

---

## Financial Health Methodology

The dashboard uses a **3-year rolling average** to assess organizational health:

```javascript
// Calculate average margin over most recent 3 years
const avgRevenue = recentYears.reduce((sum, f) => sum + f.revenue, 0) / recentYears.length
const avgExpenses = recentYears.reduce((sum, f) => sum + f.expenses, 0) / recentYears.length
const avgMarginPercent = ((avgRevenue - avgExpenses) / avgRevenue) * 100

// Classification thresholds (symmetric)
if (avgMarginPercent > 5)  → "Healthy"
if (avgMarginPercent >= -5 && <= 5) → "Stable"
if (avgMarginPercent < -5) → "At Risk"
```

---

## Recent Changes (January 2026)

1. Fixed broken App.jsx (was corrupted with bash commands)
2. Added comprehensive styling across all pages
3. Added focus area dropdown filter
4. Added NTEE code meanings to organization cards
5. Updated financial health to 3-year rolling average
6. Made dashboard lists clickable to org profiles
7. Added year range display to health rankings
8. Created compact landing page layout
9. Reduced map marker sizes
10. Created media mentions collection scripts (3 approaches)
11. Added outlets and media_mentions tables to database
12. **Added Media Coverage section to org profile pages**
13. **Fixed financials pagination (1000 row limit)**
14. **Added vercel.json for client-side routing**

---

## Next Steps (Prioritized)

### Immediate
1. **Choose media mentions API** - NewsAPI.ai recommended for entity extraction
2. **Enable Google billing** - If preferring Google Custom Search approach

### High Priority
3. **Regional Economic Breakdowns** - Add county/region aggregations to dashboard
4. **Export Feature** - Let researchers download filtered org lists as CSV

### Medium Priority
5. **Revenue Source Analysis** - If 990 data includes breakdown, add pie charts
6. **Media mentions on Organizations page** - Show mention count as a sortable column

### Lower Priority (Higher Effort)
7. **Board Member Network** - Requires Schedule J/O data from 990s
8. **Mission/Program NLP** - Auto-categorization using Claude

---

## Environment Variables

```bash
# .env file
VITE_SUPABASE_URL=https://zocaxurjikmwskmwfsfv.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
ANTHROPIC_API_KEY=sk-ant-...        # For Claude API collector
GOOGLE_API_KEY=AIzaSy...            # For Google Custom Search
GOOGLE_CSE_ID=b6cc4d5423a1c42f1     # Custom Search Engine ID
```

---

## Contacts

- **Project Lead:** Michigan Environmental Council
- **Data Partner:** Johnson Center for Philanthropy, GVSU
- **Development:** Planet Detroit (Nina)

---

*This document should be updated when significant changes are made to the project.*
