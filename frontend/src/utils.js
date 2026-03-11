// src/utils.js

const STORAGE_KEY = 'nexus_categories'

const DEFAULT_CATS = [
  { name: 'Technology',    color: '#1E73FF', icon: '💻' },
  { name: 'Science',       color: '#7C3AED', icon: '🔬' },
  { name: 'Business',      color: '#059669', icon: '📈' },
  { name: 'Health',        color: '#DC2626', icon: '❤️' },
  { name: 'Lifestyle',     color: '#D97706', icon: '🌿' },
  { name: 'Travel',        color: '#0891B2', icon: '✈️' },
  { name: 'Entertainment', color: '#DB2777', icon: '🎬' },
]

// Always read live from localStorage so any page gets updates instantly
export function getCategories() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : DEFAULT_CATS
  } catch { return DEFAULT_CATS }
}

export function saveCategories(cats) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cats))
}

// Derived helpers — computed fresh each call
export function getCatColors() {
  return Object.fromEntries(getCategories().map(c => [c.name, c.color]))
}

export function getCatIcons() {
  return Object.fromEntries(getCategories().map(c => [c.name, c.icon]))
}

// Keep these as lazy getters so existing imports still work
export const CAT_COLORS = new Proxy({}, {
  get(_, key) { return getCatColors()[key] || '#1E73FF' },
  ownKeys()   { return getCategories().map(c => c.name) },
  has(_, key) { return getCategories().some(c => c.name === key) },
  getOwnPropertyDescriptor(_, key) {
    return { enumerable: true, configurable: true, value: getCatColors()[key] || '#1E73FF' }
  }
})

// CATEGORIES array — always fresh
export function CATEGORIES() { return getCategories().map(c => c.name) }

export function catColor(cat) { return getCatColors()[cat] || '#1E73FF' }
export function catIcon(cat)  { return getCatIcons()[cat]  || '📰' }

export function catClass(cat) {
  // Dynamic: just return a stable class; color applied via inline style
  return 'cat-dynamic'
}

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
