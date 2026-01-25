# ECOcensus Michigan - Project State Document

**Last Updated:** January 25, 2026
**Repository:** https://github.com/Planet-Detroit/ecocensus
**Live Site:** Deployed on Vercel

---

## Project Overview

ECOcensus Michigan is a web application that provides analysis and visualization of Michigan's environmental and conservation nonprofit sector using IRS 990 data. The project is a collaboration between Planet Detroit and Michigan Environmental Council, with data support from the Johnson Center for Philanthropy at Grand Valley State University.

### Tech Stack

- **Frontend:** React + Vite
- **Styling:** Custom CSS (Arimo font from Google Fonts)
- **Database:** Supabase (PostgreSQL)
- **Mapping:** Leaflet / react-leaflet
- **Charts:** Recharts
- **Deployment:** Vercel

---

## Current Implementation vs. Project Proposal

| Proposal Goal | Status | Notes |
|--------------|--------|-------|
| **Phase 1: Data Collection** | ✅ Done | 600+ orgs, financials in Supabase |
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
| **Media mentions** | 🔄 In Progress | Script running, UI integration pending |

---

## Application Structure

### Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/` | `Landing.jsx` | Home page with interactive map of all geocoded orgs |
| `/organizations` | `Home.jsx` | Searchable/filterable list of all organizations |
| `/dashboard` | `Dashboard.jsx` | Financial health rankings and aggregate statistics |
| `/org/:slug` | `OrgProfile.jsx` | Individual organization profile with financials |

### Key Files

```
org-profiles/
├── src/
│   ├── App.jsx          # Main app with routing and header
│   ├── App.css          # All application styles
│   ├── index.css        # Base styles and CSS reset
│   └── components/
│       ├── Landing.jsx      # Map page with Leaflet
│       ├── Home.jsx         # Organizations list with filters
│       ├── Dashboard.jsx    # Financial health dashboard
│       └── OrgProfile.jsx   # Individual org profiles
├── scripts/
│   └── collect_media_mentions.py  # Media mentions collector (Claude API)
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
- `focus_areas` (array of 27 possible areas)
- `website`, `mission`

### Financials Table
- `id`, `organization_id` (foreign key)
- `year` (fiscal year)
- `revenue`, `expenses`, `assets`
- Data available: 2019-2024 (2024 partial - 15 records)

### Outlets Table
- `id`, `name`, `url`, `outlet_type`, `region`
- 12 Michigan outlets configured (Bridge Michigan, Detroit Free Press, MLive, etc.)

### Media Mentions Table
- `id`, `organization_id` (FK), `outlet_id` (FK)
- `article_url`, `headline`, `published_date`
- `excerpt`, `mention_type`, `created_at`

---

## Media Mentions System

### Script Location
`scripts/collect_media_mentions.py`

### What It Does
- Uses Claude API with web search to find articles (2023-2026)
- Searches 12 Michigan media outlets + optional Google News
- Writes directly to Supabase `media_mentions` table
- Deduplicates by URL across all organizations
- Prioritizes orgs with EINs (larger, more newsworthy)

### CLI Options
```bash
python collect_media_mentions.py --test           # 3 orgs (quick test)
python collect_media_mentions.py --limit 10       # First 10 orgs
python collect_media_mentions.py --offset 50 --limit 20  # Orgs 51-70 (resume)
python collect_media_mentions.py --no-google      # Skip Google News
python collect_media_mentions.py --all-orgs       # Include orgs without EINs
python collect_media_mentions.py -v               # Verbose output
```

### Outlets Configured
| Outlet | Domain | Type |
|--------|--------|------|
| Bridge Michigan | bridgemi.com | Nonprofit News |
| Detroit Free Press | freep.com | Daily Newspaper |
| The Detroit News | detroitnews.com | Daily Newspaper |
| MLive | mlive.com | News Website |
| Michigan Radio | michiganradio.org | Public Radio |
| Crain's Detroit Business | crainsdetroit.com | Business News |
| Planet Detroit | planetdetroit.org | Environmental News |
| Michigan Advance | michiganadvance.com | News Website |
| Detroit Metro Times | metrotimes.com | Alternative Weekly |
| WDET | wdet.org | Public Radio |
| Interlochen Public Radio | interlochenpublicradio.org | Public Radio |
| Great Lakes Now | greatlakesnow.org | Environmental News |

### API Costs
- ~6,648 API calls for full run (554 EIN orgs × 12 outlets)
- Rate limited: 1.5s between outlets, 3s between orgs
- Full run takes several hours

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
10. **Created media mentions collection script with Supabase integration**
11. **Added outlets and media_mentions tables to database**

---

## Next Steps (Prioritized)

### Immediate (After Script Completes)
1. **Add Media section to OrgProfile.jsx** - Display collected mentions on org pages

### High Priority
2. **Regional Economic Breakdowns** - Add county/region aggregations to dashboard
3. **Export Feature** - Let researchers download filtered org lists as CSV

### Medium Priority
4. **Revenue Source Analysis** - If 990 data includes breakdown, add pie charts
5. **Media mentions on Organizations page** - Show mention count as a sortable column

### Lower Priority (Higher Effort)
6. **Board Member Network** - Requires Schedule J/O data from 990s
7. **Mission/Program NLP** - Auto-categorization using Claude

---

## Environment Variables

```bash
# .env file
VITE_SUPABASE_URL=https://zocaxurjikmwskmwfsfv.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Contacts

- **Project Lead:** Michigan Environmental Council
- **Data Partner:** Johnson Center for Philanthropy, GVSU
- **Development:** Planet Detroit (Nina)

---

*This document should be updated when significant changes are made to the project.*
