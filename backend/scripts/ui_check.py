"""Headless UI smoke test for the Deal Finder frontend (Playwright).

Usage:
    .venv/bin/python scripts/ui_check.py [output_dir]
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:5173"
QUERY = "sony wh-1000xm5 headphones"


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1100})

        console_errors: list[str] = []
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
        )

        page.goto(URL, timeout=30_000)
        page.wait_for_timeout(1200)
        page.screenshot(path=str(out_dir / "01-home.png"), full_page=True)
        print("STEP 1: home loaded, title =", page.title())

        # Start a search.
        page.fill("#search", QUERY)
        page.get_by_role("button", name="Find best deal").click()
        page.wait_for_selector("text=Agent working", timeout=20_000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out_dir / "02-agent-running.png"), full_page=True)
        print("STEP 2: search started, agent running UI visible")

        # Wait for the result (agent run may take a while: LLM + scrapers).
        page.wait_for_selector("h2:has-text('Best deal')", timeout=240_000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out_dir / "03-results.png"), full_page=True)
        print("STEP 3: results rendered")

        best_price = page.locator(".price-display").first.inner_text().strip()
        summary = page.locator("section:has(h2:has-text('Summary')) p").first.inner_text().strip()
        sites = {
            "amazon": page.locator("text=Amazon.in").count(),
            "flipkart": page.locator("text=Flipkart").count(),
        }
        recent = page.locator("text=Recent searches").count()

        print("BEST PRICE:", best_price)
        print("SUMMARY:", summary[:280])
        print("SITE BADGES:", sites)
        print("RECENT SEARCHES WIDGET:", "yes" if recent else "no")
        print("CONSOLE ERRORS:", console_errors[:5] or "none")

        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
