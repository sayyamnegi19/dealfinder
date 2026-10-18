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
  info: 'text-slate-700',
  ok: 'text-emerald-700',
  fail: 'text-rose-600',
  muted: 'text-slate-400',
}

export function AgentProgress({ events, phase }: { events: ProgressEvent[]; phase: Phase }) {
  const lines = humanize(events)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [lines.length])

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        {phase === 'running' ? (
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
          </span>
        ) : (
          <span className="inline-flex h-2.5 w-2.5 rounded-full bg-slate-300" />
        )}
        <h2 className="text-sm font-semibold text-slate-900">
          {phase === 'running' ? 'Agent working…' : 'Agent log'}
        </h2>
        <span className="text-xs text-slate-400">
          {events.length > 0 ? formatRelativeTime(new Date(events[events.length - 1].at).toISOString()) : ''}
        </span>
      </div>

      <div className="max-h-64 space-y-1.5 overflow-y-auto pr-1">
        {lines.length === 0 && phase === 'running' && (
          <p className="text-sm text-slate-500">Querying marketplaces via MCP servers…</p>
        )}
        {lines.map((line) => (
          <p key={line.key} className={`text-sm ${TONES[line.tone]}`}>
            {line.text}
          </p>
        ))}
        <div ref={bottomRef} />
      </div>
    </section>
  )
}
