// src/pages/admin/SocialMedia.jsx
import { useState, useEffect } from 'react'
import { toast } from '../../components/shared'

const PLATFORM_PRESETS = {
  twitter:   { icon: 'https://cdn.simpleicons.org/x/000000',          color: 'border-l-slate-700' },
  facebook:  { icon: 'https://cdn.simpleicons.org/facebook/1877F2',   color: 'border-l-blue-600'  },
  instagram: { icon: 'https://cdn.simpleicons.org/instagram/E4405F',  color: 'border-l-pink-500'  },
  linkedin:  { icon: 'https://cdn.simpleicons.org/linkedin/0A66C2',   color: 'border-l-blue-800'  },
  youtube:   { icon: 'https://cdn.simpleicons.org/youtube/FF0000',    color: 'border-l-red-600'   },
  tiktok:    { icon: 'https://cdn.simpleicons.org/tiktok/000000',     color: 'border-l-slate-900' },
  snapchat:  { icon: 'https://cdn.simpleicons.org/snapchat/FFFC00',   color: 'border-l-yellow-400'},
  pinterest: { icon: 'https://cdn.simpleicons.org/pinterest/E60023',  color: 'border-l-red-500'   },
  reddit:    { icon: 'https://cdn.simpleicons.org/reddit/FF4500',     color: 'border-l-orange-500'},
  whatsapp:  { icon: 'https://cdn.simpleicons.org/whatsapp/25D366',   color: 'border-l-green-500' },
  telegram:  { icon: 'https://cdn.simpleicons.org/telegram/26A5E4',   color: 'border-l-sky-500'   },
  discord:   { icon: 'https://cdn.simpleicons.org/discord/5865F2',    color: 'border-l-violet-600'},
}
const SUGGESTIONS = Object.keys(PLATFORM_PRESETS)

function IconPreview({ src }) {
  if (!src) return <div className="w-7 h-7 rounded bg-slate-200 dark:bg-slate-600 flex items-center justify-center text-slate-400 text-xs">?</div>
  return (
    <img src={src} alt="icon"
      className="w-7 h-7 object-contain rounded"
      onError={e => { e.target.style.display='none'; e.target.nextSibling.style.display='flex' }}
    />
  )
}

