import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Landing from './components/Landing'
import Home from './components/Home'
import OrgProfile from './components/OrgProfile'
import Dashboard from './components/Dashboard'
import './App.css'

function App() {
  return (
    <Router>
      <div className="app">
        <header className="site-header">
          <div className="header-container">
            <Link to="/" className="site-logo">ECOcensus Michigan</Link>
            <nav className="site-nav">
              <Link to="/" className="nav-link">Map</Link>
              <Link to="/organizations" className="nav-link">Organizations</Link>
              <Link to="/dashboard" className="nav-link">Dashboard</Link>
            </nav>
          </div>
        </header>

        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/organizations" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/org/:slug" element={<OrgProfile />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
