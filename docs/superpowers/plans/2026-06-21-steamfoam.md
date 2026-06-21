# SteamFoam Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a weekly crawler that tracks Steam games under £4 on loaded.com, detects new listings and price changes, and writes results to Google Sheets.

**Architecture:** Playwright fetches paginated HTML; BeautifulSoup parses game cards into structured dicts; a diff engine compares the crawl against the last Sheets snapshot and produces a changelog; gspread writes the full updated list and appends history events. The CSS selectors are confirmed against the live DOM before any code is written, so the extractor works on first run.

**Tech Stack:** Python 3.11+, Playwright (Chromium), BeautifulSoup4, gspread, google-auth, python-dotenv

---

## File Map

| File | Responsibility |
|---|---|
| `config.py` | Env vars + constants (URLs, sheet names, limits) |
| `extractor.py` | Parse raw HTML → list of `{title, price_gbp, url}` |
| `crawler.py` | Playwright pagination + loop-back detection |
| `diff.py` | Compare crawl vs Sheets snapshot → write list + history events |
| `sheets.py` | gspread read/write for Games and History tabs |
| `run.py` | Entry point — orchestrates all modules |
| `tests/test_extractor.py` | Unit tests for HTML parsing + price parsing |
| `tests/test_diff.py` | Unit tests for diff logic |
| `credentials/.gitkeep` | Placeholder so directory is tracked |

---

## Task 1: Branch + Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `config.py`
- Create: `credentials/.gitkeep`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create the steamfoam branch**

```bash
git checkout -b steamfoam
```

Expected: `Switched to a new branch 'steamfoam'`

- [ ] **Step 2: Write `requirements.txt`**

```
playwright==1.44.0
beautifulsoup4==4.12.3
google-auth==2.29.0
google-auth-oauthlib==1.2.0
gspread==6.1.2
python-dotenv==1.0.1
pytest==8.2.0
```

- [ ] **Step 3: Write `.env.example`**

```
GOOGLE_SERVICE_ACCOUNT_JSON=credentials/service-account.json
SPREADSHEET_ID=your_google_sheet_id_here
```

- [ ] **Step 4: Write `.gitignore`**

```
.env
credentials/*.json
__pycache__/
*.pyc
.playwright/
```

- [ ] **Step 5: Write `config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.loaded.com/pc/steam"
PRICE_FILTER = "price=0-4.001"
MAX_PAGES = 200

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials/service-account.json")

SHEET_GAMES = "Games"
SHEET_HISTORY = "History"
```

- [ ] **Step 6: Create placeholder files**

```bash
mkdir -p credentials tests
touch credentials/.gitkeep tests/__init__.py
```

- [ ] **Step 7: Install dependencies**

```bash
pip install -r requirements.txt
playwright install chromium
```

Expected: pip installs all packages, then Playwright downloads Chromium (~150 MB).

- [ ] **Step 8: Commit scaffold**

```bash
git add requirements.txt .env.example .gitignore config.py credentials/.gitkeep tests/__init__.py
git commit -m "chore: project scaffold, deps, config"
```

---

## Task 2: DOM Inspection — Confirm Live Selectors

**Goal:** Fetch the live loaded.com page and identify the exact CSS selectors for game cards, titles, and prices. This task produces the selector values used in Task 3.

**Files:** No permanent files created — this is investigative.

- [ ] **Step 1: Run the Playwright DOM inspector**

Run this script (inline, no file needed):

```bash
python -c "
import asyncio
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
        await page.goto('https://www.loaded.com/pc/steam?price=0-4.001', wait_until='networkidle', timeout=30000)
        html = await page.content()
        await browser.close()
        print(html)
asyncio.run(inspect())
" > /tmp/loaded_page.html
```

- [ ] **Step 2: Find price elements**

