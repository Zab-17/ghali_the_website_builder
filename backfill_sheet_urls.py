"""One-shot: replace protected hash URLs in the 'New Website' column with
the public production alias.

Hash URL form (auth-gated):
    https://{slug}-{hash}-zab-17s-projects.vercel.app
Public alias (what we want):
    https://{slug}.vercel.app

For each row whose URL matches the hash form:
  1. Extract slug.
  2. HEAD the candidate alias — only rewrite on HTTP 200.
  3. Leave anything ambiguous alone and report it at the end.

Run: python3 backfill_sheet_urls.py            # dry run
     python3 backfill_sheet_urls.py --apply    # write changes
"""
import os
import re
import subprocess
import sys
import urllib.request

from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

SHEET_ID = os.environ["GOOGLE_SHEETS_ID"]
CREDS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Matches Zeyad's Vercel team-scoped hash URLs.
HASH_URL_RE = re.compile(
    r"^https://([a-z0-9-]+?)-[a-z0-9]{7,12}-zab-17s-projects\.vercel\.app/?$"
)


def is_live(url: str) -> bool:
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False


def resolve_alias_via_inspect(hash_url: str) -> str | None:
    """Ask Vercel for the deployment's aliases, return the shortest public one."""
    try:
        result = subprocess.run(
            ["vercel", "inspect", hash_url],
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    output = result.stdout + result.stderr
    aliases = re.findall(r"https://[a-z0-9-]+\.vercel\.app", output)
    public = [a for a in aliases if not a.endswith("-projects.vercel.app")]
    if not public:
        return None
    candidate = min(public, key=len)
    return candidate if is_live(candidate) else None


def main() -> None:
    apply = "--apply" in sys.argv

    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, SCOPE)
    sheet = gspread.authorize(creds).open_by_key(SHEET_ID).sheet1

    header = sheet.row_values(1)
    try:
        col = header.index("New Website") + 1
    except ValueError:
        print("ERROR: no 'New Website' column in sheet.")
        sys.exit(1)
    try:
        ready_col = header.index("Ready to Contact") + 1
    except ValueError:
        ready_col = None

    records = sheet.get_all_records()
    rewrites: list[tuple[int, str, str, str]] = []  # (row, name, old, new)
    skipped: list[tuple[int, str, str, str]] = []   # (row, name, url, reason)

    for idx, row in enumerate(records, start=2):
        url = str(row.get("New Website", "")).strip()
        name = str(row.get("Business Name", "")).strip()
        if not url:
            continue

        m = HASH_URL_RE.match(url)
        if not m:
            # Already a clean URL or a non-Vercel URL — leave alone.
            continue

        slug = m.group(1)
        candidate = f"https://{slug}.vercel.app"
        if is_live(candidate):
            rewrites.append((idx, name, url, candidate))
            continue

        # Slug collision: default alias doesn't exist. Ask Vercel.
        resolved = resolve_alias_via_inspect(url)
        if resolved:
            rewrites.append((idx, name, url, resolved))
        else:
            skipped.append((idx, name, url, "no public alias found"))

    print(f"\nFound {len(rewrites)} rewritable rows, {len(skipped)} skipped.\n")
    for row, name, old, new in rewrites:
        print(f"  row {row:3d}  {name[:30]:30s}  {old}\n            -> {new}")
    if skipped:
        print("\nSkipped:")
        for row, name, url, reason in skipped:
            print(f"  row {row:3d}  {name[:30]:30s}  {url}  ({reason})")

    if not apply:
        print("\nDry run. Re-run with --apply to write these to the sheet.")
        return

    # Batched write — Sheets limits individual writes to 60/min/user, but a
    # single batch_update counts as one request.
    def col_letter(col_num: int) -> str:
        letters = ""
        while col_num > 0:
            col_num, rem = divmod(col_num - 1, 26)
            letters = chr(65 + rem) + letters
        return letters

    updates = [
        {"range": f"{col_letter(col)}{row}", "values": [[new]]}
        for row, _, _, new in rewrites
    ]
    if ready_col and skipped:
        updates += [
            {"range": f"{col_letter(ready_col)}{row}", "values": [["Needs redeploy"]]}
            for row, _, _, _ in skipped
        ]

    sheet.batch_update(updates, value_input_option="USER_ENTERED")
    print(f"\nWrote {len(rewrites)} URL cells + flagged {len(skipped)} dead rows.")


if __name__ == "__main__":
    main()
