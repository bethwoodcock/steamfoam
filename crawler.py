import asyncio
from playwright.async_api import async_playwright
from extractor import extract_games_from_page
from config import BASE_URL, PRICE_FILTER, MAX_PAGES


def build_url(page_number: int) -> str:
    if page_number == 1:
        return f"{BASE_URL}?{PRICE_FILTER}"
    return f"{BASE_URL}?p={page_number}&{PRICE_FILTER}"


async def fetch_all_games() -> list[dict]:
    all_games = []
    page1_anchor = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for page_num in range(1, MAX_PAGES + 1):
            url = build_url(page_num)
            print(f"  Fetching page {page_num}: {url}")

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception as e:
                print(f"  Page {page_num} timed out or errored: {e}")
                break

            games = extract_games_from_page(await page.content())

            if not games:
                print(f"  No games on page {page_num} — stopping.")
                break

            if page_num == 1:
                page1_anchor = games[0]["title"]
                print(f"  Page 1 anchor: '{page1_anchor}'")
            elif games[0]["title"] == page1_anchor:
                print(f"  Page {page_num} matches anchor — loop detected. Stopping.")
                break

            for game in games:
                game["page_found"] = page_num
            all_games.extend(games)
            print(f"  {len(games)} games on page {page_num}. Total: {len(all_games)}")

            await asyncio.sleep(1.5)

        await browser.close()

    print(f"\nCrawl complete. {len(all_games)} games found.")
    return all_games
