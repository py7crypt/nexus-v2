// src/pages/ArticlePage.jsx
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchArticle, fetchArticles } from '../api'
import { Spinner, LikeButton } from '../components/shared'
import { formatDate, catColor } from '../utils'
import RightSidebar from '../components/RightSidebar'

export default function ArticlePage() {
  const { id } = useParams()

  // ── All hooks must be at the top, before any early returns ──

  const { data, isLoading, error } = useQuery({
    queryKey: ['article', id],
    queryFn:  () => fetchArticle(id),
    enabled:  !!id,
    retry: 1,
  })

  const article = data?.article

  const { data: related } = useQuery({
    queryKey: ['articles', article?.category],
    queryFn:  () => fetchArticles({ category: article?.category, limit: 4 }),
    enabled:  !!article?.category,
  })

  // ── Early returns after all hooks ──
  if (isLoading) return (
    <div className="flex justify-center items-center py-32"><Spinner size="lg"/></div>
  )

  if (error || !article) return (
    <div className="max-w-2xl mx-auto px-5 py-20 text-center">
      <div className="text-5xl mb-4">😕</div>
      <h1 className="font-display text-2xl font-bold mb-3">Article Not Found</h1>
      <p className="text-slate-500 mb-6">This article may have been removed or the link is incorrect.</p>
      <p className="text-xs text-slate-400 mb-6">Article ID: {id}</p>
      <Link to="/" className="btn-primary">← Back to Home</Link>
    </div>
  )

  const a = article

  return (
    <div className="max-w-[1280px] mx-auto px-5 py-8">
      <div className="grid lg:grid-cols-[1fr_320px] gap-10">
        <article>
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-5">
            <Link to="/" className="hover:text-blue-600">Home</Link>
            <span>›</span>
            <Link to={`/category/${a.category?.toLowerCase()}`} className="hover:text-blue-600">{a.category}</Link>
            <span>›</span>
            <span className="text-slate-500 truncate max-w-[200px]">{a.title}</span>
          </div>

          {/* Category badge */}
          <span className="inline-block font-bold uppercase tracking-wide rounded-full text-white text-sm px-3 py-1"
            style={{ background: catColor(a.category) }}>
            {a.category}
          </span>

          <h1 className="font-display text-3xl lg:text-4xl font-black leading-tight mt-3 mb-4">{a.title}</h1>

          {a.excerpt && (
            <p className="text-lg text-slate-500 dark:text-slate-400 leading-relaxed mb-5 font-light">
              {a.excerpt.replace(/<[^>]*>/g, '')}
            </p>
          )}

          {/* Meta */}
          <div className="flex items-center justify-between pb-5 mb-6" style={{ borderBottom: '1px solid var(--border)' }}>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold"
                style={{ background: catColor(a.category) }}>
                {(a.author || 'N')[0].toUpperCase()}
              </div>
              <div>
                <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{a.author}</div>
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{formatDate(a.created_at)}</div>
              </div>
            </div>
            <LikeButton articleId={a.id}/>
          </div>

          {/* Content — rendered exactly as written in the editor, no extra CSS */}
          <div
            className="article-content"
            dangerouslySetInnerHTML={{ __html: a.content }}
          />

          {/* Tags */}
          {a.tags?.length > 0 && (
            <div className="mt-8 pt-6" style={{ borderTop: '1px solid var(--border)' }}>
              <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>Tags</h4>
              <div className="flex flex-wrap gap-2">
                {a.tags.map(tag => (
                  <span key={tag} className="text-xs px-3 py-1 rounded-full"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}>
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* More articles to read */}
          {related?.articles?.filter(r => r.id !== a.id).length > 0 && (
            <div className="mt-10 pt-6" style={{ borderTop: '1px solid var(--border)' }}>
              <h3 className="font-display text-base font-bold mb-4" style={{ color: 'var(--text-primary)' }}>
                More to Read
              </h3>
              <div className="grid sm:grid-cols-2 gap-4">
                {related.articles.filter(r => r.id !== a.id).slice(0, 4).map(r => (
                  <Link key={r.id} to={`/article/${r.id}`}
                    className="group flex gap-3 p-3 rounded-xl transition-all"
                    style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
                    onMouseOver={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.background = 'var(--accent-glow)' }}
                    onMouseOut={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'var(--bg-card)' }}>
                    {r.cover_image && (
                      <div className="w-20 h-16 rounded-lg overflow-hidden flex-shrink-0">
                        <img src={r.cover_image} alt="" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"/>
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: catColor(r.category) }}>
                        {r.category}
                      </span>
                      <h5 className="font-display text-xs font-bold line-clamp-2 leading-snug mt-0.5 group-hover:text-blue-500 transition-colors"
                        style={{ color: 'var(--text-primary)' }}>
                        {r.title}
                      </h5>
                      <span className="text-[10px] mt-1 block" style={{ color: 'var(--text-muted)' }}>
                        {formatDate(r.created_at)}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

        </article>

        <RightSidebar variant="article" article={a}/>
      </div>
    </div>
  )
}