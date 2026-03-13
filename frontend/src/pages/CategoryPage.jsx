// src/pages/CategoryPage.jsx
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchArticles } from '../api'
import { ArticleCard, Spinner } from '../components/shared'
import { getCategories, catColor } from '../utils'
import RightSidebar from '../components/RightSidebar'

export default function CategoryPage() {
  const { slug } = useParams()
  const cats = getCategories()
  const category = cats.find(c => c.name.toLowerCase() === slug?.toLowerCase())?.name || slug

  const { data, isLoading } = useQuery({
    queryKey: ['articles', category],
    queryFn: () => fetchArticles({ category, limit: 20 }),
    enabled: !!category,
  })

  const color    = catColor(category)
  const articles = data?.articles || []

  return (
    <div className="nexus-container py-8">

      {/* Two-column layout matching HomePage */}
      <div className="grid lg:grid-cols-[1fr_300px] xl:grid-cols-[1fr_320px] gap-8">

        {/* Articles */}
        <div>
          {isLoading ? (
            <div className="flex justify-center py-20"><Spinner size="lg"/></div>
          ) : articles.length === 0 ? (
            <div className="text-center py-20" style={{ color: 'var(--text-muted)' }}>
              <div className="text-5xl mb-4">📭</div>
              <p className="text-base">No articles in {category} yet.</p>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {articles.map(a => <ArticleCard key={a.id} article={a}/>)}
            </div>
          )}
        </div>

        {/* Shared right sidebar — Newsletter variant */}
        <RightSidebar variant="category"/>
      </div>
    </div>
  )
}