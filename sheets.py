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