```bash
python -c "
from bs4 import BeautifulSoup
with open('/tmp/loaded_page.html') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

# Find all text containing £
import re
for el in soup.find_all(string=re.compile(r'£\d')):
    parent = el.parent
    print('TEXT:', el.strip())
    print('TAG:', parent.name, 'CLASS:', parent.get('class'))
    print('---')
" | head -80
```

**Record the class/tag of the price element for use in Step 4.**

- [ ] **Step 3: Find the parent game card from a price element**

```bash
python -c "
from bs4 import BeautifulSoup
import re
with open('/tmp/loaded_page.html') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

# Walk up from first price to find the card ancestor
price_el = soup.find(string=re.compile(r'£\d')).parent
print('Price element:', price_el.name, price_el.get('class'))
for i, ancestor in enumerate(price_el.parents):
    print(f'  Parent {i}: <{ancestor.name}> class={ancestor.get(\"class\")} href={ancestor.get(\"href\", \"\")[:60]}')
    if i > 5:
        break
"
```

**Record the card selector (the ancestor that wraps both title and price) for use in Step 4.**

- [ ] **Step 4: Find title element within a card**

Using what you found in Step 3, inspect the title text. Run:

```bash
python -c "
from bs4 import BeautifulSoup
import re
with open('/tmp/loaded_page.html') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

# Use the card selector found in Step 3 — update CARD_SEL below
CARD_SEL = 'a[href*=\"/pc/steam/\"]'  # update this if wrong
cards = soup.select(CARD_SEL)[:3]
for card in cards:
    print('CARD href:', card.get('href', '')[:80])
    print('CARD text snippet:', card.get_text()[:200])
    print('---')
"
```

**Record:** card selector, title selector (tag/class inside card), price selector (tag/class inside card). You now have everything needed for Task 3.

---

## Task 3: Extractor (TDD)

**Files:**
- Create: `extractor.py`
- Create: `tests/test_extractor.py`

Use the selectors confirmed in Task 2. Replace `CONFIRMED_CARD_SEL`, `CONFIRMED_TITLE_SEL`, and `CONFIRMED_PRICE_SEL` below with the actual values.

- [ ] **Step 1: Write failing tests using an HTML fixture**

The fixture is a minimal slice of real loaded.com HTML containing two game cards. Build it from what you saw in Task 2's output.

`tests/test_extractor.py`:

```python
import pytest
from extractor import extract_games_from_page, _parse_price

# Minimal HTML fixture — two product cards matching loaded.com real structure.
# Replace tag names and class names with what Task 2 confirmed.
FIXTURE_HTML = """
<html><body>
  <!-- Card 1 -->
  <a href="/pc/steam/half-life-2-123">
    <span class="CONFIRMED_TITLE_CLASS">Half-Life 2</span>
    <span class="CONFIRMED_PRICE_CLASS">£1.99</span>
  </a>
  <!-- Card 2 -->
  <a href="/pc/steam/portal-456">
    <span class="CONFIRMED_TITLE_CLASS">Portal</span>
    <span class="CONFIRMED_PRICE_CLASS">£3.49</span>
  </a>
  <!-- Nav link that should be filtered out -->
  <a href="/pc/steam">All Steam Games</a>
</body></html>
"""

def test_extract_returns_two_games():
    games = extract_games_from_page(FIXTURE_HTML)
    assert len(games) == 2

def test_extract_title():
    games = extract_games_from_page(FIXTURE_HTML)
    assert games[0]["title"] == "Half-Life 2"

def test_extract_price():
    games = extract_games_from_page(FIXTURE_HTML)
    assert games[0]["price_gbp"] == 1.99

def test_extract_url_is_absolute():
    games = extract_games_from_page(FIXTURE_HTML)
    assert games[0]["url"].startswith("https://www.loaded.com")

def test_nav_link_excluded():
    games = extract_games_from_page(FIXTURE_HTML)
    titles = [g["title"] for g in games]
    assert "All Steam Games" not in titles

def test_parse_price_pound_sign():
    assert _parse_price("£1.99") == 1.99

def test_parse_price_plain():
    assert _parse_price("1.99") == 1.99

def test_parse_price_missing():
    assert _parse_price("Free") is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_extractor.py -v
```

