// src/components/PublicLayout.jsx
import { useState, useEffect } from 'react'
import { Outlet, Link, NavLink, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { getCategories } from '../utils'
import { fetchArticles } from '../api'

export default function PublicLayout() {
  const { dark, toggleDark } = useApp()
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [searchOpen, setSearch] = useState(false)
  const [query, setQuery] = useState('')
  const [cats, setCats]     = useState(getCategories())
  const [tickerArticles, setTickerArticles] = useState([])
  const [socialLinks,    setSocialLinks]    = useState([])

  useEffect(() => {
    fetch('/api/social')
      .then(r => r.json())
      .then(d => { if (d.success && Array.isArray(d.links)) setSocialLinks(d.links) })
      .catch(() => {})
  }, [])

  // Fetch last 10 published articles for breaking news ticker
  useEffect(() => {
    fetchArticles({ limit: 10 })
      .then(d => { if (d.articles?.length) setTickerArticles(d.articles) })
      .catch(() => {})
  }, [])
  const navigate = useNavigate()

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 60)
    window.addEventListener('scroll', fn, { passive: true })
    return () => window.removeEventListener('scroll', fn)
  }, [])

  // Keep categories in sync with localStorage changes
  useEffect(() => {
    const sync = () => setCats(getCategories())
    window.addEventListener('storage', sync)
    const t = setInterval(sync, 2000)
    return () => { window.removeEventListener('storage', sync); clearInterval(t) }
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    if (query.trim()) { navigate(`/?q=${encodeURIComponent(query.trim())}`); setSearch(false) }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className={`sticky top-0 z-50 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 transition-shadow ${scrolled ? 'shadow-md' : 'shadow-sm'}`}>
        <div className="max-w-[1280px] mx-auto px-5 h-16 flex items-center gap-5">
          <Link to="/" className="font-display text-2xl font-black tracking-tight flex-shrink-0">
            NEX<span className="text-blue-600">US</span>
          </Link>
          <nav className="hidden lg:flex items-center gap-1 flex-1 overflow-x-auto scrollbar-none">
            <NavLink to="/" end className={({isActive}) => `text-xs font-semibold px-3 py-1.5 rounded-md transition-colors ${isActive ? 'text-blue-600 bg-blue-50 dark:bg-blue-950' : 'text-slate-500 hover:text-blue-600 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
              Home
            </NavLink>
            {cats.map(cat => (
              <NavLink key={cat.name} to={`/category/${cat.name.toLowerCase()}`}
                className={({isActive}) => `text-xs font-semibold px-3 py-1.5 rounded-md whitespace-nowrap transition-colors ${isActive ? 'text-blue-600 bg-blue-50 dark:bg-blue-950' : 'text-slate-500 hover:text-blue-600 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
                {cat.icon} {cat.name}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button onClick={() => setSearch(s => !s)} className="p-2 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">🔍</button>
            <button onClick={toggleDark} className="p-2 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">{dark ? '☀️' : '🌙'}</button>
            <button className="lg:hidden p-2 rounded-lg text-slate-500" onClick={() => setMenuOpen(o => !o)}>☰</button>
          </div>
        </div>

        {menuOpen && (
          <div className="lg:hidden bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 px-5 py-3 flex flex-col gap-1">
            <Link to="/" onClick={() => setMenuOpen(false)} className="py-2 px-3 text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-blue-600 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800">Home</Link>
            {cats.map(c => (
              <Link key={c.name} to={`/category/${c.name.toLowerCase()}`} onClick={() => setMenuOpen(false)}
                className="py-2 px-3 text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-blue-600 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800">
                {c.icon} {c.name}
              </Link>
            ))}
          </div>
        )}

        {searchOpen && (
          <div className="bg-slate-50 dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 px-5 py-3">
            <form onSubmit={handleSearch} className="max-w-xl mx-auto flex gap-2">
              <input autoFocus value={query} onChange={e => setQuery(e.target.value)}
                className="form-input" placeholder="Search articles, topics..."/>
              <button type="button" onClick={() => setSearch(false)} className="px-3 text-slate-400 hover:text-slate-600">✕</button>
            </form>
          </div>
        )}
      </header>

      {tickerArticles.length > 0 && (
        <div className="bg-blue-600 text-white flex items-center h-9 overflow-hidden">
          <span className="bg-black/20 px-4 h-full flex items-center text-xs font-bold tracking-widest flex-shrink-0 border-r border-white/20">BREAKING</span>
          <div className="overflow-hidden flex-1">
            <span className="ticker-scroll inline-block whitespace-nowrap text-xs font-medium py-2">
              {[...tickerArticles, ...tickerArticles].map((a, i) => (
                <span key={i}>
                  <Link to={`/article/${a.id}`}
                    className="hover:underline hover:text-blue-200 transition-colors cursor-pointer">
                    {a.title}
                  </Link>
                  <span className="mx-4 opacity-60">•</span>
                </span>
              ))}
            </span>
          </div>
        </div>
      )}

      <main className="flex-1"><Outlet /></main>

      <footer className="bg-slate-50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-800 mt-16">
        <div className="max-w-[1280px] mx-auto px-5 py-12 grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <div className="font-display text-2xl font-black mb-3">NEX<span className="text-blue-600">US</span></div>
            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">A modern digital media platform covering technology, science, business, health, and culture.</p>
          </div>
          <div>
            <h4 className="text-sm font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-4">Categories</h4>
            <ul className="space-y-2">
              {cats.map(c => (
                <li key={c.name}><Link to={`/category/${c.name.toLowerCase()}`} className="text-sm text-slate-500 hover:text-blue-600 transition-colors">{c.icon} {c.name}</Link></li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-4">Resources</h4>
            <ul className="space-y-2 text-sm text-slate-500">
              {['About NEXUS','Editorial Policy','Write for Us','Advertise','Careers','Contact'].map(i => (
                <li key={i}><a href="#" className="hover:text-blue-600 transition-colors">{i}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-4">Follow Us</h4>
            <div className="flex gap-2 flex-wrap">
              {socialLinks.length > 0
                ? socialLinks.map(l => (
                    <a key={l.id} href={l.url} target="_blank" rel="noreferrer"
                      title={l.label}
                      className="w-9 h-9 flex items-center justify-center border border-slate-200 dark:border-slate-700 rounded-lg text-slate-500 hover:bg-blue-600 hover:text-white hover:border-blue-600 transition-all text-base">
                      {l.icon || '🔗'}
                    </a>
                  ))
                : ['𝕏','f','◎','in','▶'].map((icon, i) => (
                    <a key={i} href="#" className="w-9 h-9 flex items-center justify-center border border-slate-200 dark:border-slate-700 rounded-lg text-slate-500 hover:bg-blue-600 hover:text-white hover:border-blue-600 transition-all text-sm font-bold">{icon}</a>
                  ))
              }
            </div>
          </div>
        </div>
        <div className="border-t border-slate-200 dark:border-slate-800 py-5">
          <div className="max-w-[1280px] mx-auto px-5 flex justify-between items-center text-xs text-slate-400">
            <span>© 2025 NEXUS Media. All rights reserved.</span>
            <div className="flex gap-4">{['Privacy','Terms','Cookies'].map(l => <a key={l} href="#" className="hover:text-blue-600">{l}</a>)}</div>
          </div>
        </div>
      </footer>
    </div>
  )
}
