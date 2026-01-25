# ECOcensus Michigan - Project State Document

**Last Updated:** January 24, 2026
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
| **Media mentions** | ⚠️ Script exists | `scripts/collect_media_mentions.py` - needs integration |

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
- `id`, `name`, `slug`
- `ein` (IRS Employer Identification Number)
- `city`, `state`, `zip`
- `latitude`, `longitude` (517 orgs geocoded)
- `ntee_code` (National Taxonomy of Exempt Entities)
- `focus_areas` (array of 27 possible areas)
- `website`, `mission`

### Financials Table
- `id`, `org_id` (foreign key)
- `year` (fiscal year)
- `revenue`, `expenses`, `assets`
- Data available: 2019-2024 (2024 partial - 15 records)

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

This approach smooths year-over-year fluctuations common in nonprofits (grant cycles, capital campaigns, etc.).

---

## NTEE Codes Reference

The app includes 47 NTEE codes with human-readable meanings:

| Code | Meaning |
|------|---------|
| C01 | Environmental Alliance |
| C20 | Pollution Abatement |
| C27 | Recycling Programs |
| C30 | Natural Resources Conservation |
| C32 | Water Conservation |
| C34 | Land Conservation |
| C35 | Energy Resources |
| C36 | Forestry |
| C40 | Botanical & Horticultural |
| C42 | Garden Clubs |
| C50 | Zoos & Aquariums |
| C60 | Environmental Education |
| ... | (see Home.jsx for full list) |

---

## Focus Areas (27 categories)

Advocacy, Air Quality, Birding, Climate, Coastal, Energy, Environmental Education, Environmental Health, Environmental Justice, Farming, Fishing & Hunting, Food, Forestry, Green Infrastructure, Health, Justice, Land, Land Use, Parks, Recycling, Transportation, Trees, Urban Agriculture, Waste, Water, Wetlands, Wildlife

---

## Media Mentions Script

**Location:** `scripts/collect_media_mentions.py`

**What it does:**
- Uses Claude API with web search to find articles mentioning Michigan environmental orgs
- Searches 8 Michigan media outlets (Bridge Michigan, Detroit Free Press, MLive, etc.)
- Outputs CSV and JSON files with headlines, URLs, excerpts, dates

**Requirements:**
- `ANTHROPIC_API_KEY` in `.env` file
- Python packages: `anthropic`, `python-dotenv`

**Current state:** Test script with 10 sample organizations. Needs:
1. Supabase table for storing mentions
2. Integration with org profile pages
3. Expansion to all organizations

---

## Styling Notes

- **Font:** Arimo (Google Fonts) - clean sans-serif
- **Design:** Clean & minimal header, card-based layouts
- **Map:** Markers reduced 25% from Leaflet defaults
- **Responsive:** Landing page optimized for map "above the fold"

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

---

## Next Steps (Recommended Priority)

### High Priority
1. **Media Mentions Integration** - Create Supabase table, run script for all orgs, add to profiles
2. **Regional Economic Breakdowns** - Add county/region aggregations to dashboard

### Medium Priority
3. **Revenue Source Analysis** - If 990 data includes breakdown, add pie charts
4. **Export Feature** - Let researchers download filtered org lists as CSV

### Lower Priority (Higher Effort)
5. **Board Member Network** - Requires Schedule J/O data from 990s
6. **Mission/Program NLP** - Auto-categorization using Claude

---

## Environment Variables

```
# .env (for media mentions script)
ANTHROPIC_API_KEY=sk-ant-...

# Supabase (configured in app)
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
```

---

## Contacts

- **Project Lead:** Michigan Environmental Council
- **Data Partner:** Johnson Center for Philanthropy, GVSU
- **Development:** Planet Detroit

---

*This document should be updated when significant changes are made to the project.*
