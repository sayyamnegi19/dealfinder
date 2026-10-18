"""Amazon.in + Flipkart search MCP server.

Vendored from the open-source project `mcp-india-retail-intelligence`
(https://github.com/balaadityaai/mcp-india-retail-intelligence, MIT license) and
adapted only where necessary:

  * imports now target the FastMCP 4 / MCP 2.x SDK (`from fastmcp import FastMCP`)
    because the published package still imports `mcp.server.fastmcp`, which was
    removed in MCP 2.x;
  * the httpx client uses `proxy=` (httpx >= 0.28 removed `proxies=`).

Scraping and parsing logic is unchanged. Runs as a stdio MCP server:

    python -m mcp_servers.retail_intel_server
"""

import logging
import os
import re
import urllib.parse
from collections import defaultdict
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup
from fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-retail-intelligence")

# Initialize FastMCP Server
mcp = FastMCP("india-retail-intelligence")

# HTTP headers to mimic a genuine desktop browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


def get_client() -> httpx.Client:
    """Helper to configure client with proxies if supplied in environment variables."""
    proxy_url = (
        os.environ.get("RETAIL_INTEL_PROXY")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("HTTPS_PROXY")
    )

    kwargs: Dict[str, Any] = {
        "headers": HEADERS,
        "follow_redirects": True,
        "timeout": 15.0,
        "http2": True,
    }
    if proxy_url:
        logger.info("Initializing HTTP client with proxy configuration.")
        kwargs["proxy"] = proxy_url
        return httpx.Client(**kwargs)
    return httpx.Client(**kwargs)


