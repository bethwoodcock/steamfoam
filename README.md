# SteamFoam ☕

> **Personal project — not intended for public use.** This tool is built around my own Google Sheets account and service account credentials, so it won't run for anyone else without their own setup. Shared here as a portfolio piece.

A personal weekend project built to scratch an itch: I wanted a weekly digest of cheap Steam games without manually checking a store page. SteamFoam crawls [loaded.com](https://www.loaded.com/pc/steam) every Sunday, finds every Steam game under £3, detects new listings and price changes, and writes everything to a private Google Sheet. A local Flask dashboard lets me filter and search the results.

**What it does:**
- Crawls ~200 pages of loaded.com using Playwright (headless Chromium)
- Extracts game titles, prices, and URLs via BeautifulSoup
- Diffs the current crawl against the previous week's data to detect new games and price changes
- Writes results to Google Sheets via the Sheets API
- Serves a local filterable dashboard (New / Price Drop / Price Up / search / sortable columns)
- Runs automatically every Sunday via GitHub Actions

**Tech:** Python, Playwright, BeautifulSoup, gspread, Flask, Google Sheets API, GitHub Actions

---

> ⚠️ **This won't work if you clone it.** It requires a private Google service account JSON and a private spreadsheet that are not in this repo. If you want to build something similar, see the setup notes below.

---

## How I use it

**Check the dashboard:**
```
venv\Scripts\activate
python app.py
```
Then open http://localhost:5000 — filterable table of all tracked games, click any row to open the loaded.com page.

**Trigger a manual crawl:**
```
venv\Scripts\activate
python run.py
```
Takes a few minutes. Updates the Google Sheet, then refresh the dashboard to see the latest.

**Automatic crawl:** GitHub Actions runs `run.py` every Sunday at midnight UTC. The sheet stays up to date without me doing anything.

---

## How it's built

```
crawler.py     — Playwright pagination, loop-back detection for last page
extractor.py   — BeautifulSoup DOM parsing → {title, price_gbp, url}
diff.py        — Compare crawl vs last Sheets snapshot, produce change events
sheets.py      — gspread read/write for Games and History tabs
run.py         — Orchestrates everything end to end
app.py         — Flask dashboard with filtering, search, sorting
```

**Sheet structure — Games tab** (rewritten each run):

| Column | Description |
|---|---|
| title | Game name |
| price_gbp | Current price |
| status | NEW, PRICE_DOWN, PRICE_UP, or blank |
| price_change | e.g. -1.00 or +0.50 |
| first_seen | Date first spotted |
| last_seen | Date of last crawl |

**History tab** — append-only log of every new game and price change, so I can see what moved week to week.

---

## If you want to build your own version

You'd need:
1. A Google Cloud project with Sheets API + Drive API enabled
2. A service account JSON key saved to `credentials/service-account.json`
3. A Google Sheet with `Games` and `History` tabs, shared with the service account
4. A `.env` file with your `SPREADSHEET_ID`
5. `pip install -r requirements.txt` and `playwright install chromium`

For GitHub Actions automation, add `SPREADSHEET_ID` and `GOOGLE_SERVICE_ACCOUNT_JSON` as repository secrets.
