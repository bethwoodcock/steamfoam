import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from config import SERVICE_ACCOUNT_JSON, SPREADSHEET_ID, SHEET_GAMES, SHEET_HISTORY

HISTORY_RETENTION_DAYS = 60

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

GAMES_HEADERS = ["title", "price_gbp", "url", "status", "price_change", "first_seen", "last_seen", "in_stock"]
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


def prune_history(client):
    """Delete history rows older than HISTORY_RETENTION_DAYS."""
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_HISTORY)
    rows = ws.get_all_values()
    if len(rows) <= 1:
        return
    cutoff = datetime.today() - timedelta(days=HISTORY_RETENTION_DAYS)
    keep = [rows[0]]  # always keep header
    removed = 0
    for row in rows[1:]:
        try:
            row_date = datetime.strptime(row[0], "%Y-%m-%d")
            if row_date >= cutoff:
                keep.append(row)
            else:
                removed += 1
        except (ValueError, IndexError):
            keep.append(row)  # keep rows with unparseable dates
    if removed:
        ws.clear()
        ws.update(keep)
        print(f"  Pruned {removed} history rows older than {HISTORY_RETENTION_DAYS} days.")
    else:
        print(f"  No history rows to prune.")


def append_history(client, events: list[dict]):
    if not events:
        return
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_HISTORY)
    ensure_headers(ws, HISTORY_HEADERS)
    rows = [[e.get(h, "") for h in HISTORY_HEADERS] for e in events]
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    print(f"  Appended {len(rows)} history events to '{SHEET_HISTORY}' tab.")
