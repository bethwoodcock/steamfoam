# SteamFoam ☕

Weekly tracker for Steam games under £3 on loaded.com.
Detects new games and price changes. Writes to Google Sheets.

---

## Viewing the data

**Google Sheet (always up to date):**
https://docs.google.com/spreadsheets/d/1dKFaeZw__UPVwXmj3srIHSXgx0wEy6MN3wRpK66YJXg

**Local dashboard (filterable UI):**
1. Open a terminal in the steamfoam folder
2. Run:
   ```
   venv\Scripts\activate
   python app.py
   ```
3. Open http://localhost:5000 in your browser
4. Press `Ctrl+C` in the terminal to stop it when done

The dashboard lets you filter by New / Price Drop / Price Up, search by game name, and sort by price or date. Clicking a game opens its loaded.com page.

---

## Refreshing the data manually

To crawl loaded.com and update the sheet right now:
```
venv\Scripts\activate
python run.py
```

This takes a few minutes (crawls ~200 pages). When done, refresh the dashboard or the Google Sheet to see the latest data.

---

## Automatic weekly crawl

GitHub Actions runs the crawl automatically every Sunday at midnight UTC.
No action needed — the sheet updates itself.

To trigger a manual run on GitHub:
1. Go to github.com/bethwoodcock/steamfoam
2. Click **Actions** → **Weekly SteamFoam Crawl**
3. Click **Run workflow**

---

## First-time setup (new machine)

1. Clone the repo and open a terminal in the folder
2. Create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Copy `.env.example` to `.env` and fill in your `SPREADSHEET_ID`
4. Put your `service-account.json` in the `credentials/` folder
5. Run `python app.py` to open the dashboard, or `python run.py` to crawl

---

## Sheet structure

**Games tab** — rewritten on each run:

| Column | Description |
|---|---|
| title | Game name |
| price_gbp | Current price |
| url | loaded.com product page |
| status | NEW, PRICE_DOWN, PRICE_UP, or blank |
| price_change | e.g. -1.00 or +0.50 |
| first_seen | Date first found |
| last_seen | Date of last crawl |

**History tab** — append-only log of every new game and price change.

---

## Troubleshooting

If you get 0 games on first run, the DOM selectors may have changed.
Check `extractor.py` and update `CARD_SEL`, `TITLE_SEL`, `PRICE_SEL` — see
`docs/superpowers/plans/2026-06-21-steamfoam.md` Task 2 for the inspection steps.
