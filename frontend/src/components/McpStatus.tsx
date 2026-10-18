import { useEffect, useState } from 'react'

import { getMcpHealth } from '../api/client'
import type { McpServerInfo } from '../api/types'

export function McpStatus() {
  const [servers, setServers] = useState<McpServerInfo[]>([])

  useEffect(() => {
    let cancelled = false
    getMcpHealth()
      .then((data) => {
        if (!cancelled) setServers(data.servers)
      })
      .catch(() => {
        // health is best-effort
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (servers.length === 0) return null

  return (
    <div className="hidden items-center gap-3 sm:flex">
      {servers.map((server) => (
        <span key={server.name} className="inline-flex items-center gap-1.5 text-[11px] text-slate-500" title={server.description}>
          <span
            className={`inline-block h-2 w-2 rounded-full ${server.kind === 'live' ? 'bg-emerald-500' : 'bg-slate-300'}`}
          />
          {server.name}
          <span className="text-slate-300">({server.kind})</span>
        </span>
      ))}
    </div>
  )
}
