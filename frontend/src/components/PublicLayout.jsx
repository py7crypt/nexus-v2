// src/components/PublicLayout.jsx
import { useState, useEffect } from 'react'
import { Outlet, Link, NavLink, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { getCategories } from '../utils'
import { fetchArticles } from '../api'

export default function PublicLayout() {
  const { dark, toggleDark } = useApp()
  const [menuOpen,       setMenuOpen]       = useState(false)
  const [searchOpen,     setSearchOpen]     = useState(false)
  const [query,          setQuery]          = useState('')
  const [cats,           setCats]           = useState(getCategories())
  const [tickerArticles, setTickerArticles] = useState([])
  const [socialLinks,    setSocialLinks]    = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/api/social').then(r => r.json())
      .then(d => { if (d.success && Array.isArray(d.links)) setSocialLinks(d.links) })
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetchArticles({ limit: 10 })
      .then(d => { if (d.articles?.length) setTickerArticles(d.articles) })
      .catch(() => {})
  }, [])

  useEffect(() => {
    const sync = () => setCats(getCategories())
    window.addEventListener('storage', sync)
    const t = setInterval(sync, 2000)
    return () => { window.removeEventListener('storage', sync); clearInterval(t) }
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    if (query.trim()) { navigate(`/?q=${encodeURIComponent(query.trim())}`); setSearchOpen(false); setQuery('') }
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--bg-base)', color: 'var(--text-primary)' }}>

      {/* ── TOP NAV ─────────────────────────────────────────────────────── */}
      <header className="nexus-header sticky top-0 z-50">
        <div className="nexus-container h-16 flex items-center gap-4">

          {/* Logo */}
          <Link to="/" className="nexus-logo flex-shrink-0">
            NEX<span>US</span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden lg:flex items-center gap-0.5 flex-1 overflow-x-auto scrollbar-none">
            <NavLink to="/" end className={({isActive}) => `nexus-nav-link ${isActive ? 'active' : ''}`}>Home</NavLink>
            {cats.map(cat => (
              <NavLink key={cat.name} to={`/category/${cat.name.toLowerCase()}`}
                className={({isActive}) => `nexus-nav-link ${isActive ? 'active' : ''}`}>
                {cat.name}
              </NavLink>
            ))}
          </nav>

          {/* Right controls */}
          <div className="flex items-center gap-1 flex-shrink-0 ml-auto lg:ml-0">
            <button onClick={() => setSearchOpen(s => !s)} className="nexus-icon-btn" title="Search">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
            </button>
            <button onClick={toggleDark} className="nexus-icon-btn" title="Toggle theme">
              {dark
                ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
                : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
              }
            </button>
            <button className="lg:hidden nexus-icon-btn" onClick={() => setMenuOpen(o => !o)}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                {menuOpen ? <><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></> : <><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></>}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="lg:hidden nexus-mobile-menu">
            <Link to="/" onClick={() => setMenuOpen(false)} className="nexus-mobile-link">Home</Link>
            {cats.map(c => (
              <Link key={c.name} to={`/category/${c.name.toLowerCase()}`} onClick={() => setMenuOpen(false)} className="nexus-mobile-link">
                <span className="w-2 h-2 rounded-full inline-block mr-2" style={{ background: c.color }}/>
                {c.icon} {c.name}
              </Link>
            ))}
          </div>
        )}

        {/* Search bar */}
        {searchOpen && (
          <div className="nexus-search-bar">
            <form onSubmit={handleSearch} className="nexus-container flex gap-3 py-3">
              <div className="relative flex-1">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                <input autoFocus value={query} onChange={e => setQuery(e.target.value)}
                  className="w-full bg-white/10 border border-white/20 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-white/50 focus:outline-none focus:border-blue-400"
                  placeholder="Search articles, topics, authors..."/>
              </div>
              <button type="submit" className="nexus-btn-primary text-sm px-5">Search</button>
              <button type="button" onClick={() => setSearchOpen(false)} className="nexus-icon-btn text-white/70 hover:text-white">✕</button>
            </form>
          </div>
        )}
      </header>

      {/* ── BREAKING NEWS TICKER ────────────────────────────────────────── */}
      {tickerArticles.length > 0 && (
        <div className="nexus-ticker">
          <span className="nexus-ticker-label">BREAKING</span>
          <div className="overflow-hidden flex-1">
            <span className="ticker-scroll inline-block whitespace-nowrap text-xs font-medium">
              {[...tickerArticles, ...tickerArticles].map((a, i) => (
                <span key={i}>
                  <Link to={`/article/${a.id}`} className="hover:text-blue-300 transition-colors">{a.title}</Link>
                  <span className="mx-5 opacity-40">◆</span>
                </span>
              ))}
            </span>
          </div>
        </div>
      )}

      <main className="flex-1"><Outlet /></main>

      {/* ── FOOTER ──────────────────────────────────────────────────────── */}
      <footer className="nexus-footer">
        <div className="nexus-container py-14 grid grid-cols-1 md:grid-cols-4 gap-10">
          <div>
            <div className="nexus-logo text-2xl mb-4">NEX<span>US</span></div>
            <p className="text-sm text-slate-400 leading-relaxed">A modern digital media platform covering technology, science, business, health, and culture.</p>
            {socialLinks.length > 0 && (
              <div className="flex gap-2 mt-5 flex-wrap">
                {socialLinks.map(l => (
                  <a key={l.id} href={l.url || '#'} target="_blank" rel="noreferrer" title={l.label}
                    className="w-9 h-9 flex items-center justify-center rounded-lg border border-white/10 hover:border-blue-500 hover:bg-blue-500/10 transition-all bg-white/5 overflow-hidden p-1.5">
                    {l.icon
                      ? <img src={l.icon} alt={l.label} className="w-full h-full object-contain"/>
                      : <span className="text-slate-400 text-xs font-bold">{l.label?.[0]?.toUpperCase() || '?'}</span>
                    }
                  </a>
                ))}
              </div>
            )}
          </div>
          <div>
            <h4 className="nexus-footer-heading">Categories</h4>
            <ul className="space-y-2">
              {cats.map(c => (
                <li key={c.name}>
                  <Link to={`/category/${c.name.toLowerCase()}`} className="text-sm text-slate-400 hover:text-blue-400 transition-colors flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.color }}/>
                    {c.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="nexus-footer-heading">Resources</h4>
            <ul className="space-y-2">
              {['About NEXUS', 'Editorial Policy', 'Write for Us', 'Advertise', 'Careers', 'Contact'].map(i => (
                <li key={i}><a href="#" className="text-sm text-slate-400 hover:text-blue-400 transition-colors">{i}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="nexus-footer-heading">Newsletter</h4>
            <p className="text-sm text-slate-400 mb-4">Get top stories delivered every morning.</p>
            <input type="email" placeholder="your@email.com"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 mb-3"/>
            <button className="nexus-btn-primary w-full text-sm py-2.5">Subscribe Free</button>
          </div>
        </div>
        <div className="border-t border-white/5 py-5">
          <div className="nexus-container flex justify-between items-center text-xs text-slate-500">
            <span>© 2025 NEXUS Media. All rights reserved.</span>
            <div className="flex gap-5">{['Privacy', 'Terms', 'Cookies'].map(l => <a key={l} href="#" className="hover:text-blue-400 transition-colors">{l}</a>)}</div>
          </div>
        </div>
      </footer>
    </div>
  )
}