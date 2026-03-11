// src/components/NewsScraperModal.jsx
// Scrape real news from Google News RSS — no AI needed
import { useState, useEffect } from 'react'
import { fetchNews, fetchArticleMeta } from '../api'
import { getCategories } from '../utils'

const CATS = ['All', ...Object.keys({
  Technology:1, Science:1, Business:1, Health:1,
  Politics:1, Sports:1, Entertainment:1, Travel:1, Culture:1
})]

export default function NewsScraperModal({ onFill, onClose }) {
  const [articles,  setArticles]  = useState([])
  const [loading,   setLoading]   = useState(true)
  const [fetching,  setFetching]  = useState(null)  // URL being fetched
  const [category,  setCategory]  = useState('All')
  const [search,    setSearch]    = useState('')
  const [error,     setError]     = useState('')

  const load = async (cat, q) => {
    setLoading(true); setError('')
    try {
      const res = await fetchNews({
        q:        q    || undefined,
        category: (cat && cat !== 'All') ? cat : undefined,
      })
      if (res.success) setArticles(res.articles)
      else setError(res.error || 'Failed to load news')
    } catch(e) { setError(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load('All', '') }, [])

  const handleCategoryChange = (cat) => {
    setCategory(cat)
    setSearch('')
    load(cat, '')
  }

  const handleSearch = (e) => {
    e.preventDefault()
    load(category, search)
  }

  const handlePick = async (article) => {
    setFetching(article.url)
    try {
      // Try to get full meta from the article page
      const res = await fetchArticleMeta(article.url)
      const meta = res.success ? res.meta : {}

      // Guess category from current filter or fallback
      const cat = category !== 'All' ? category : ''

      onFill({
        title:       meta.title       || article.title,
        excerpt:     meta.excerpt     || article.excerpt,
        cover_image: meta.cover_image || '',
        category:    cat,
        seo_title:   (meta.title || article.title).slice(0, 60),
        seo_description: (meta.excerpt || article.excerpt || '').slice(0, 155),
        // Put content preview into editor as a starting point
        content: meta.content_preview
          ? `<p>${meta.content_preview.split('. ').slice(0, 8).join('. ')}.</p>\n<p><em>Source: <a href="${article.url}" target="_blank">${article.source}</a></em></p>`
          : `<p>${article.excerpt}</p>\n<p><em>Source: <a href="${article.url}" target="_blank">${article.source}</a></em></p>`,
        tags: article.source ? [article.source.toLowerCase().replace(/\s+/g, '-')] : [],
      })
    } catch {
      // Fallback to RSS data only
      onFill({
        title:       article.title,
        excerpt:     article.excerpt,
        cover_image: '',
        category:    category !== 'All' ? category : '',
        content:     `<p>${article.excerpt}</p>\n<p><em>Source: <a href="${article.url}" target="_blank">${article.source}</a></em></p>`,
        tags:        article.source ? [article.source.toLowerCase().replace(/\s+/g,'-')] : [],
      })
    } finally {
      setFetching(null)
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-12 px-4"
      style={{ background: 'rgba(0,0,0,0.6)' }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[80vh] flex flex-col overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex-shrink-0">
          <div>
            <h2 className="text-lg font-bold">📰 Live News Feed</h2>
            <p className="text-xs text-slate-400 mt-0.5">Pick a real article from Google News to import as a draft</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-2xl leading-none">×</button>
        </div>

        {/* Search + Category filter */}
        <div className="px-6 py-3 border-b border-slate-200 dark:border-slate-700 flex-shrink-0 space-y-2">
          <form onSubmit={handleSearch} className="flex gap-2">
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search news (e.g. climate, AI, elections...)"
              className="form-input text-sm flex-1"/>
            <button type="submit" className="btn-primary text-sm py-2 px-4">Search</button>
            <button type="button" onClick={() => { setSearch(''); load(category, '') }}
              className="btn-outline text-sm py-2 px-3">↺</button>
          </form>
          <div className="flex gap-1.5 flex-wrap">
            {CATS.map(cat => (
              <button key={cat} onClick={() => handleCategoryChange(cat)}
                className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
                  category === cat
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'
                }`}>
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Articles list */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-16 gap-3 text-slate-400">
              <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"/>
              Loading news...
            </div>
          ) : error ? (
            <div className="text-center py-16">
              <div className="text-4xl mb-3">😕</div>
              <p className="text-sm text-red-500">{error}</p>
              <button onClick={() => load(category, search)} className="mt-3 btn-outline text-sm py-2 px-4">Retry</button>
            </div>
          ) : articles.length === 0 ? (
            <div className="text-center py-16 text-slate-400">
              <div className="text-4xl mb-3">📭</div>
              <p className="text-sm">No articles found</p>
            </div>
          ) : (
            <div className="space-y-2">
              {articles.map((a, i) => (
                <button key={i} onClick={() => handlePick(a)}
                  disabled={!!fetching}
                  className="w-full text-left p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-all group disabled:opacity-60">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-semibold leading-snug group-hover:text-blue-600 transition-colors line-clamp-2">
                        {a.title}
                      </div>
                      {a.excerpt && (
                        <div className="text-xs text-slate-400 mt-1 line-clamp-2">{a.excerpt}</div>
                      )}
                      <div className="flex items-center gap-3 mt-2">
                        {a.source && (
                          <span className="text-xs font-medium text-blue-500">{a.source}</span>
                        )}
                        {a.pub_date && (
                          <span className="text-xs text-slate-400">{new Date(a.pub_date).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex-shrink-0 text-xs text-blue-500 font-bold opacity-0 group-hover:opacity-100 transition-opacity mt-1">
                      {fetching === a.url
                        ? <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"/>
                        : 'Import →'
                      }
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-400 flex-shrink-0">
          Powered by Google News RSS · {articles.length} articles loaded · Content is from original sources
        </div>
      </div>
    </div>
  )
}
