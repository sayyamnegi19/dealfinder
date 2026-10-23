import { formatPrice, formatRelativeTime, priceNumber, siteMeta } from '../api/format'
import type { Offer, ProductGroup, SearchDetail } from '../api/types'

function SiteBadge({ site }: { site: string }) {
  const meta = siteMeta(site)
  return <span className={`badge ${meta.className}`}>{meta.label}</span>
}

function SampleBadge() {
  return <span className="badge badge-warning">Sample data</span>
}

function StockBadge({ inStock, showInStock = false }: { inStock: boolean | null; showInStock?: boolean }) {
  if (inStock == null || (inStock && !showInStock)) return null
  return <span className={`badge ${inStock ? 'badge-success' : 'badge-danger'}`}>{inStock ? 'In stock' : 'Out of stock'}</span>
}

function Rating({ rating, reviews }: { rating: number | null; reviews: number | null }) {
  if (rating == null) return null
  return (
    <span
      className="text-meta"
      aria-label={`Rated ${rating.toFixed(1)} out of 5${reviews != null && reviews > 0 ? ` from ${reviews.toLocaleString('en-IN')} ratings` : ''}`}
    >
      <span aria-hidden="true">★</span> {rating.toFixed(1)}
      {reviews != null && reviews > 0 ? ` · ${reviews.toLocaleString('en-IN')} ratings` : ''}
    </span>
  )
}

function OfferRow({ offer, isLowest }: { offer: Offer; isLowest: boolean }) {
  const price = formatPrice(offer.price)
  const mrp = formatPrice(offer.mrp)
  const showMrp = mrp && price && offer.mrp !== offer.price

  return (
    <div className="offer-row">
      <div className="min-w-0">
        <div className="offer-meta">
          <SiteBadge site={offer.site} />
          {offer.is_sample && <SampleBadge />}
          {isLowest && <span className="badge badge-brand">Lowest price</span>}
          <Rating rating={offer.rating} reviews={offer.reviews} />
          <StockBadge inStock={offer.in_stock} />
        </div>
        <a href={offer.url} target="_blank" rel="noreferrer" className="offer-title" title={offer.title}>
          {offer.title}
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
        {offer.seller && <p className="offer-seller">Sold by {offer.seller}</p>}
      </div>

      <div className="offer-price">
        <span className="price">{price ?? '—'}</span>
        {showMrp && (
          <span className="offer-price__meta">
            <span className="price-mrp">{mrp}</span>
            {offer.discount_pct != null && <span className="discount">{Math.round(offer.discount_pct)}% off</span>}
          </span>
        )}
      </div>
    </div>
  )
}

function GroupCard({ group }: { group: ProductGroup }) {
  const sorted = [...group.offers].sort(
    (a, b) => (priceNumber(a.price) ?? Number.POSITIVE_INFINITY) - (priceNumber(b.price) ?? Number.POSITIVE_INFINITY),
  )
  const lowestId = sorted.find((offer) => priceNumber(offer.price) != null)?.id

  return (
    <section className="card">
      <div className="group-card__header">
        <div>
          <h3 className="card-title">{group.canonical_name}</h3>
          {group.note && <p className="card-description">{group.note}</p>}
        </div>
        <span className="badge badge-neutral">
          {group.offers.length} {group.offers.length === 1 ? 'offer' : 'offers'}
        </span>
      </div>
      <div>
        {sorted.map((offer) => (
          <OfferRow key={offer.id} offer={offer} isLowest={offer.id === lowestId} />
        ))}
      </div>
    </section>
  )
}