export default function SocialMedia() {
  const [links,    setLinks]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [saving,   setSaving]   = useState(false)
  const [newPlat,  setNewPlat]  = useState('twitter')
  const [newLabel, setNewLabel] = useState('')
  const [newIcon,  setNewIcon]  = useState(PLATFORM_PRESETS.twitter.icon)
  const [newUrl,   setNewUrl]   = useState('')
  const [custom,   setCustom]   = useState(false)

  useEffect(() => {
    fetch('/api/social')
      .then(r => r.json())
      .then(d => {
        if (d.success && Array.isArray(d.links)) setLinks(d.links)
        else if (d.success && d.social) {
          const migrated = Object.entries(d.social)
            .filter(([,v]) => v)
            .map(([k,v]) => ({
              id: k, platform: k,
              label: k.charAt(0).toUpperCase() + k.slice(1),
              icon: PLATFORM_PRESETS[k]?.icon || '',
              url: v,
            }))
          setLinks(migrated)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handlePlatChange = (p) => {
    setNewPlat(p)
    setNewIcon(PLATFORM_PRESETS[p]?.icon || '')
    setNewLabel('')
  }

  const save = async (updatedLinks) => {
    setSaving(true)
    try {
      const token = localStorage.getItem('nexus_token') || ''
      const res = await fetch('/api/social', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
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
    const icon     = newIcon.trim() || PLATFORM_PRESETS[platform]?.icon || ''
    const id       = `${platform}-${Date.now()}`
    const updated  = [...links, { id, platform, label, icon, url }]
    setLinks(updated)
    save(updated)
    setNewUrl(''); setNewLabel(''); setNewPlat('twitter')
    setNewIcon(PLATFORM_PRESETS.twitter.icon); setCustom(false)
  }

  const handleDelete = (id) => { const u = links.filter(l=>l.id!==id); setLinks(u); save(u) }
  const updateField  = (id, field, val) => setLinks(ls => ls.map(l => l.id===id ? {...l,[field]:val} : l))

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
            Links appear in the share widget and site footer.
            <span className="ml-2 text-blue-500 font-medium">{links.length} link{links.length!==1?'s':''}</span>
          </p>
        </div>
        <button onClick={() => save(links)} disabled={saving} className="btn-primary text-sm py-2 px-5 flex-shrink-0">
          {saving ? '⏳ Saving...' : '💾 Save All'}
        </button>
      </div>

      {/* Add new */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 mb-5">
        <h2 className="text-sm font-bold mb-4">➕ Add New Link</h2>
        <div className="flex items-center gap-2 mb-3">
          <input type="checkbox" id="custom-toggle" checked={custom} onChange={e=>setCustom(e.target.checked)} className="w-4 h-4 rounded"/>
          <label htmlFor="custom-toggle" className="text-xs text-slate-500 cursor-pointer">Custom platform</label>
        </div>
        <div className="space-y-3">
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="form-label">Platform</label>
              {custom
                ? <input value={newLabel} onChange={e=>setNewLabel(e.target.value)} placeholder="e.g. Threads" className="form-input text-sm"/>
                : <select value={newPlat} onChange={e=>handlePlatChange(e.target.value)} className="form-select text-sm">
                    {SUGGESTIONS.map(p=>(
                      <option key={p} value={p}>{p.charAt(0).toUpperCase()+p.slice(1)}</option>
                    ))}
                  </select>
              }
            </div>
            <div>
              <label className="form-label">Profile URL</label>
              <input value={newUrl} onChange={e=>setNewUrl(e.target.value)} placeholder="https://..." className="form-input text-sm" type="url"
                onKeyDown={e=>e.key==='Enter'&&handleAdd()}/>
            </div>
          </div>
          <div>
            <label className="form-label">Icon Image URL</label>
            <div className="flex gap-2 items-center">
              <div className="w-9 h-9 flex-shrink-0 flex items-center justify-center bg-slate-100 dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 overflow-hidden">
                {newIcon
                  ? <img src={newIcon} alt="" className="w-6 h-6 object-contain" onError={e=>e.target.style.opacity='0'}/>
                  : <span className="text-slate-400 text-xs">?</span>
                }
              </div>
              <input value={newIcon} onChange={e=>setNewIcon(e.target.value)}
                placeholder="https://cdn.simpleicons.org/twitter/1DA1F2"
                className="form-input text-sm flex-1" type="url"/>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Tip: use <a href="https://simpleicons.org" target="_blank" rel="noreferrer" className="text-blue-500 hover:underline">simpleicons.org</a> — format: <code className="font-mono">https://cdn.simpleicons.org/PLATFORM/COLOR</code>
            </p>
          </div>
          <button onClick={handleAdd} className="btn-primary text-sm py-2.5 px-5 w-full justify-center">Add Link</button>
        </div>
      </div>

      {/* List */}
      {links.length===0
        ? <div className="text-center py-12 text-slate-400 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
            <div className="text-4xl mb-3">📭</div>
            <p className="text-sm">No social links yet. Add one above.</p>
          </div>
        : <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 divide-y divide-slate-100 dark:divide-slate-700">
            {links.map(({id,platform,label,icon,url})=>{
              const color = PLATFORM_PRESETS[platform]?.color || 'border-l-slate-400'
              return (
                <div key={id} className={`p-4 border-l-4 ${color}`}>
                  <div className="flex items-center gap-3 mb-2">
                    {/* Icon preview */}
                    <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center bg-slate-100 dark:bg-slate-700 rounded-lg overflow-hidden">
                      {icon
                        ? <img src={icon} alt={label} className="w-5 h-5 object-contain"
                            onError={e=>{ e.target.style.display='none' }}/>
                        : <span className="text-slate-400 text-xs">?</span>
                      }
                    </div>
                    <div className="text-xs font-bold text-slate-500 uppercase tracking-wide flex-1">{label}</div>
                    {url && <a href={url} target="_blank" rel="noreferrer" className="text-xs text-blue-500 hover:underline">↗</a>}
                    <button onClick={()=>handleDelete(id)} className="text-slate-300 hover:text-red-500 transition-colors text-xl leading-none" title="Delete">×</button>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-slate-400 mb-1 block">Profile URL</label>
                      <input value={url} onChange={e=>updateField(id,'url',e.target.value)}
                        className="form-input text-sm py-1.5" type="url" placeholder="https://..."/>
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 mb-1 block">Icon Image URL</label>
                      <input value={icon||''} onChange={e=>updateField(id,'icon',e.target.value)}
                        className="form-input text-sm py-1.5" type="url" placeholder="https://cdn.simpleicons.org/..."/>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
      }
      <p className="text-xs text-slate-400 mt-4 text-center">Served publicly via <code className="font-mono">/api/social</code></p>
    </div>
  )
}
