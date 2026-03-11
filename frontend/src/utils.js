// src/utils.js
// Categories are stored in KV via /api/categories and cached in localStorage.
// getCategories() returns the localStorage cache (fast, sync).
// loadCategoriesFromAPI() fetches fresh from server and updates cache.

const STORAGE_KEY = 'nexus_categories'

export const DEFAULT_CATS = [
  { name: 'Technology',    color: '#1E73FF', icon: '💻' },
  { name: 'Science',       color: '#7C3AED', icon: '🔬' },
  { name: 'Business',      color: '#059669', icon: '📈' },
  { name: 'Health',        color: '#DC2626', icon: '❤️' },
  { name: 'Lifestyle',     color: '#D97706', icon: '🌿' },
  { name: 'Travel',        color: '#0891B2', icon: '✈️' },
  { name: 'Entertainment', color: '#DB2777', icon: '🎬' },
]

// ── Sync read from localStorage cache (used everywhere synchronously) ──────
export function getCategories() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : DEFAULT_CATS
  } catch { return DEFAULT_CATS }
}

// ── Write to localStorage + broadcast to same-tab listeners ───────────────
export function saveCategories(cats) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cats))
  window.dispatchEvent(new Event('storage'))
}

// ── Fetch from /api/categories and update localStorage cache ──────────────
export async function loadCategoriesFromAPI() {
  try {
    const res = await fetch('/api/categories')
    const data = await res.json()
    if (data.success && Array.isArray(data.categories) && data.categories.length > 0) {
      saveCategories(data.categories)
      return data.categories
    }
  } catch (e) {
    console.warn('Could not load categories from API, using cache:', e)
  }
  return getCategories()
}

// ── Color / icon helpers ───────────────────────────────────────────────────
export function catColor(cat) {
  const found = getCategories().find(c => c.name === cat)
  return found ? found.color : '#1E73FF'
}

export function catIcon(cat) {
  const found = getCategories().find(c => c.name === cat)
  return found ? found.icon : '📰'
}

// ── Legacy proxy exports (keep old imports working) ───────────────────────
export const CAT_COLORS = new Proxy({}, {
  get(_, key)  { return catColor(key) },
  has(_, key)  { return getCategories().some(c => c.name === key) },
  ownKeys()    { return getCategories().map(c => c.name) },
  getOwnPropertyDescriptor(_, key) {
    return { enumerable: true, configurable: true, value: catColor(key) }
  }
})

export function CATEGORIES() { return getCategories().map(c => c.name) }

export function catClass() { return 'cat-dynamic' }

// ── General helpers ───────────────────────────────────────────────────────
export function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function timeAgo(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const h = Math.floor(diff / 3600000)
  if (h < 1)  return 'Just now'
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  if (d < 30) return `${d}d ago`
  return formatDate(iso)
}

export function wordCount(html) {
  return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().split(' ').filter(Boolean).length
}

export function stripHtml(html) {
  return html.replace(/<[^>]*>/g, '').trim()
}

export function slugify(str) {
  return str.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').substring(0, 80)
}
