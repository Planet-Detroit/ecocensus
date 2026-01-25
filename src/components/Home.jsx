import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

// NTEE Code meanings (Environmental category)
const NTEE_CODES = {
  'C01': 'Environmental Alliance',
  'C02': 'Environmental Management',
  'C03': 'Environmental Beautification',
  'C05': 'Environmental Research',
  'C11': 'Environmental Conservation',
  'C12': 'Water Resources',
  'C19': 'Environmental Support',
  'C20': 'Pollution Abatement',
  'C27': 'Recycling Programs',
  'C30': 'Natural Resources',
  'C32': 'Water Conservation',
  'C34': 'Land Conservation',
  'C35': 'Energy Conservation',
  'C36': 'Forest Conservation',
  'C40': 'Botanical Gardens',
  'C41': 'Botanical Gardens',
  'C42': 'Garden Clubs',
  'C50': 'Environmental Education',
  'C60': 'Environmental Advocacy',
  'C99': 'Environmental NEC',
  // Extended codes (with additional digits)
  'C013': 'Environmental Alliance',
  'C015': 'Environmental Alliance',
  'C023': 'Environmental Management',
  'C030': 'Natural Resources',
  'C033': 'Natural Resources',
  'C054': 'Environmental Research',
  'C114': 'Environmental Conservation',
  'C123': 'Water Resources',
  'C193': 'Environmental Support',
  'C200': 'Pollution Abatement',
  'C270': 'Recycling Programs',
  'C27Z': 'Recycling Programs',
  'C300': 'Natural Resources',
  'C30Z': 'Natural Resources',
  'C320': 'Water Conservation',
  'C340': 'Land Conservation',
  'C40Z': 'Botanical & Nature Centers',
  'C410': 'Botanical Gardens',
  'C420': 'Garden Clubs',
  'C428': 'Garden Clubs',
  'C42C': 'Garden Clubs',
  'C42Z': 'Garden Clubs',
  'C500': 'Environmental Education',
  'C50Z': 'Environmental Education',
  'C600': 'Environmental Advocacy',
  'C60Z': 'Environmental Advocacy',
}

// All focus areas for the filter
const FOCUS_AREAS = [
  'Advocacy',
  'Air Quality',
  'Birding',
  'Climate',
  'Energy',
  'Environmental Education',
  'Environmental Justice',
  'Food & Agriculture',
  'Garden Club',
  'Hunting & Fishing',
  'Lake Association',
  'Land Conservation',
  'Landfills',
  'Nature Center',
  'Outdoor Recreation',
  'Pollinators',
  'Recycling',
  'Stewardship',
  'Sustainability',
  'Trails & Pathways',
  'Transportation',
  'Tree Canopy',
  'Utilities',
  'Water',
  'Watershed Council',
  'Wetlands',
  'Wildlife',
]

function Home() {
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [dataFilter, setDataFilter] = useState('all') // 'all', 'with-data', 'without-data'
  const [focusFilter, setFocusFilter] = useState('all')

  useEffect(() => {
    fetchOrgs()
  }, [])

  const fetchOrgs = async () => {
    try {
      // Fetch orgs
      const orgsResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/organizations?select=*&order=name`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const orgsData = await orgsResponse.json()

      // Fetch financial data counts
      const finResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/financials?select=organization_id`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }}
      )
      const finData = await finResponse.json()

      // Count financials per org
      const finCounts = {}
      finData.forEach(f => {
        finCounts[f.organization_id] = (finCounts[f.organization_id] || 0) + 1
      })

      // Add hasFinancials flag and parse focus
      const orgsWithFlags = orgsData.map(org => ({
        ...org,
        hasFinancials: (finCounts[org.id] || 0) > 0,
        focusAreas: parseFocus(org.focus)
      }))

      setOrgs(orgsWithFlags)
      setLoading(false)
    } catch (error) {
      console.error('Error:', error)
      setLoading(false)
    }
  }

  // Parse the focus array from the database format
  const parseFocus = (focus) => {
    if (!focus) return []
    try {
      // Handle both string and array formats
      if (Array.isArray(focus)) return focus
      return JSON.parse(focus)
    } catch {
      return []
    }
  }

  // Get NTEE meaning
  const getNTEEMeaning = (code) => {
    if (!code) return null
    return NTEE_CODES[code] || NTEE_CODES[code.substring(0, 3)] || null
  }

  const filteredOrgs = orgs.filter(org => {
    // Search filter
    const matchesSearch = org.name.toLowerCase().includes(search.toLowerCase())

    // Financial data filter
    let matchesData = true
    if (dataFilter === 'with-data') matchesData = org.hasFinancials
    if (dataFilter === 'without-data') matchesData = !org.hasFinancials

    // Focus area filter
    let matchesFocus = true
    if (focusFilter !== 'all') {
      matchesFocus = org.focusAreas.includes(focusFilter)
    }

    return matchesSearch && matchesData && matchesFocus
  })

  const withDataCount = orgs.filter(o => o.hasFinancials).length
  const withoutDataCount = orgs.length - withDataCount

  return (
    <div className="home">
      <header className="home-header">
        <h1>Michigan Environmental Organizations</h1>
        <p className="subtitle">
          {orgs.length} organizations · {withDataCount} with financial data · {withoutDataCount} contact info only
        </p>
      </header>

      <div className="filters-row">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search organizations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="focus-filter">
          <select
            value={focusFilter}
            onChange={(e) => setFocusFilter(e.target.value)}
          >
            <option value="all">All Focus Areas</option>
            {FOCUS_AREAS.map(area => (
              <option key={area} value={area}>{area}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="filter-buttons">
        <button
          className={dataFilter === 'all' ? 'active' : ''}
          onClick={() => setDataFilter('all')}
        >
          All ({orgs.length})
        </button>
        <button
          className={dataFilter === 'with-data' ? 'active' : ''}
          onClick={() => setDataFilter('with-data')}
        >
          With Financial Data ({withDataCount})
        </button>
        <button
          className={dataFilter === 'without-data' ? 'active' : ''}
          onClick={() => setDataFilter('without-data')}
        >
          Contact Info Only ({withoutDataCount})
        </button>
      </div>

      {loading ? (
        <div className="loading">Loading organizations...</div>
      ) : (
        <section className="org-list">
          <h2>
            {filteredOrgs.length} {filteredOrgs.length === 1 ? 'Organization' : 'Organizations'}
            {focusFilter !== 'all' && ` in ${focusFilter}`}
          </h2>
          <div className="org-grid">
            {filteredOrgs.map(org => (
              <Link key={org.slug} to={`/org/${org.slug}`} className="org-card">
                <h3>{org.name}</h3>
                <div className="org-card-meta">
                  {org.ntee_code && getNTEEMeaning(org.ntee_code) && (
                    <span className="badge ntee">{getNTEEMeaning(org.ntee_code)}</span>
                  )}
                  {org.focusAreas.length > 0 && (
                    <span className="focus-tags">
                      {org.focusAreas.slice(0, 2).join(' · ')}
                      {org.focusAreas.length > 2 && ` +${org.focusAreas.length - 2}`}
                    </span>
                  )}
                </div>
                {org.hasFinancials ? (
                  <span className="badge financial">Financial data available</span>
                ) : (
                  <span className="badge small-org">Contact info only</span>
                )}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export default Home
