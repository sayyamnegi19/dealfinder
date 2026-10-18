import { useCallback, useEffect, useRef, useState } from 'react'

import { createSearch, getSearch, streamUrl } from '../api/client'
import type { ProgressEvent, SearchDetail } from '../api/types'

const SERVER_EVENTS = [
  'status',
  'tool_started',
  'search_completed',
  'llm_tool_call',
  'llm_tool_result',
  'result_ready',
  'error',
  'done',
] as const

export type Phase = 'idle' | 'running' | 'completed' | 'failed'

export interface StreamState {
  phase: Phase
  searchId: string | null
  events: ProgressEvent[]
  search: SearchDetail | null
  error: string | null
}

const INITIAL: StreamState = {
  phase: 'idle',
  searchId: null,
  events: [],
  search: null,
  error: null,
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

export function useSearchStream() {
  const [state, setState] = useState<StreamState>(INITIAL)
  const esRef = useRef<EventSource | null>(null)
  const finishedRef = useRef(false)

  const stop = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
  }, [])

  const run = useCallback(
    async (query: string, sites: string[], limit: number) => {
      stop()
      finishedRef.current = false
      setState({ ...INITIAL, phase: 'running' })

      let searchId: string
      try {
        const created = await createSearch({ query, sites, limit })
        searchId = created.id
      } catch (error) {
        setState((s) => ({ ...s, phase: 'failed', error: errorMessage(error) }))
        return
      }

      setState((s) => ({ ...s, searchId }))
      const source = new EventSource(streamUrl(searchId))
      esRef.current = source

      for (const type of SERVER_EVENTS) {
        source.addEventListener(type, (rawEvent) => {
          const event = rawEvent as MessageEvent
          if (!event.data) {
            // Native EventSource connection error (no payload).
            if (!finishedRef.current && source.readyState === EventSource.CLOSED) {
              setState((s) =>
                s.phase === 'running'
                  ? { ...s, phase: 'failed', error: 'Connection to the agent stream was lost.' }
                  : s,
              )
            }
            return
          }

          let payload: Record<string, unknown> = {}
          try {
            payload = JSON.parse(event.data) as Record<string, unknown>
          } catch {
            // keep empty payload
          }

          if (type === 'done') {
            finishedRef.current = true
            stop()
            const search = (payload.search ?? null) as SearchDetail | null
            setState((s) => ({
              ...s,
              phase: payload.status === 'completed' ? 'completed' : 'failed',
              search,
              error:
                payload.status === 'completed'
                  ? null
                  : (search?.error || s.error || 'The search failed.'),
            }))
            return
          }

          if (type === 'error') {
            setState((s) => ({ ...s, error: String(payload.message ?? 'Agent error') }))
          }

          setState((s) => ({ ...s, events: [...s.events, { type, payload, at: Date.now() }] }))
        })
      }
    },
    [stop],
  )

  const openExisting = useCallback(async (id: string) => {
    stop()
    finishedRef.current = true
    setState({ ...INITIAL, phase: 'running', searchId: id })
    try {
      const search = await getSearch(id)
      setState({
        phase: search.status === 'completed' ? 'completed' : search.status === 'failed' ? 'failed' : 'running',
        searchId: id,
        events: [],
        search,
        error: search.status === 'failed' ? search.error : null,
      })
    } catch (error) {
      setState({ ...INITIAL, phase: 'failed', error: errorMessage(error) })
    }
  }, [stop])

  const reset = useCallback(() => {
    stop()
    setState(INITIAL)
  }, [stop])

  useEffect(() => stop, [stop])

  return { ...state, run, openExisting, reset }
}
