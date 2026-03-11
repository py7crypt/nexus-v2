// src/pages/admin/SocialMedia.jsx
import { useState, useEffect } from 'react'
import { toast } from '../../components/shared'

const ICON_MAP = {
  twitter: '𝕏', facebook: '📘', instagram: '📸', linkedin: '💼',
  youtube: '▶️', tiktok: '🎵', snapchat: '👻', pinterest: '📌',
  reddit: '🟠', whatsapp: '💬', telegram: '✈️', discord: '🎮',
}
const COLOR_MAP = {
  twitter: 'border-l-slate-700', facebook: 'border-l-blue-600',
  instagram: 'border-l-pink-500', linkedin: 'border-l-blue-800',
  youtube: 'border-l-red-600', tiktok: 'border-l-slate-900',
  snapchat: 'border-l-yellow-400', pinterest: 'border-l-red-500',
  reddit: 'border-l-orange-500', whatsapp: 'border-l-green-500',
  telegram: 'border-l-sky-500', discord: 'border-l-violet-600',
}
const SUGGESTIONS = ['twitter','facebook','instagram','linkedin','youtube','tiktok','snapchat','pinterest','reddit','whatsapp','telegram','discord']

export default function SocialMedia() {
  // links = [{id, platform, label, url}]
  const [links,   setLinks]   = useState([])
  const [loading, setLoading] = useState(true)
  const [saving,  setSaving]  = useState(false)
  const [newPlat, setNewPlat] = useState('twitter')
  const [newLabel,setNewLabel]= useState('')
  const [newUrl,  setNewUrl]  = useState('')
  const [custom,  setCustom]  = useState(false)

  useEffect(() => {
    fetch('/api/social')
      .then(r => r.json())
      .then(d => {
        if (d.success && Array.isArray(d.links)) setLinks(d.links)
        else if (d.success && d.social) {
          // migrate old flat object format
          const migrated = Object.entries(d.social)
            .filter(([, v]) => v)
            .map(([k, v]) => ({ id: k, platform: k, label: k.charAt(0).toUpperCase() + k.slice(1), url: v }))
          setLinks(migrated)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const save = async (updatedLinks) => {
    setSaving(true)
    try {
      const token = localStorage.getItem('nexus_token') || ''
      const res = await fetch('/api/social', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ links: updatedLinks }),
      })
      const data = await res.json()
      if (data.success) { setLinks(data.links); toast('✅ Saved!', 'success') }
      else toast(`Error: ${data.error}`, 'error')
    } catch (e) { toast(`Error: ${e.message}`, 'error') }
    finally { setSaving(false) }
  }

  const handleAdd = () => {
    const url = newUrl.trim()
    if (!url) { toast('URL is required', 'error'); return }
    const platform = custom ? (newLabel.trim().toLowerCase().replace(/\s+/g,'-') || 'custom') : newPlat
    const label    = newLabel.trim() || platform.charAt(0).toUpperCase() + platform.slice(1)
    const id       = `${platform}-${Date.now()}`
    const updated  = [...links, { id, platform, label, url }]
    setLinks(updated)
    save(updated)
    setNewUrl(''); setNewLabel(''); setNewPlat('twitter'); setCustom(false)
  }

  const handleDelete = (id) => {
    const updated = links.filter(l => l.id !== id)
    setLinks(updated)
    save(updated)
  }

  const handleUrlChange = (id, url) => {
    setLinks(l => l.map(x => x.id === id ? { ...x, url } : x))
  }

  if (loading) return (
    <div className="flex justify-center items-center py-32">
      <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"/>
    </div>
  )

  return (
    <div className="fade-in max-w-2xl">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold">📱 Social Media</h1>
          <p className="text-sm text-slate-400 mt-1">
            Links appear publicly in the share widget on every article page.
            <span className="ml-2 text-blue-500 font-medium">{links.length} link{links.length !== 1 ? 's' : ''}</span>
          </p>
        </div>
        <button onClick={() => save(links)} disabled={saving}
          className="btn-primary text-sm py-2 px-5 flex-shrink-0">
          {saving ? '⏳ Saving...' : '💾 Save All'}
        </button>
      </div>

      {/* Add new link */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 mb-5">
        <h2 className="text-sm font-bold mb-4">➕ Add New Link</h2>
        <div className="flex flex-wrap gap-3 mb-3">
          <div className="flex items-center gap-2">
            <input type="checkbox" id="custom-toggle" checked={custom} onChange={e => setCustom(e.target.checked)}
              className="w-4 h-4 rounded border-slate-300"/>
            <label htmlFor="custom-toggle" className="text-xs text-slate-500 cursor-pointer">Custom platform</label>
          </div>
        </div>
        <div className="grid sm:grid-cols-[1fr_1fr_auto] gap-3 items-end">
          <div>
            <label className="form-label">Platform</label>
            {custom
              ? <input value={newLabel} onChange={e => setNewLabel(e.target.value)}
                  placeholder="e.g. Threads" className="form-input text-sm"/>
              : <select value={newPlat} onChange={e => { setNewPlat(e.target.value); setNewLabel('') }}
                  className="form-select text-sm">
                  {SUGGESTIONS.map(p => (
                    <option key={p} value={p}>
                      {ICON_MAP[p] || '🔗'} {p.charAt(0).toUpperCase() + p.slice(1)}
                    </option>
                  ))}
                </select>
            }
          </div>
          <div>
            <label className="form-label">URL</label>
            <input value={newUrl} onChange={e => setNewUrl(e.target.value)}
              placeholder="https://..." className="form-input text-sm" type="url"
              onKeyDown={e => e.key === 'Enter' && handleAdd()}/>
          </div>
          <button onClick={handleAdd}
            className="btn-primary text-sm py-2.5 px-4 flex-shrink-0">
            Add
          </button>
        </div>
      </div>

      {/* Existing links */}
      {links.length === 0
        ? <div className="text-center py-12 text-slate-400 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
            <div className="text-4xl mb-3">📭</div>
            <p className="text-sm">No social links yet. Add one above.</p>
          </div>
        : <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 divide-y divide-slate-100 dark:divide-slate-700">
            {links.map(({ id, platform, label, url }) => {
              const icon  = ICON_MAP[platform] || '🔗'
              const color = COLOR_MAP[platform] || 'border-l-slate-400'
              return (
                <div key={id} className={`flex items-center gap-4 p-4 border-l-4 ${color}`}>
                  <span className="text-xl w-7 text-center flex-shrink-0">{icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">{label}</div>
                    <input value={url}
                      onChange={e => handleUrlChange(id, e.target.value)}
                      className="form-input text-sm py-1.5"
                      type="url" placeholder="https://..."/>
                  </div>
                  {url && (
                    <a href={url} target="_blank" rel="noreferrer"
                      className="text-xs text-blue-500 hover:underline flex-shrink-0">↗</a>
                  )}
                  <button onClick={() => handleDelete(id)}
                    className="text-slate-300 hover:text-red-500 transition-colors flex-shrink-0 text-lg leading-none"
                    title="Delete">
                    ×
                  </button>
                </div>
              )
            })}
          </div>
      }

      <p className="text-xs text-slate-400 mt-4 text-center">
        Served publicly via <code className="font-mono">/api/social</code>
      </p>
    </div>
  )
}
