import { priceNumber, formatPrice, siteMeta } from '../api/format'
import type { Offer, ProductGroup, SearchDetail } from '../api/types'

function SiteBadge({ site }: { site: string }) {
  const meta = siteMeta(site)
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${meta.className}`}>
      {meta.label}
    </span>
  )
}

function SampleBadge() {
  return (
    <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700 ring-1 ring-amber-200">
      sample
    </span>
  )
}

function OfferRow({ offer, isLowest }: { offer: Offer; isLowest: boolean }) {
  const price = formatPrice(offer.price)
  const mrp = formatPrice(offer.mrp)
  const showMrp = mrp && price && offer.mrp !== offer.price

  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-slate-100 bg-white px-3 py-2.5">
      <div className="min-w-0">
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <SiteBadge site={offer.site} />
          {offer.is_sample && <SampleBadge />}
          {isLowest && (
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 ring-1 ring-emerald-200">
              lowest price
            </span>
          )}
          {offer.rating != null && (
            <span className="text-[11px] text-slate-500">
              ★ {offer.rating.toFixed(1)}
              {offer.reviews != null && offer.reviews > 0 ? ` · ${offer.reviews.toLocaleString('en-IN')} ratings` : ''}
            </span>
          )}
        </div>
        <a
          href={offer.url}
          target="_blank"
          rel="noreferrer"
          className="line-clamp-2 text-sm text-slate-800 hover:text-blue-700 hover:underline"
          title={offer.title}
        >
          {offer.title}
        </a>
      </div>
      <div className="shrink-0 text-right">
        <div className="text-sm font-semibold text-slate-900">{price ?? '—'}</div>
        {showMrp && (
          <div className="text-xs text-slate-400">
            <span className="line-through">{mrp}</span>
            {offer.discount_pct != null && (
              <span className="ml-1 font-medium text-emerald-600">{Math.round(offer.discount_pct)}% off</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function GroupCard({ group }: { group: ProductGroup }) {
  const sorted = [...group.offers].sort(
    (a, b) => (priceNumber(a.price) ?? Number.POSITIVE_INFINITY) - (priceNumber(b.price) ?? Number.POSITIVE_INFINITY),
  )
  const lowestId = sorted[0]?.id

  return (
    <section className="rounded-2xl border border-slate-200 bg-slate-50/60 p-4">
      <h3 className="text-sm font-semibold text-slate-900">{group.canonical_name}</h3>
      {group.note && <p className="mt-0.5 text-xs text-slate-500">{group.note}</p>}
      <div className="mt-3 space-y-2">
        {sorted.map((offer) => (
          <OfferRow key={offer.id} offer={offer} isLowest={offer.id === lowestId} />
        ))}
      </div>
    </section>
  )
}

function BestDealCard({ search, bestOffer, group }: { search: SearchDetail; bestOffer: Offer; group: ProductGroup }) {
  const price = formatPrice(bestOffer.price)
  const prices = group.offers.map((o) => priceNumber(o.price)).filter((n): n is number => n != null)
  const maxPrice = prices.length ? Math.max(...prices) : null
  const bestPrice = priceNumber(bestOffer.price)
  const savings = maxPrice != null && bestPrice != null && maxPrice > bestPrice ? maxPrice - bestPrice : null

  return (
    <section className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-5 shadow-sm">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-lg">🏆</span>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-emerald-800">Best deal</h2>
      </div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="mb-1 flex items-center gap-2">
            <SiteBadge site={bestOffer.site} />
            {bestOffer.is_sample && <SampleBadge />}
            {bestOffer.rating != null && <span className="text-xs text-slate-500">★ {bestOffer.rating.toFixed(1)}</span>}
          </div>
          <a
            href={bestOffer.url}
            target="_blank"
            rel="noreferrer"
            className="text-base font-medium text-slate-900 hover:text-emerald-700 hover:underline"
          >
            {bestOffer.title}
          </a>
          {search.best_deal_reason && <p className="mt-2 max-w-xl text-sm text-slate-600">{search.best_deal_reason}</p>}
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-emerald-700">{price ?? '—'}</div>
          {savings != null && <div className="text-xs font-medium text-emerald-600">saves {formatPrice(savings)} vs highest offer</div>}
          <a
            href={bestOffer.url}
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-flex items-center rounded-lg bg-emerald-600 px-3.5 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
          >
            Check deal →
          </a>
        </div>
      </div>
    </section>
  )
}

export function DealResults({ search }: { search: SearchDetail }) {
  let bestOffer: Offer | null = null
  let bestGroup: ProductGroup | null = null
  for (const group of search.groups) {
    if (group.best_offer == null) continue
    const offer = group.offers.find((o) => o.id === group.best_offer)
    if (offer) {
      bestOffer = offer
      bestGroup = group
      break
    }
  }

  return (
    <div className="space-y-4">
      {search.is_sample && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          ⚠️ Live marketplace data was unavailable for this search — the listings below are illustrative <strong>sample data</strong>.
        </div>
      )}

      {bestOffer && bestGroup && <BestDealCard search={search} bestOffer={bestOffer} group={bestGroup} />}

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">Summary</h2>
        <p className="text-sm leading-relaxed text-slate-700">{search.summary}</p>
        {search.caveats.length > 0 && (
          <ul className="mt-3 space-y-1">
            {search.caveats.map((caveat, index) => (
              <li key={index} className="text-xs text-slate-500">
                • {caveat}
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-[11px] text-slate-400">
          {search.model_used && <>model: {search.model_used} · </>}
          {search.latency_ms != null && <>{Math.round(search.latency_ms / 1000)}s · </>}
          {search.source_servers.length > 0 && <>via {search.source_servers.join(', ')}</>}
        </p>
      </section>

      {search.groups.length > 0 ? (
        <div className="space-y-4">
          {[...search.groups]
            .sort((a, b) => a.rank - b.rank)
            .map((group) => (
              <GroupCard key={group.id} group={group} />
            ))}
        </div>
      ) : (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500 shadow-sm">
          No product groups were found for this query. Try more specific terms (include the brand and model).
        </section>
      )}
    </div>
  )
}
