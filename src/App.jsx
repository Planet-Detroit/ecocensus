import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './components/Home'
import OrgProfile from './components/OrgProfile'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/org/:slug" element={<OrgProfile />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App