function BestDealCard({ search, bestOffer, group }: { search: SearchDetail; bestOffer: Offer; group: ProductGroup }) {
  const price = formatPrice(bestOffer.price)
  const prices = group.offers.map((offer) => priceNumber(offer.price)).filter((value): value is number => value != null)
  const maxPrice = prices.length ? Math.max(...prices) : null
  const bestPrice = priceNumber(bestOffer.price)
  const savings = maxPrice != null && bestPrice != null && maxPrice > bestPrice ? maxPrice - bestPrice : null
  const savingsLabel = savings != null ? formatPrice(savings) : null

  return (
    <section className="card card-brand">
      <div className="best-deal__header">
        <span className="best-deal__icon" aria-hidden="true">
          <svg
            className="icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="8" r="5" />
            <path d="M8.2 12.4 7 22l5-3 5 3-1.2-9.6" />
          </svg>
        </span>
        <div>
          <h2 className="best-deal__title">Best deal</h2>
          <p className="text-meta">Recommended across the compared marketplaces</p>
        </div>
      </div>

      <div className="best-deal__body">
        <div className="min-w-0">
          <div className="offer-meta">
            <SiteBadge site={bestOffer.site} />
            {bestOffer.is_sample && <SampleBadge />}
            <Rating rating={bestOffer.rating} reviews={bestOffer.reviews} />
            <StockBadge inStock={bestOffer.in_stock} showInStock />
          </div>
          <a href={bestOffer.url} target="_blank" rel="noreferrer" className="offer-title">
            {bestOffer.title}
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
          {bestOffer.seller && <p className="offer-seller">Sold by {bestOffer.seller}</p>}
          {search.best_deal_reason && <p className="summary-copy mt-2">{search.best_deal_reason}</p>}
        </div>

        <div className="best-deal__price">
          <div className="price-display">{price ?? '—'}</div>
          {savingsLabel && <div className="savings">Saves {savingsLabel} vs the highest offer</div>}
          <a href={bestOffer.url} target="_blank" rel="noreferrer" className="btn btn-primary mt-3">
            Check deal
            <svg
              className="icon-sm"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M7 17 17 7" />
              <path d="M7 7h10v10" />
            </svg>
            <span className="sr-only"> (opens in a new tab)</span>
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
    const offer = group.offers.find((item) => item.id === group.best_offer)
    if (offer) {
      bestOffer = offer
      bestGroup = group
      break
    }
  }

  const checkedAt = formatRelativeTime(search.completed_at ?? search.created_at)
  const groupLabel = `${search.groups.length} product ${search.groups.length === 1 ? 'group' : 'groups'}`

  return (
    <div className="section-stack">
      <header className="results-header">
        <div>
          <p className="overline">Search results</p>
          <h2 className="results-title">{search.user_query}</h2>
        </div>
        <p className="text-meta">
          Checked {checkedAt || 'recently'} · {groupLabel}
        </p>
      </header>

      {search.is_sample && (
        <div className="alert alert-warning" role="note">
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
            <p className="alert-title">Live marketplace data was unavailable</p>
            <p className="alert-body">
              The listings below are illustrative <strong>sample data</strong>, not current prices.
            </p>
          </div>
        </div>
      )}

      {bestOffer && bestGroup && <BestDealCard search={search} bestOffer={bestOffer} group={bestGroup} />}

      <section className="card">
        <h2 className="overline">Summary</h2>
        <p className="summary-copy mt-2">{search.summary || 'No summary is available for this search.'}</p>
        {search.caveats.length > 0 && (
          <ul className="caveat-list">
            {search.caveats.map((caveat, index) => (
              <li key={index}>• {caveat}</li>
            ))}
          </ul>
        )}
        {(search.model_used || search.latency_ms != null || search.source_servers.length > 0) && (
          <details className="details">
            <summary>Run details</summary>
            <p className="details__content">
              {search.model_used && <>Model: {search.model_used}. </>}
              {search.latency_ms != null && <>Completed in {Math.round(search.latency_ms / 1000)}s. </>}
              {search.source_servers.length > 0 && <>Sources: {search.source_servers.join(', ')}.</>}
            </p>
          </details>
        )}
      </section>

      {search.groups.length > 0 ? (
        <div className="section-stack">
          {[...search.groups]
            .sort((a, b) => a.rank - b.rank)
            .map((group) => (
              <GroupCard key={group.id} group={group} />
            ))}
        </div>
      ) : (
        <section className="card">
          <div className="empty-state empty-state--compact">
            <p className="empty-state__title">No product groups found</p>
            <p className="empty-state__body">Try a more specific query with the brand and model.</p>
          </div>
        </section>
      )}
    </div>
  )
}
