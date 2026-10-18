export type SiteKey = 'amazon' | 'flipkart'

export interface Offer {
  id: number
  site: string
  title: string
  price: string | null
  mrp: string | null
  discount_pct: number | null
  rating: number | null
  reviews: number | null
  url: string
  image_url: string
  seller: string
  in_stock: boolean | null
  source_server: string
  is_sample: boolean
}

export interface ProductGroup {
  id: number
  rank: number
  canonical_name: string
  note: string
  attributes: Record<string, unknown>
  match_confidence: number | null
  best_offer: number | null
  offers: Offer[]
}

export type SearchStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface SearchDetail {
  id: string
  user_query: string
  normalized_query: string
  status: SearchStatus
  requested_sites: string[]
  result_limit: number
  source_servers: string[]
  is_sample: boolean
  error: string
  summary: string
  best_deal_reason: string
  caveats: string[]
  model_used: string
  latency_ms: number | null
  created_at: string
  completed_at: string | null
  groups: ProductGroup[]
}

export interface SearchListItem {
  id: string
  user_query: string
  status: SearchStatus
  is_sample: boolean
  summary: string
  created_at: string
  completed_at: string | null
}

export interface McpServerInfo {
  name: string
  description: string
  kind: 'live' | 'fallback'
  timeout_seconds: number
  tools: Record<string, string> | string | null
}

export interface AttemptInfo {
  server: string
  ok: boolean
  count: number
  error: string
  latency_ms: number
}

export interface ProgressEvent {
  type: string
  payload: Record<string, unknown>
  at: number
}
