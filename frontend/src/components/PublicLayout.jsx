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

      {/* ── HEADER ─────────────────────────────────────────────────────── */}
      <header className="nexus-header sticky top-0 z-50">
        <div className="nexus-container h-14 flex items-center gap-4">

          <Link to="/" className="nexus-logo flex-shrink-0">NEX<span>US</span></Link>

          <nav className="hidden lg:flex items-center gap-0.5 flex-1 overflow-x-auto scrollbar-none">
            <NavLink to="/" end className={({isActive}) => `nexus-nav-link${isActive ? ' active' : ''}`}>Home</NavLink>
            {cats.map(cat => (
              <NavLink key={cat.name} to={`/category/${cat.name.toLowerCase()}`}
                className={({isActive}) => `nexus-nav-link${isActive ? ' active' : ''}`}>
                {cat.name}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-1.5 flex-shrink-0 ml-auto lg:ml-0">
            <button onClick={() => setSearchOpen(s => !s)} className="nexus-icon-btn" title="Search">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            </button>
            <button onClick={toggleDark} className="nexus-icon-btn" title="Toggle theme">
              {dark
                ? <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
                : <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
              }
            </button>
            <button className="lg:hidden nexus-icon-btn" onClick={() => setMenuOpen(o => !o)}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                {menuOpen ? <><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></> : <><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></>}
              </svg>
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="lg:hidden nexus-mobile-menu">
            <Link to="/" onClick={() => setMenuOpen(false)} className="nexus-mobile-link">Home</Link>
            {cats.map(c => (
              <Link key={c.name} to={`/category/${c.name.toLowerCase()}`} onClick={() => setMenuOpen(false)} className="nexus-mobile-link">
                <span className="w-2 h-2 rounded-full inline-block mr-2" style={{ background: c.color }}/>{c.icon} {c.name}
              </Link>
            ))}
          </div>
        )}

        {searchOpen && (
          <div className="nexus-search-bar">
            <form onSubmit={handleSearch} className="nexus-container flex gap-2 py-2.5">
              <div className="relative flex-1">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color:'var(--text-muted)' }} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                <input autoFocus value={query} onChange={e => setQuery(e.target.value)}
                  className="form-input pl-9" placeholder="Search articles, topics..."/>
              </div>
              <button type="submit" className="btn-primary px-4 text-sm">Search</button>
              <button type="button" onClick={() => setSearchOpen(false)} className="nexus-icon-btn">✕</button>
            </form>
          </div>
        )}
      </header>

      {/* ── BREAKING TICKER ──────────────────────────────────────────────*/}
      {tickerArticles.length > 0 && (
        <div className="nexus-ticker" style={{ marginBottom: '1cm' }}>
          <span className="nexus-ticker-label">BREAKING</span>
          <div className="overflow-hidden flex-1">
            <span className="ticker-scroll inline-block whitespace-nowrap text-xs font-medium">
              {[...tickerArticles, ...tickerArticles].map((a, i) => (
                <span key={i}>
                  <Link to={`/article/${a.id}`} className="hover:opacity-75 transition-opacity">{a.title}</Link>
                  <span className="mx-5 opacity-30">◆</span>
                </span>
              ))}
            </span>
          </div>
        </div>
      )}

      <main className="flex-1"><Outlet /></main>

      {/* ── SLIM FOOTER (copyright only) ─────────────────────────────── */}
      <footer className="nexus-footer-slim">
        <div className="nexus-container flex flex-wrap items-center justify-between gap-3 py-4">
          <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>© 2025 NEXUS Media. All rights reserved.</span>
          <div className="flex gap-4">
            {['Privacy', 'Terms', 'Cookies'].map(l => (
              <a key={l} href="#" style={{ color: 'var(--text-muted)', fontSize: '0.72rem', transition: 'color 0.15s' }}
                onMouseOver={e => e.target.style.color='var(--accent)'}
                onMouseOut={e => e.target.style.color='var(--text-muted)'}>
                {l}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}