Expected: `ModuleNotFoundError: No module named 'extractor'` or similar — all fail.

- [ ] **Step 3: Write `extractor.py` with confirmed selectors**

Replace `CONFIRMED_CARD_SEL`, `CONFIRMED_TITLE_SEL`, `CONFIRMED_PRICE_SEL` with actual values from Task 2.

```python
import re
from bs4 import BeautifulSoup

CARD_SEL = "CONFIRMED_CARD_SEL"      # e.g. "a[href*='/pc/steam/']"
TITLE_SEL = "CONFIRMED_TITLE_SEL"    # e.g. ".product-name" or "h3"
PRICE_SEL = "CONFIRMED_PRICE_SEL"    # e.g. ".price" or "span.sale-price"

def extract_games_from_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    games = []
    seen_hrefs = set()

    for card in soup.select(CARD_SEL):
        href = card.get("href", "")
        # Skip category/nav links — only individual product pages
        if not href or href in seen_hrefs or href.rstrip("/").endswith("/steam"):
            continue
        seen_hrefs.add(href)

        title = _extract_title(card)
        price = _extract_price(card)
        if not title or price is None:
            continue

        url = href if href.startswith("http") else "https://www.loaded.com" + href
        games.append({"title": title.strip(), "price_gbp": price, "url": url})

    return games


def _extract_title(card) -> str | None:
    if TITLE_SEL:
        el = card.select_one(TITLE_SEL)
        if el and el.text.strip():
            return el.text.strip()
    # Fallbacks
    for sel in ["h3", "h2", ".product-name", ".title", "[data-testid='title']"]:
        el = card.select_one(sel)
        if el and el.text.strip():
            return el.text.strip()
    label = card.get("aria-label", "")
    if label:
        return label.strip()
    img = card.select_one("img")
    if img and img.get("alt"):
        return img["alt"].strip()
    return None


def _extract_price(card) -> float | None:
    if PRICE_SEL:
        el = card.select_one(PRICE_SEL)
        if el and el.text.strip():
            return _parse_price(el.text)
    for sel in [".price", ".product-price", "[data-testid='price']", ".sale-price", "span[class*='price']"]:
        el = card.select_one(sel)
        if el and el.text.strip():
            result = _parse_price(el.text)
            if result is not None:
                return result
    # Last resort: scan all text in card
    match = re.search(r'£(\d+\.\d{2})', card.get_text())
    if match:
        return float(match.group(1))
    return None


def _parse_price(text: str) -> float | None:
    match = re.search(r'(\d+\.\d{2})', text)
    return float(match.group(1)) if match else None
```

- [ ] **Step 4: Update the fixture HTML in the test to match real structure**

Open `tests/test_extractor.py` and update `FIXTURE_HTML` so the tag/class names in the fixture match the selectors you just baked into `extractor.py`. The test must be internally consistent.

- [ ] **Step 5: Run tests — all must pass**

```bash
pytest tests/test_extractor.py -v
```

Expected: 8 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add extractor.py tests/test_extractor.py
git commit -m "feat: extractor with confirmed DOM selectors"
```

---

## Task 4: Diff Engine (TDD)

**Files:**
- Create: `diff.py`
- Create: `tests/test_diff.py`

- [ ] **Step 1: Write failing tests**

`tests/test_diff.py`:

```python
from diff import compute_diff

EXISTING = {
    "Half-Life 2": {"price_gbp": 1.99, "url": "https://www.loaded.com/pc/steam/hl2", "first_seen": "2026-01-01"},
    "Portal": {"price_gbp": 3.99, "url": "https://www.loaded.com/pc/steam/portal", "first_seen": "2026-01-01"},
}