def clean_price(price_str: str) -> Optional[float]:
    """Helper to clean currency strings and parse them to floats."""
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d.]", "", price_str)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def clean_rating(rating_str: str) -> Optional[float]:
    """Helper to clean rating strings and parse to float."""
    if not rating_str:
        return None
    match = re.search(r"(\d+(\.\d+)?)", rating_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def parse_amazon_html(html: str, limit: int) -> List[Dict[str, Any]]:
    """Helper to parse Amazon search results HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    products = []
    cards = soup.select('div[data-component-type="s-search-result"]')

    for card in cards[: limit * 2]:
        if len(products) >= limit:
            break

        try:
            # Resilient title selection
            title_el = (
                card.select_one("h2.a-text-normal")
                or card.select_one("h2 a span")
                or card.select_one("h2")
            )
            if not title_el:
                continue
            title = title_el.text.strip()

            # Resilient link selection
            link_el = card.select_one("a.a-text-normal") or card.find(
                "a", href=lambda h: h and ("/dp/" in h or "/sspa/" in h or "/gp/" in h)
            )
            if not link_el:
                continue
            href = link_el["href"]
            link = f"https://www.amazon.in{href}" if href.startswith("/") else href

            clean_link = link.split("?")[0] if link else None

            # Resilient price selection
            price_el = (
                card.select_one("span.a-price span.a-offscreen")
                or card.select_one("span.a-price span.a-price-whole")
                or card.select_one("span.a-price-whole")
            )
            price_str = price_el.text.strip() if price_el else None
            price = clean_price(price_str)

            mrp_el = card.select_one("span.a-price.a-text-price span.a-offscreen")
            mrp_str = mrp_el.text.strip() if mrp_el else None
            mrp = clean_price(mrp_str)

            discount_pct = None
            if mrp and price and mrp > price:
                discount_pct = round(((mrp - price) / mrp) * 100, 1)

            rating_el = card.select_one("span.a-icon-alt")
            rating_str = rating_el.text.strip() if rating_el else None
            rating = clean_rating(rating_str)

            reviews_el = card.select_one("span.a-size-base.s-underline-text")
            reviews_str = reviews_el.text.strip() if reviews_el else "0"
            reviews_count = (
                int(re.sub(r"\D", "", reviews_str)) if re.sub(r"\D", "", reviews_str) else 0
            )

            image_el = card.select_one("img.s-image")
            image_url = image_el["src"] if image_el and "src" in image_el.attrs else None

            products.append(
                {
                    "platform": "Amazon India",
                    "title": title,
                    "price": price,
                    "mrp": mrp or price,
                    "discount_percentage": discount_pct or 0.0,
                    "rating": rating,
                    "reviews_count": reviews_count,
                    "url": clean_link,
                    "image_url": image_url,
                }
            )
        except Exception as e:  # noqa: BLE001 - scraper must never crash on one card
            logger.debug(f"Error parsing Amazon product card: {e}")
            continue

    return products


def scrape_amazon_via_playwright(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Attempts local browser automation fallback for Amazon India using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright is not installed. Cannot use browser automation fallback.")
        return []

    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.amazon.in/s?k={encoded_query}"
    logger.info("Attempting browser automation fallback for Amazon India via Playwright...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                is_mobile=False,
                has_touch=False,
                locale="en-US",
            )
            page = context.new_page()

            # Hide webdriver flag
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # Go to Amazon search page
            page.goto(url, timeout=30000)

            # Wait for search results or brief timeout
            try:
                page.wait_for_selector(
                    'div[data-component-type="s-search-result"]', timeout=8000
                )
            except Exception:
                logger.warning(
                    "Search results selector did not load within timeout. Checking page content."
                )

            html = page.content()
            title = page.title()
            browser.close()

            # Specific captcha check
            if "robot check" in title.lower() or "enter the characters you see below" in html.lower():
                logger.error("Amazon served a captcha block even via local browser automation.")
                return []

            products = parse_amazon_html(html, limit)
            if not products:
                logger.warning(
                    "No products parsed from retrieved Amazon HTML. Page might be blocked or empty."
                )
            return products

    except Exception as e:  # noqa: BLE001
        logger.error(f"Error occurred during Playwright Amazon scraping: {e}")
        return []


def scrape_amazon_india(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Scrapes Amazon.in search results for a given query using HTTP. Falls back to Playwright if blocked."""
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.amazon.in/s?k={encoded_query}"

    logger.info(f"Scraping Amazon India for query: '{query}'")

    is_blocked = False
    try:
        with get_client() as client:
            response = client.get(url)

            if response.status_code != 200:
                logger.error(f"Amazon returned status code {response.status_code}")
                is_blocked = True
            elif (
                "captcha" in response.text.lower()
                or "robot" in response.text.lower()
                or "verification" in response.text.lower()
            ):
                logger.warning("Amazon served a verification/captcha block on standard HTTP request.")
                is_blocked = True
            else:
                products = parse_amazon_html(response.text, limit)
                if products:
                    return products
                else:
                    is_blocked = True
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error occurred while connecting to Amazon India via HTTP: {e}")
        is_blocked = True

    # Try browser automation fallback if blocked
    if is_blocked:
        try:
            import playwright  # noqa: F401

            return scrape_amazon_via_playwright(query, limit)
        except ImportError:
            logger.warning(
                "Amazon standard HTTP request blocked and Playwright is not installed. "
                "Install Playwright ('pip install playwright && playwright install') or "
                "configure RETAIL_INTEL_PROXY to bypass."
            )
            return []

    return []


def scrape_flipkart(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Scrapes Flipkart search results for a given query using a resilient grouped parser."""
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.flipkart.com/search?q={encoded_query}"

    logger.info(f"Scraping Flipkart for query: '{query}'")

    try:
        with get_client() as client:
            response = client.get(url)

            if response.status_code != 200:
                logger.error(f"Flipkart returned status code {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            # Find all links with /p/ which represent products
            links = soup.find_all("a", href=lambda href: href and "/p/" in href)
            if not links:
                logger.warning("No product links found on Flipkart.")
                return []

            # Group tags by normalized product URL
            product_groups = defaultdict(list)
            for link_tag in links:
                href = link_tag.get("href", "")
                if not href:
                    continue
                url_base = href.split("?")[0]
                full_url = f"https://www.flipkart.com{url_base}"
                product_groups[full_url].append(link_tag)

            products = []
            for prod_url, tags in product_groups.items():
                if len(products) >= limit:
                    break

                title = None
                image_url = None
                prices_found: List[str] = []
                rating = None
                reviews_count = 0

                for tag in tags:
                    # Check for image
                    img = tag.find("img")
                    if img:
                        # Prefer lazy loaded source over placeholder SVG base64
                        img_src = img.get("src")
                        img_data_src = img.get("data-src")
                        if img_data_src and not img_data_src.startswith("data:"):
                            image_url = img_data_src
                        elif img_src and not img_src.startswith("data:"):
                            image_url = img_src

                        if img.get("alt"):
                            title = img.get("alt").strip()

                    # Check for text information
                    text = tag.text.strip()
                    if text:
                        if "₹" in text:
                            # Extract deepest elements with ₹
                            for el in tag.find_all(True):
                                if "₹" in el.text and not any(
                                    "₹" in c.text for c in el.find_all(True)
                                ):
                                    prices_found.append(el.text.strip())
                            if not prices_found:
                                prices_found.append(text)
                        else:
                            # Verify if it's a potential title block (length > 8, not rating counts)
                            if (
                                not re.match(r"^\d\.\d$", text)
                                and len(text) > 8
                                and not title
                            ):
                                if "ratings" not in text.lower() and "reviews" not in text.lower():
                                    title = text

                    # Extract ratings and reviews counts
                    for el in tag.find_all(["span", "div"]):
                        txt = el.text.strip()
                        if re.match(r"^\d\.\d$", txt):
                            val = float(txt)
                            if 3.0 <= val <= 5.0:
                                rating = val
                        # Check for reviews/ratings count string
                        if (
                            "ratings" in txt.lower()
                            or "reviews" in txt.lower()
                            or "ratings &" in txt.lower()
                        ):
                            rev_match = re.search(
                                r"([\d,]+)\s*(Ratings|Reviews|Reviews?)", txt, re.IGNORECASE
                            )
                            if rev_match:
                                reviews_count = int(rev_match.group(1).replace(",", ""))

                # Parse and clean prices
                cleaned_prices = []
                for p in prices_found:
                    cleaned = re.sub(r"[^\d]", "", p)
                    if cleaned:
                        cleaned_prices.append(float(cleaned))

                unique_prices = sorted(list(set(cleaned_prices)))

                price = None
                mrp = None
                if len(unique_prices) == 1:
                    price = unique_prices[0]
                elif len(unique_prices) >= 2:
                    price = unique_prices[0]
                    mrp = unique_prices[1]

                # Generate fallback title from URL slug if not found
                if not title:
                    path_parts = prod_url.split("/")
                    if len(path_parts) > 3:
                        title = path_parts[3].replace("-", " ").title()

                products.append(
                    {
                        "platform": "Flipkart",
                        "title": title or "Flipkart Product",
                        "price": price,
                        "mrp": mrp or price,
                        "discount_percentage": (
                            round(((mrp - price) / mrp) * 100, 1)
                            if mrp and price and mrp > price
                            else 0.0
                        ),
                        "rating": rating,
                        "reviews_count": reviews_count,
                        "url": prod_url,
                        "image_url": image_url,
                    }
                )

            return products

    except Exception as e:  # noqa: BLE001
        logger.error(f"Error occurred while connecting to Flipkart: {e}")
        return []


# --- MCP Tool Registrations ---


@mcp.tool()
def search_amazon(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search and retrieve product details from Amazon India.

    Args:
        query: The search keywords for the e-commerce product.
        limit: The maximum number of product records to retrieve (default is 5).

    Returns:
        A list of dictionaries containing title, price, MRP, discount percentage,
        rating, reviews count, URL, and image URL.
    """
    return scrape_amazon_india(query, limit)


@mcp.tool()
def search_flipkart(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search and retrieve product details from Flipkart.

    Args:
        query: The search keywords for the e-commerce product.
        limit: The maximum number of product records to retrieve (default is 5).

    Returns:
        A list of dictionaries containing title, price, MRP, discount percentage,
        rating, reviews count, URL, and image URL.
    """
    return scrape_flipkart(query, limit)


@mcp.tool()
def compare_prices(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Compare products and price points side-by-side across Amazon India and Flipkart.

    Args:
        query: The product name or search keywords to compare.
        limit: The number of top products to fetch from each platform (default is 5).

    Returns:
        A dictionary with separate lists of results from Amazon India and Flipkart,
        and a sorted comparison list ordered by price (lowest first).
    """
    amazon_results = scrape_amazon_india(query, limit)
    flipkart_results = scrape_flipkart(query, limit)

    # Merge and filter valid items (items with prices)
    all_items = []
    for item in amazon_results + flipkart_results:
        if item.get("price") is not None:
            all_items.append(item)

    # Sort unified results by price ascending (lowest price first)
    sorted_by_price = sorted(all_items, key=lambda x: x["price"])

    return {
        "query": query,
        "amazon_india_results": amazon_results,
        "flipkart_results": flipkart_results,
        "best_deals_ranked": sorted_by_price,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
