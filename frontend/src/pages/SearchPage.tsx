import { useState } from 'react'

import { AgentProgress } from '../components/AgentProgress'
import { DealResults } from '../components/DealResults'
import { RecentSearches } from '../components/RecentSearches'
import { useSearchStream } from '../hooks/useSearchStream'

const EXAMPLES = ['sony wh-1000xm5', 'iphone 15 128gb', 'boat rockerz 450', 'lenovo loq gaming laptop']

export function SearchPage() {
  const { phase, events, search, error, searchId, run, openExisting } = useSearchStream()
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(5)

  const canSubmit = query.trim().length >= 2 && phase !== 'running'

  function submit(text?: string) {
    const finalQuery = (text ?? query).trim()
    if (finalQuery.length < 2 || phase === 'running') return
    setQuery(finalQuery)
    void run(finalQuery, ['amazon', 'flipkart'], limit)
  }

  return (
    <div className="page-grid" aria-busy={phase === 'running'}>
      <div className="section-stack">
        <section className="card">
          <form
            className="search-form"
            onSubmit={(event) => {
              event.preventDefault()
              submit()
            }}
          >
            <div className="field">
              <label htmlFor="search" className="label">
                What are you looking for?
              </label>
              <input
                id="search"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                autoComplete="off"
                enterKeyHint="search"
                maxLength={500}
                placeholder='e.g. "sony wh-1000xm5 headphones"'
                className="input"
              />
            </div>

            <div className="field">
              <label htmlFor="limit" className="label">
                Results per site
              </label>
              <select
                id="limit"
                value={limit}
                onChange={(event) => setLimit(Number(event.target.value))}
                disabled={phase === 'running'}
                className="select"
                title="Listings to fetch per marketplace"
              >
                <option value={3}>3 / site</option>
                <option value={5}>5 / site</option>
                <option value={8}>8 / site</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={!canSubmit}
              aria-busy={phase === 'running'}
              className="btn btn-primary search-form__submit"
            >
              {phase === 'running' && <span className="spinner" aria-hidden="true" />}
              {phase === 'running' ? 'Searching…' : 'Find best deal'}
            </button>
          </form>

          <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Example searches">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => submit(example)}
                disabled={phase === 'running'}
                className="chip"
              >
                {example}
              </button>
            ))}
          </div>
        </section>

        {phase === 'running' && <AgentProgress events={events} phase={phase} />}

        {phase === 'failed' && (
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
              <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
              <path d="M12 9v4" />
              <path d="M12 17h.01" />
            </svg>
            <div>
              <p className="alert-title">The search failed.</p>
              <p className="alert-body">The comparison could not be completed. This is usually temporary.</p>
              {error && (
                <details className="details">
                  <summary>Technical details</summary>
                  <p className="details__content">{error}</p>
                </details>
              )}
            </div>
          </div>
        )}

        {phase === 'completed' && search && <DealResults search={search} />}

        {events.length > 0 && phase !== 'running' && <AgentProgress events={events} phase={phase} />}
      </div>

      <aside className="page-rail">
        <RecentSearches
          refreshKey={search?.completed_at ?? searchId ?? ''}
          activeId={searchId}
          onOpen={(id) => void openExisting(id)}
        />
        <section className="card prose-card">
          <h2 className="overline mb-2">How it works</h2>
          <p>
            Deal Finder checks Amazon.in and Flipkart, groups the same product across both, and recommends the best value.
            If a source is unavailable, results are clearly labelled as sample data.
          </p>
        </section>
      </aside>
    </div>
  )
}
