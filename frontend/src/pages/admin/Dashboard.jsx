// src/pages/admin/Dashboard.jsx
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchAllArticles } from '../../api'
import { Spinner, StatusPill } from '../../components/shared'
import { formatDate, catColor, getCategories } from '../../utils'

function StatCard({ icon, value, label, bg }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl mb-3 ${bg}`}>{icon}</div>
      <div className="text-2xl font-bold mb-0.5">{value ?? '—'}</div>
      <div className="text-xs text-slate-500 font-medium">{label}</div>
    </div>
  )
}

export default function Dashboard() {
  // Fetch ALL articles and compute stats client-side — avoids cold-start memory reset
  const { data, isLoading } = useQuery({
    queryKey: ['admin-articles-all'],
    queryFn: () => fetchAllArticles({ status: 'all', limit: 200 }),
    refetchInterval: 15000,
  })

  const articles  = data?.articles || []
  const published = articles.filter(a => a.status === 'published')
  const drafts    = articles.filter(a => a.status === 'draft')
  const totalViews = articles.reduce((s, a) => s + (a.views || 0), 0)

  const by_cat = {}
  articles.forEach(a => { by_cat[a.category] = (by_cat[a.category] || 0) + 1 })

  const recent = [...articles].sort((a, b) => (b.created_at || '').localeCompare(a.created_at || '')).slice(0, 5)
  const maxCat = Math.max(...Object.values(by_cat), 1)

  if (isLoading) return <div className="flex justify-center items-center min-h-64"><Spinner size="lg"/></div>

  return (
    <div className="fade-in">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Dashboard</h1>
        <p className="text-sm text-slate-400">Welcome back to NEXUS CMS</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon="📰" value={articles.length}             label="Total Articles"  bg="bg-blue-50 dark:bg-blue-950"/>
        <StatCard icon="✅" value={published.length}            label="Published"       bg="bg-green-50 dark:bg-green-950"/>
        <StatCard icon="📝" value={drafts.length}               label="Drafts"          bg="bg-yellow-50 dark:bg-yellow-950"/>
        <StatCard icon="👁" value={totalViews.toLocaleString()} label="Total Views"     bg="bg-purple-50 dark:bg-purple-950"/>
      </div>

      <div className="grid lg:grid-cols-[1fr_320px] gap-6">
        {/* Recent Articles */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-700">
            <h2 className="font-semibold text-sm">Recent Articles</h2>
            <Link to="/admin/articles" className="text-xs text-blue-600 hover:underline font-medium">View All →</Link>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {!recent.length ? (
              <div className="px-5 py-10 text-center text-slate-400 text-sm">
                No articles yet. <Link to="/admin/articles/new" className="text-blue-600 hover:underline">Create one →</Link>
              </div>
            ) : recent.map(a => (
              <Link key={a.id} to={`/admin/articles/edit/${a.id}`}
                className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                  style={{ background: catColor(a.category) }}>
                  {a.category?.[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium truncate">{a.title}</h4>
                  <p className="text-xs text-slate-400">{a.category} · {formatDate(a.created_at)} · {a.views || 0} views</p>
                </div>
                <StatusPill status={a.status}/>
              </Link>
            ))}
          </div>
          <div className="px-5 py-3 border-t border-slate-100 dark:border-slate-700">
            <Link to="/admin/articles/new" className="btn-primary text-xs py-2 w-full justify-center">+ New Article</Link>
          </div>
        </div>

        {/* Category breakdown */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h2 className="font-semibold text-sm mb-4">By Category</h2>
          {!Object.keys(by_cat).length ? (
            <p className="text-slate-400 text-sm text-center py-6">No data yet</p>
          ) : Object.entries(by_cat).sort((a,b) => b[1]-a[1]).map(([cat, count]) => (
            <div key={cat} className="mb-3">
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium">{cat}</span>
                <span className="font-bold">{count}</span>
              </div>
              <div className="h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${count / maxCat * 100}%`, background: catColor(cat) }}/>
              </div>
            </div>
          ))}
          <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-700">
            <Link to="/admin/ai" className="flex items-center gap-2 text-sm font-semibold text-violet-600 hover:underline">
              🤖 Generate with AI →
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
