import { useEffect, useRef } from 'react'

import { formatRelativeTime } from '../api/format'
import type { ProgressEvent } from '../api/types'
import type { Phase } from '../hooks/useSearchStream'

interface Line {
  key: string
  tone: 'info' | 'ok' | 'fail' | 'muted'
  text: string
}

function humanize(events: ProgressEvent[]): Line[] {
  const lines: Line[] = []
  events.forEach((event, index) => {
    const key = `${event.at}-${index}`
    const p = event.payload as Record<string, any>
    switch (event.type) {
      case 'status':
        lines.push({ key, tone: 'info', text: 'Connected — starting the agent…' })
        break
      case 'tool_started':
        lines.push({
          key,
          tone: 'info',
          text: `Searching ${(p.sites as string[])?.map((s: string) => (s === 'amazon' ? 'Amazon.in' : 'Flipkart')).join(' & ')} for “${p.query}”…`,
        })
        break
      case 'search_completed': {
        const attempts = (p.attempts ?? []) as Array<Record<string, any>>
        if (p.server) {
          lines.push({
            key,
            tone: 'ok',
            text: `Got ${p.new_listings} listing${p.new_listings === 1 ? '' : 's'} from ${p.server}${p.is_sample ? ' (sample data)' : ''}`,
          })
        } else {
          lines.push({ key, tone: 'fail', text: 'No listings returned for that query' })
        }
        for (const [i, attempt] of attempts.entries()) {
          lines.push({
            key: `${key}-${i}`,
            tone: attempt.ok ? 'muted' : 'fail',
            text: attempt.ok
              ? `${attempt.server}: ${attempt.count} listing${attempt.count === 1 ? '' : 's'} in ${(attempt.latency_ms / 1000).toFixed(1)}s`
              : `${attempt.server}: unavailable (${String(attempt.error).slice(0, 90)})`,
          })
        }
        break
      }
      case 'result_ready':
        lines.push({ key, tone: 'ok', text: 'Comparing offers and picking the best deal…' })
        break
      case 'error':
        lines.push({ key, tone: 'fail', text: String(p.message ?? 'Agent error') })
        break
      default:
        break
    }
  })
  return lines
}

const TONES: Record<Line['tone'], string> = {
  info: 'log-line',
  ok: 'log-line log-line--ok',
  fail: 'log-line log-line--fail',
  muted: 'log-line log-line--muted',
}

function LogLines({ lines, phase }: { lines: Line[]; phase: Phase }) {
  return (
    <>
      {lines.length === 0 && phase === 'running' && <p className="text-meta">Querying marketplaces via MCP servers…</p>}
      {lines.map((line) => (
        <p key={line.key} className={TONES[line.tone]}>
          {line.text}
        </p>
      ))}
    </>
  )
}

export function AgentProgress({ events, phase }: { events: ProgressEvent[]; phase: Phase }) {
  const lines = humanize(events)
  const logRef = useRef<HTMLDivElement | null>(null)
  const lastEventAt =
    events.length > 0 ? formatRelativeTime(new Date(events[events.length - 1].at).toISOString()) : ''

  useEffect(() => {
    const log = logRef.current
    if (log) log.scrollTop = log.scrollHeight
  }, [lines.length])

  const announcement =
    phase === 'running' ? 'Agent is working.' : phase === 'completed' ? 'Search complete.' : phase === 'failed' ? 'Search failed.' : ''

  if (phase !== 'running' && lines.length === 0) return null

  if (phase !== 'running' && lines.length > 0) {
    return (
      <section className="card status-panel" aria-label="Agent progress">
        <p className="sr-only" role="status" aria-live="polite">
          {announcement}
        </p>
        <details className="status-details">
          <summary className="status-summary">
            <span className="status-dot status-dot--muted" aria-hidden="true" />
            <span className="card-title">Activity log</span>
            <span className="text-meta">{lastEventAt}</span>
          </summary>
          <div className="log mt-3" ref={logRef}>
            <LogLines lines={lines} phase={phase} />
          </div>
        </details>
      </section>
    )
  }

  return (
    <section className="card status-panel" aria-label="Agent progress">
      <p className="sr-only" role="status" aria-live="polite">
        {announcement}
      </p>

      <div className="status-header">
        <span className={phase === 'running' ? 'status-dot is-running' : 'status-dot status-dot--muted'} aria-hidden="true" />
        <h2 className="card-title">{phase === 'running' ? 'Agent working…' : 'Agent log'}</h2>
        <span className="text-meta">{lastEventAt}</span>
      </div>

      <div className="log" ref={logRef}>
        <LogLines lines={lines} phase={phase} />
      </div>
    </section>
  )
}