CURRENT = [
    {"title": "Half-Life 2", "price_gbp": 1.99, "url": "https://www.loaded.com/pc/steam/hl2"},   # unchanged
    {"title": "Portal", "price_gbp": 2.49, "url": "https://www.loaded.com/pc/steam/portal"},     # price drop
    {"title": "Team Fortress 2", "price_gbp": 0.99, "url": "https://www.loaded.com/pc/steam/tf2"}, # new
]


def test_new_game_gets_NEW_status():
    games, _ = compute_diff(CURRENT, EXISTING)
    tf2 = next(g for g in games if g["title"] == "Team Fortress 2")
    assert tf2["status"] == "NEW"


def test_new_game_in_history():
    _, history = compute_diff(CURRENT, EXISTING)
    events = [e for e in history if e["title"] == "Team Fortress 2"]
    assert len(events) == 1
    assert events[0]["event"] == "new"
    assert events[0]["new_price"] == 0.99


def test_price_drop_status():
    games, _ = compute_diff(CURRENT, EXISTING)
    portal = next(g for g in games if g["title"] == "Portal")
    assert portal["status"] == "PRICE_DOWN"


def test_price_drop_in_history():
    _, history = compute_diff(CURRENT, EXISTING)
    events = [e for e in history if e["title"] == "Portal"]
    assert len(events) == 1
    assert events[0]["event"] == "price_down"
    assert events[0]["old_price"] == 3.99
    assert events[0]["new_price"] == 2.49


def test_unchanged_no_history():
    _, history = compute_diff(CURRENT, EXISTING)
    events = [e for e in history if e["title"] == "Half-Life 2"]
    assert len(events) == 0


def test_unchanged_empty_status():
    games, _ = compute_diff(CURRENT, EXISTING)
    hl2 = next(g for g in games if g["title"] == "Half-Life 2")
    assert hl2["status"] == ""


def test_first_seen_preserved():
    games, _ = compute_diff(CURRENT, EXISTING)
    hl2 = next(g for g in games if g["title"] == "Half-Life 2")
    assert hl2["first_seen"] == "2026-01-01"


def test_sort_order():
    games, _ = compute_diff(CURRENT, EXISTING)
    statuses = [g["status"] for g in games]
    # NEW comes before PRICE_DOWN comes before ""
    assert statuses.index("NEW") < statuses.index("PRICE_DOWN")
    assert statuses.index("PRICE_DOWN") < statuses.index("")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_diff.py -v
```

Expected: `ModuleNotFoundError: No module named 'diff'`

- [ ] **Step 3: Write `diff.py`**

```python
from datetime import datetime


def compute_diff(
    current_games: list[dict],
    existing_games: dict[str, dict],
) -> tuple[list[dict], list[dict]]:
    today = datetime.today().strftime("%Y-%m-%d")
    games_to_write = []
    history_events = []

    for game in current_games:
        title = game["title"]
        new_price = game["price_gbp"]
        url = game["url"]

        if title not in existing_games:
            games_to_write.append({
                "title": title,
                "price_gbp": new_price,
                "url": url,
                "status": "NEW",
                "price_change": "",
                "first_seen": today,
                "last_seen": today,
            })
            history_events.append({
                "timestamp": today,
                "title": title,
                "event": "new",
                "old_price": "",
                "new_price": new_price,
                "url": url,
            })
        else:
            existing = existing_games[title]
            old_price = float(existing.get("price_gbp", 0) or 0)
            delta = round(new_price - old_price, 2)

            if delta != 0:
                status = "PRICE_DOWN" if delta < 0 else "PRICE_UP"
                price_change = f"{'+' if delta > 0 else ''}{delta:.2f}"
                history_events.append({
                    "timestamp": today,
                    "title": title,
                    "event": status.lower(),
                    "old_price": old_price,
                    "new_price": new_price,
                    "url": url,
                })
            else:
                status = ""
                price_change = ""

            games_to_write.append({
                "title": title,
                "price_gbp": new_price,
                "url": url,
                "status": status,
                "price_change": price_change,
                "first_seen": existing.get("first_seen", today),
                "last_seen": today,
            })

    status_order = {"NEW": 0, "PRICE_DOWN": 1, "PRICE_UP": 2, "": 3}
    games_to_write.sort(key=lambda g: (status_order.get(g["status"], 3), g["title"].lower()))

    return games_to_write, history_events
