import { useEffect, useState } from 'react'

import { AgentProgress } from '../components/AgentProgress'
import { DealResults } from '../components/DealResults'
import { RecentSearches } from '../components/RecentSearches'
import { useSearchStream } from '../hooks/useSearchStream'

const EXAMPLES = ['sony wh-1000xm5', 'iphone 15 128gb', 'boat rockerz 450', 'lenovo loq gaming laptop']

export function SearchPage() {
  const { phase, events, search, error, searchId, run, openExisting } = useSearchStream()
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(5)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    if (phase === 'completed' || phase === 'failed') setRefreshKey((key) => key + 1)
  }, [phase])

  const canSubmit = query.trim().length >= 2 && phase !== 'running'

  function submit(text?: string) {
    const finalQuery = (text ?? query).trim()
    if (finalQuery.length < 2 || phase === 'running') return
    setQuery(finalQuery)
    void run(finalQuery, ['amazon', 'flipkart'], limit)
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_300px]">
      <div className="space-y-5">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <label htmlFor="search" className="mb-2 block text-sm font-medium text-slate-700">
            What are you looking for?
          </label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              id="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') submit()
              }}
              placeholder='e.g. "sony wh-1000xm5 headphones"'
              className="w-full flex-1 rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none ring-emerald-500/30 placeholder:text-slate-400 focus:border-emerald-500 focus:ring-4"
            />
            <div className="flex items-center gap-3">
              <select
                value={limit}
                onChange={(event) => setLimit(Number(event.target.value))}
                className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-600 outline-none focus:border-emerald-500"
                title="Listings to fetch per marketplace"
              >
                <option value={3}>3 / site</option>
                <option value={5}>5 / site</option>
                <option value={8}>8 / site</option>
              </select>
              <button
                type="button"
                onClick={() => submit()}
                disabled={!canSubmit}
                className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {phase === 'running' ? 'Searching…' : 'Find best deal'}
              </button>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => submit(example)}
                disabled={phase === 'running'}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600 transition hover:border-slate-300 hover:bg-slate-100 disabled:opacity-40"
              >
                {example}
              </button>
            ))}
          </div>
        </div>

        {(phase === 'running' || events.length > 0) && <AgentProgress events={events} phase={phase} />}

        {phase === 'failed' && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
            <p className="font-semibold">The search failed.</p>
            {error && <p className="mt-1 text-rose-600">{error}</p>}
            <p className="mt-2 text-xs text-rose-500">
              Tip: check that the backend is running and the MCP servers are reachable (see /api/health/mcp/?probe=1).
            </p>
          </div>
        )}

        {phase === 'completed' && search && <DealResults search={search} />}
      </div>

      <aside className="space-y-5">
        <RecentSearches refreshKey={refreshKey} activeId={searchId} onOpen={(id) => void openExisting(id)} />
        <section className="rounded-2xl border border-slate-200 bg-white p-4 text-xs leading-relaxed text-slate-500 shadow-sm">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">How it works</h2>
          <p>
            An AI agent queries live marketplace data through MCP servers, groups identical products, and recommends the
            best deal. If a live site blocks the scraper, the pool fails over to the next MCP server and finally to clearly
            labelled sample data.
          </p>
        </section>
      </aside>
    </div>
  )
}
