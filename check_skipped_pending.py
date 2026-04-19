"""How many of the skipped rows are still pending Ahmed's outreach?"""
import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

SKIPPED_ROWS = {92, 93, 98, 99, 102, 103, 104, 105, 106, 107, 109, 111, 112, 113, 115}

creds = ServiceAccountCredentials.from_json_keyfile_name(
    os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json"), SCOPE
)
sheet = gspread.authorize(creds).open_by_key(os.environ["GOOGLE_SHEETS_ID"]).sheet1
records = sheet.get_all_records()

for idx, row in enumerate(records, start=2):
    if idx not in SKIPPED_ROWS:
        continue
    name = row.get("Business Name", "")
    ready = str(row.get("Ready to Contact", "")).strip()
    contacted = str(row.get("Contacted?", "")).strip()
    pending = ready == "Yes" and contacted in ("No", "no", "")
    flag = "PENDING" if pending else "done/skipped"
    print(f"  row {idx:3d}  {flag:14s}  ready={ready!r:6s}  contacted={contacted!r:15s}  {name}")