```

- [ ] **Step 4: Run tests — all must pass**

```bash
pytest tests/test_diff.py -v
```

Expected: 8 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add diff.py tests/test_diff.py
git commit -m "feat: diff engine with full test coverage"
```

---

## Task 5: Crawler

**Files:**
- Create: `crawler.py`

No unit tests for the crawler — it requires live network and a real browser. It is validated end-to-end in Task 8.

- [ ] **Step 1: Write `crawler.py`**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add crawler.py
git commit -m "feat: paginated crawler with loop-back detection"
```

---

## Task 6: Google Sheets Module

**Files:**
- Create: `sheets.py`

No unit tests — requires live Google Sheets credentials. Validated in Task 8.

- [ ] **Step 1: Write `sheets.py`**

```python
import gspread
from google.oauth2.service_account import Credentials
from config import SERVICE_ACCOUNT_JSON, SPREADSHEET_ID, SHEET_GAMES, SHEET_HISTORY

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

GAMES_HEADERS = ["title", "price_gbp", "url", "status", "price_change", "first_seen", "last_seen"]
HISTORY_HEADERS = ["timestamp", "title", "event", "old_price", "new_price", "url"]


def get_client():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    return gspread.authorize(creds)


def ensure_headers(worksheet, headers: list[str]):
    existing = worksheet.row_values(1)
    if existing != headers:
        worksheet.insert_row(headers, index=1)


def read_existing_games(client) -> dict[str, dict]:
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_GAMES)
    records = ws.get_all_records()
    return {r["title"]: r for r in records}


def write_games(client, games_data: list[dict]):
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_GAMES)
    ws.clear()
    ensure_headers(ws, GAMES_HEADERS)
    rows = [[g.get(h, "") for h in GAMES_HEADERS] for g in games_data]
    if rows:
        ws.append_rows(rows, value_input_option="USER_ENTERED")
    print(f"  Wrote {len(rows)} games to '{SHEET_GAMES}' tab.")


def append_history(client, events: list[dict]):
    if not events:
        return
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_HISTORY)
    ensure_headers(ws, HISTORY_HEADERS)
    rows = [[e.get(h, "") for h in HISTORY_HEADERS] for e in events]
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    print(f"  Appended {len(rows)} history events to '{SHEET_HISTORY}' tab.")
```

- [ ] **Step 2: Commit**

```bash
git add sheets.py
git commit -m "feat: Google Sheets read/write module"
```

---

## Task 7: Entry Point

**Files:**
- Create: `run.py`

- [ ] **Step 1: Write `run.py`**

```python
import asyncio
from crawler import fetch_all_games
from sheets import get_client, read_existing_games, write_games, append_history
from diff import compute_diff


async def main():
    print("=== SteamFoam — starting crawl ===\n")

    print("Step 1: Crawling loaded.com...")
    current_games = await fetch_all_games()
    if not current_games:
        print("ERROR: No games returned. Check selectors in extractor.py.")
        return

    print("\nStep 2: Reading existing Games sheet...")
    client = get_client()
    existing_games = read_existing_games(client)
    print(f"  Found {len(existing_games)} existing games in sheet.")

    print("\nStep 3: Computing diff...")
    games_to_write, history_events = compute_diff(current_games, existing_games)
    new_count = sum(1 for g in games_to_write if g["status"] == "NEW")
    changed_count = sum(1 for g in games_to_write if g["status"] in ("PRICE_DOWN", "PRICE_UP"))
    print(f"  {new_count} new, {changed_count} price changes, {len(games_to_write)} total.")

    print("\nStep 4: Writing to Google Sheets...")
    write_games(client, games_to_write)
    append_history(client, history_events)

    print("\n=== SteamFoam done ===")
    print(f"  {new_count} new | {changed_count} price changes | {len(games_to_write)} total tracked")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
