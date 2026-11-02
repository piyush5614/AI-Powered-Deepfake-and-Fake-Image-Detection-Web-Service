import { Menu, ScanEye, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useHealth } from '../hooks/useHealth'
import { Button } from './Button'

export function Navbar() {
  const health = useHealth()
  const [open, setOpen] = useState(false)
  const status = health.status === 'offline' ? 'offline' : health.status === 'loading' ? 'loading' : health.health.model_loaded ? 'online' : 'missing'
  const statusLabel = { online: 'Model online', missing: 'Model not loaded', offline: 'API offline', loading: 'Checking API' }[status]
  return (
    <header className="navbar">
      <NavLink className="brand" to="/" aria-label="TruthLens home"><span className="brand-mark"><ScanEye size={18} /></span><span>TruthLens</span></NavLink>
      <Button className="menu-toggle" variant="ghost" size="sm" aria-label={open ? 'Close menu' : 'Open menu'} onClick={() => setOpen(!open)}>{open ? <X size={19} /> : <Menu size={19} />}</Button>
      <nav className={open ? 'nav-links nav-open' : 'nav-links'} aria-label="Main navigation">
        <NavLink to="/" onClick={() => setOpen(false)}>Analyze</NavLink>
        <NavLink to="/history" onClick={() => setOpen(false)}>History</NavLink>
        <NavLink to="/about" onClick={() => setOpen(false)}>How it works</NavLink>
        <NavLink to="/ethics" onClick={() => setOpen(false)}>Ethics</NavLink>
      </nav>
      <div className={`health-pill health-${status}`} role="status"><span className="health-dot" />{statusLabel}</div>
    </header>
  )
}
