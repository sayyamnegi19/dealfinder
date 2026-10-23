import { McpStatus } from './components/McpStatus'
import { SearchPage } from './pages/SearchPage'

export default function App() {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>

      <header className="site-header">
        <div className="container-page site-header__inner">
          <a className="brand" href="/" aria-label="Deal Finder home">
            <span className="brand-mark" aria-hidden="true">
              <svg
                className="icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M20.59 13.41 12 22 2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82Z" />
                <circle cx="7" cy="7" r="1.4" />
              </svg>
            </span>
            <div className="brand-copy">
              <h1 className="brand-title">Deal Finder</h1>
              <p className="brand-tagline">Live prices · Amazon.in vs Flipkart</p>
            </div>
          </a>

          <McpStatus />
        </div>
      </header>

      <main id="main" className="container-page page-main" tabIndex={-1}>
        <SearchPage />
      </main>

      <footer className="site-footer">
        <div className="container-page site-footer__inner">
          <p>Prices are fetched live and may change. Confirm the final price and seller on the marketplace.</p>
          <p>Personal, low-volume price comparison.</p>
        </div>
      </footer>
    </div>
  )
}