git add run.py
git commit -m "feat: run.py entry point"
```

---

## Task 8: End-to-End Smoke Test

**Goal:** Verify the full pipeline works before pushing. Requires `.env` set up with real credentials.

- [ ] **Step 1: Run the unit test suite first**

```bash
pytest tests/ -v
```

Expected: All tests PASSED (extractor + diff suites). Fix any failures before continuing.

- [ ] **Step 2: Set up `.env`**

```bash
cp .env.example .env
# Edit .env — fill in SPREADSHEET_ID and GOOGLE_SERVICE_ACCOUNT_JSON path
```

Ensure `credentials/service-account.json` exists (downloaded from Google Cloud Console).
Ensure the Google Sheet has two tabs named exactly `Games` and `History`.
Ensure the service account email has **Editor** access to the sheet.

- [ ] **Step 3: Run a single-page crawl to test selectors**

```bash
python -c "
import asyncio
from crawler import fetch_all_games
from config import MAX_PAGES
import config
config.MAX_PAGES = 1  # Override to one page only
games = asyncio.run(fetch_all_games())
print(f'Got {len(games)} games')
if games:
    print('First game:', games[0])
"
```

Expected: prints at least one game with a title, price_gbp (float), and absolute URL.
If you get 0 games, the selectors in `extractor.py` need updating — re-run Task 2.

- [ ] **Step 4: Run the full pipeline**

```bash
python run.py
```

Expected output (approximate):

```
=== SteamFoam — starting crawl ===

Step 1: Crawling loaded.com...
  Fetching page 1: https://www.loaded.com/pc/steam?price=0-4.001
  Page 1 anchor: '<some game title>'
  ...
  Crawl complete. NNN games found.

Step 2: Reading existing Games sheet...
  Found 0 existing games in sheet.

Step 3: Computing diff...
  NNN new, 0 price changes, NNN total.

Step 4: Writing to Google Sheets...
  Wrote NNN games to 'Games' tab.

=== SteamFoam done ===
  NNN new | 0 price changes | NNN total tracked
```

Open the Google Sheet and verify rows are present in Games and one row per game in History (event = "new").

- [ ] **Step 5: Run a second time (idempotency check)**

```bash
python run.py
```

Expected: `0 new | 0 price changes | NNN total tracked` — no duplicate history rows, same game count.

---

## Task 9: README + Push

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# SteamFoam

Weekly tracker for Steam games under £4 on loaded.com.
Detects new games and price changes. Writes to Google Sheets.

## Setup

1. Install dependencies:
   pip install -r requirements.txt
   playwright install chromium

2. Set up Google Sheets API:
   - Go to console.cloud.google.com
   - Create a project → enable Google Sheets API + Google Drive API
   - Create a service account → download JSON key → save to credentials/service-account.json
   - Share your Google Sheet with the service account email (Editor access)

3. Create your Google Sheet with two tabs named exactly:
   - Games
   - History

4. Copy .env.example to .env and fill in SPREADSHEET_ID (from the sheet URL).

5. Run:
   python run.py

## Scheduling (weekly, Sunday midnight)

   0 0 * * 0 cd /path/to/steamfoam && python run.py >> logs/steamfoam.log 2>&1

## Troubleshooting

If you get 0 games on first run, the DOM selectors need updating.
Run the inspector snippet (see docs/superpowers/plans/2026-06-21-steamfoam.md Task 2)
then update CARD_SEL, TITLE_SEL, PRICE_SEL in extractor.py.
```

- [ ] **Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: README with setup and scheduling instructions"
```

- [ ] **Step 3: Push to steamfoam branch**

```bash
git push -u origin steamfoam
```

**Do NOT push to main.**

---

## Full Test Run Before Handoff

```bash
pytest tests/ -v
```

All tests must be green. The end-to-end smoke test (Task 8) provides integration confidence.
