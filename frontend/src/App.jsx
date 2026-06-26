import { Route, Routes } from 'react-router-dom'
import Nav from './components/Nav.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Episode from './pages/Episode.jsx'
import Library from './pages/Library.jsx'
import Queue from './pages/Queue.jsx'
import Settings from './pages/Settings.jsx'
import './App.css'

export default function App() {
  return (
    <div className="app">
      <Nav />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Library />} />
          <Route path="/episode/:id" element={<Episode />} />
          <Route path="/queue" element={<Queue />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
