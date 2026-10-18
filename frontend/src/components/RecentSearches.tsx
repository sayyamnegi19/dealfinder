import { useEffect, useState } from 'react'

import { getRecentSearches } from '../api/client'
import { formatRelativeTime } from '../api/format'
import type { SearchListItem } from '../api/types'

export function RecentSearches({
  refreshKey,
  activeId,
  onOpen,
}: {
  refreshKey: number
  activeId: string | null
  onOpen: (id: string) => void
}) {
  const [items, setItems] = useState<SearchListItem[]>([])

  useEffect(() => {
    let cancelled = false
    getRecentSearches()
      .then((data) => {
        if (!cancelled) setItems(data)
      })
      .catch(() => {
        // best-effort
      })
    return () => {
      cancelled = true
    }
  }, [refreshKey])

  if (items.length === 0) return null

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Recent searches</h2>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onOpen(item.id)}
              className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm transition ${
                activeId === item.id ? 'bg-slate-100 text-slate-900' : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <span className="min-w-0 flex-1 truncate">{item.user_query}</span>
              <span className="flex shrink-0 items-center gap-2 text-[11px] text-slate-400">
                {item.is_sample && <span className="text-amber-500">sample</span>}
                {item.status === 'failed' && <span className="text-rose-500">failed</span>}
                {formatRelativeTime(item.created_at)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
