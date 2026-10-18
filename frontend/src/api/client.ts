import type { McpServerInfo, SearchDetail, SearchListItem } from './types'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      if (body?.detail) detail = String(body.detail)
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail)
  }
  return (await response.json()) as T
}

export interface CreateSearchInput {
  query: string
  sites: string[]
  limit: number
}

export function createSearch(input: CreateSearchInput): Promise<{ id: string; status: string }> {
  return request('/api/search/', { method: 'POST', body: JSON.stringify(input) })
}

export function getSearch(id: string): Promise<SearchDetail> {
  return request(`/api/search/${id}/`)
}

export function getRecentSearches(): Promise<SearchListItem[]> {
  return request('/api/searches/')
}

export function getMcpHealth(): Promise<{ servers: McpServerInfo[] }> {
  return request('/api/health/mcp/')
}

export function streamUrl(searchId: string): string {
  return `${API_BASE}/api/search/${searchId}/stream`
}
