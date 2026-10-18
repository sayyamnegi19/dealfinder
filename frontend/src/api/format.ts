const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

export function formatPrice(value: string | number | null | undefined): string | null {
  if (value === null || value === undefined || value === '') return null
  const numeric = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(numeric)) return null
  return inr.format(numeric)
}

export function priceNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null
  const numeric = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

export function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  if (!Number.isFinite(then)) return ''
  const seconds = Math.max(1, Math.round((Date.now() - then) / 1000))
  if (seconds < 60) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  return `${days}d ago`
}

export const SITE_META: Record<string, { label: string; className: string }> = {
  amazon: { label: 'Amazon.in', className: 'bg-amber-100 text-amber-900 ring-amber-200' },
  flipkart: { label: 'Flipkart', className: 'bg-blue-100 text-blue-900 ring-blue-200' },
}

export function siteMeta(site: string): { label: string; className: string } {
  return SITE_META[site] ?? { label: site, className: 'bg-slate-100 text-slate-700 ring-slate-200' }
}
