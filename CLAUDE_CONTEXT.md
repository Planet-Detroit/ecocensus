# Claude Context File

**Read this first when starting a new session on ECOcensus.**

---

## Quick Summary

ECOcensus Michigan is a React + Supabase web app showing Michigan environmental nonprofits. It displays 732 organizations with financial data, maps, and media mentions.

**Live site:** https://ecocensus.vercel.app
**Repo:** https://github.com/Planet-Detroit/ecocensus

---

## Tech Stack

- React + Vite (frontend)
- Supabase (PostgreSQL database)
- Vercel (hosting)
- Leaflet (maps)
- Recharts (charts)

---

## Key Files

| File | Purpose |
|------|---------|
| `src/components/Home.jsx` | Org search/filter page with paginated financials fetch |
| `src/components/OrgProfile.jsx` | Individual org profile with financials + media mentions |
| `src/components/Dashboard.jsx` | Financial health rankings |
| `src/components/Landing.jsx` | Map view |
| `src/App.css` | All styles |
| `vercel.json` | Client-side routing fix |
| `PROJECT_STATE.md` | Full project documentation |
| `scripts/collect_media_*.py` | Media collection scripts (didn't work well) |

---

## Database Tables (Supabase)

1. **organizations** - 732 orgs, UUID `id`, has `slug` for URLs
2. **financials** - 1197 records, links via `organization_id`
3. **outlets** - 12 Michigan news outlets
4. **media_mentions** - Links orgs to articles, `outlet_id` often NULL

---

## Recent Issues & Fixes

### 1. Supabase 1000-row limit
Home.jsx now paginates to fetch all 1197 financial records:
```javascript
while (true) {
  const finResponse = await fetch(
    `${SUPABASE_URL}/rest/v1/financials?select=organization_id&offset=${offset}&limit=${pageSize}`,
    ...
  )
  if (finData.length < pageSize) break
  offset += pageSize
}
```

### 2. Vercel 404 on refresh
Added `vercel.json` with rewrite rule for client-side routing.

### 3. Media mentions outlet names
When `outlet_id` is NULL, `OrgProfile.jsx` extracts outlet name from article URL using a domain map.

---

## What Didn't Work

**Media mentions collection** hit rate limits on all approaches:
- Claude API + web search → 429 errors
- GDELT API → 429 errors
- Google Custom Search → needs billing account

**Recommended alternatives:**
1. NewsAPI.ai (has entity extraction, 1000 free/month)
2. NewsData.io (7 years historical, 200 free/day)
3. Enable Google billing (~$5/1000 queries)
4. Manual curation via Google Alerts

---

## Pending Git Push

There are commits that need to be pushed from the user's Mac:
```bash
cd ~/Documents/org-profiles && git pull && git push
```

---

## Key UUIDs

- **Michigan Environmental Council:** `dcb04eaf-ad2c-4ca7-a177-0ff8659aeb55`

---

## Environment Variables (.env)

```
VITE_SUPABASE_URL=https://zocaxurjikmwskmwfsfv.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIzaSy...
GOOGLE_CSE_ID=b6cc4d5423a1c42f1
```

---

## Next Steps

1. Push git changes (user's Mac)
2. Choose media mentions API (NewsAPI.ai recommended)
3. Add regional breakdowns to dashboard
4. Add CSV export feature

---

*For full details, read PROJECT_STATE.md*
