import { useEffect, useState } from 'react'

import { getMcpHealth } from '../api/client'
import type { McpServerInfo } from '../api/types'

type LoadStatus = 'loading' | 'ready' | 'error'

export function McpStatus() {
  const [servers, setServers] = useState<McpServerInfo[]>([])
  const [status, setStatus] = useState<LoadStatus>('loading')

  useEffect(() => {
    let cancelled = false
    getMcpHealth()
      .then((data) => {
        if (cancelled) return
        setServers(data.servers)
        setStatus('ready')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (status === 'loading') return null

  if (status === 'error') {
    return (
      <div
        className="mcp-status"
        role="status"
        aria-label="Marketplace connection status unavailable"
        title="Could not load marketplace connection status"
      >
        <span className="status-dot status-dot--muted" aria-hidden="true" />
        <span>Status n/a</span>
      </div>
    )
  }

  if (servers.length === 0) return null

  const sourceCount = `${servers.length} ${servers.length === 1 ? 'source' : 'sources'}`
  const detail = servers.map((server) => `${server.name} (${server.kind})`).join(', ')
  const hasLiveSource = servers.some((server) => server.kind === 'live')

  return (
    <div className="mcp-status" role="group" aria-label={`Marketplace data sources: ${detail}`}>
      <span className="mcp-status__mobile">
        <span className={hasLiveSource ? 'status-dot status-dot--brand' : 'status-dot status-dot--muted'} aria-hidden="true" />
        {sourceCount}
      </span>

      <span className="mcp-status__list">
        {servers.map((server) => (
          <span key={server.name} className="mcp-status__item" title={server.description}>
            <span
              className={server.kind === 'live' ? 'status-dot status-dot--brand' : 'status-dot status-dot--muted'}
              aria-hidden="true"
            />
            <span>{server.name}</span>
            <span className="mcp-status__kind">({server.kind})</span>
          </span>
        ))}
      </span>
    </div>
  )
}
