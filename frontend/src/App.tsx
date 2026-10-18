import { McpStatus } from './components/McpStatus'
import { SearchPage } from './pages/SearchPage'

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3.5">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">🛍️</span>
            <div>
              <h1 className="text-base font-bold leading-tight text-slate-900">Deal Finder</h1>
              <p className="text-[11px] leading-tight text-slate-400">AI price comparison · Amazon.in vs Flipkart</p>
            </div>
          </div>
          <McpStatus />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <SearchPage />
      </main>

      <footer className="border-t border-slate-200 py-6">
        <p className="mx-auto max-w-6xl px-4 text-[11px] text-slate-400">
          Development build · prices are fetched live from marketplaces via MCP servers and may change · scraping is
          best-effort, personal/low-volume use only.
        </p>
      </footer>
    </div>
  )
}
