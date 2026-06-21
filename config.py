import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.loaded.com/pc/steam"
PRICE_FILTER = "price=0-3.001"
MAX_PAGES = 200

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials/service-account.json")

SHEET_GAMES = "Games"
SHEET_HISTORY = "History"
