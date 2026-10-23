import { useEffect, useState } from 'react'

import { getRecentSearches } from '../api/client'
import { formatRelativeTime } from '../api/format'
import type { SearchListItem } from '../api/types'

type LoadStatus = 'loading' | 'ready' | 'error'

export function RecentSearches({
  refreshKey,
  activeId,
  onOpen,
}: {
  refreshKey: string
  activeId: string | null
  onOpen: (id: string) => void
}) {
  const [items, setItems] = useState<SearchListItem[]>([])
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    getRecentSearches()
      .then((data) => {
        if (cancelled) return
        setItems(data)
        setStatus('ready')
      })
      .catch(() => {
        if (cancelled) return
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [refreshKey, reloadKey])

  return (
    <section className="card" aria-labelledby="recent-searches-title">
      <h2 id="recent-searches-title" className="overline mb-3">
        Recent searches
      </h2>

      {status === 'loading' && items.length === 0 && (
        <div className="space-y-2" aria-busy="true">
          <span className="sr-only">Loading recent searches</span>
          <div className="skeleton h-3 w-4/5" />
          <div className="skeleton h-3 w-3/5" />
          <div className="skeleton h-3 w-2/3" />
        </div>
      )}

      {status === 'error' && items.length === 0 && (
        <div className="alert alert-danger" role="alert">
          <svg
            className="alert-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v4" />
            <path d="M12 16h.01" />
          </svg>
          <div>
            <p className="alert-title">Couldn’t load recent searches</p>
            <p className="alert-body">Check your connection and try again.</p>
            <button
              type="button"
              className="btn btn-secondary btn-sm alert-action"
              onClick={() => {
                setStatus('loading')
                setReloadKey((key) => key + 1)
              }}
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {status === 'ready' && items.length === 0 && (
        <div className="empty-state empty-state--compact">
          <p className="empty-state__title">No searches yet</p>
          <p className="empty-state__body">Your recent comparisons will appear here.</p>
        </div>
      )}

      {items.length > 0 && (
        <ul className="recent-list">
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onOpen(item.id)}
                aria-current={activeId === item.id ? 'true' : undefined}
                className={`recent-item ${activeId === item.id ? 'is-active' : ''}`}
              >
                <span className="recent-item__query">{item.user_query}</span>
                <span className="recent-item__meta">
                  {item.is_sample && <span className="recent-item__status recent-item__status--sample">sample</span>}
                  {item.status === 'failed' && (
                    <span className="recent-item__status recent-item__status--failed">failed</span>
                  )}
                  {formatRelativeTime(item.created_at)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
