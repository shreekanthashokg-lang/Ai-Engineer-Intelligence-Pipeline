"""Upload the 6 exported CSV tabs to a Google Sheet using the Sheets API.

Setup (documented, credentials never committed to the repo):
  1. Create a Google Cloud project -> enable "Google Sheets API" and "Google Drive API".
  2. Create a Service Account -> download its JSON key -> save as
     credentials/service_account.json (gitignored).
  3. Create a blank Google Sheet, share it with the service account's email
     (found inside the JSON key as `client_email`) with Editor access.
  4. Put the sheet's ID (from its URL) into SPREADSHEET_ID below or pass --sheet-id.
  5. Run:  python scripts/export_google_sheets.py --sheet-id <id>
     Add --dry-run to validate files and print the plan without calling the API.

This script: validates the CSVs exist and match expected headers, clears each
target tab, batch-uploads rows, freezes the header row, bolds headers, and
prints the final shareable Sheet URL.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, ".")
from src.storage.exporters import TAB_HEADERS

TAB_FILES = {
    "Startups": "data/exports/startups.csv",
    "Products": "data/exports/products.csv",
    "Research Papers": "data/exports/research_papers.csv",
    "Jobs": "data/exports/jobs.csv",
    "News": "data/exports/news.csv",
    "Entity Mapping Log": "data/exports/entity_mapping_log.csv",
}


def validate_files() -> dict[str, list[list[str]]]:
    data = {}
    for tab, path in TAB_FILES.items():
        p = Path(path)
        if not p.exists():
            print(f"[WARN] {path} not found — run the pipeline/exporter first. Skipping tab '{tab}'.")
            continue
        with open(p, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        expected = TAB_HEADERS.get(tab, [])
        if rows and expected and rows[0] != expected:
            print(f"[WARN] {tab}: header mismatch. Expected {expected}, got {rows[0]}")
        data[tab] = rows
        print(f"[OK] {tab}: {max(len(rows) - 1, 0)} data rows from {path}")
    return data


def upload(sheet_id: str, data: dict[str, list[list[str]]]) -> str:
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials/service_account.json", scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)

    for tab, rows in data.items():
        try:
            ws = sh.worksheet(tab)
            ws.clear()
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=tab, rows=max(len(rows) + 10, 100), cols=max(len(rows[0]) if rows else 10, 10))
        if rows:
            ws.update("A1", rows)
            ws.freeze(rows=1)
            ws.format("A1:Z1", {"textFormat": {"bold": True}})
        print(f"[UPLOADED] {tab}: {max(len(rows) - 1, 0)} rows")

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = validate_files()

    if args.dry_run or not args.sheet_id:
        print("\nDry run (or no --sheet-id supplied) — no API calls made.")
        print("To actually upload: python scripts/export_google_sheets.py --sheet-id <your_sheet_id>")
        return

    url = upload(args.sheet_id, data)
    print(f"\nDone. Spreadsheet URL: {url}")


if __name__ == "__main__":
    main()
