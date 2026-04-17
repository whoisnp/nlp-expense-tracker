"""Google Sheets storage service — with local JSON fallback."""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

FALLBACK_FILE = Path("expenses_fallback.json")


# ── Google Sheets helpers ──────────────────────────────────────────────────────

def _get_sheet():
    """Return a gspread worksheet, or None if credentials are missing."""
    creds_path = os.getenv("GOOGLE_CREDENTIALS_FILE")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")

    if not creds_path or not sheet_id:
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open_by_key(sheet_id).sheet1
    except Exception as e:
        logger.warning(f"Could not connect to Google Sheets: {e}")
        return None


def _ensure_header(sheet) -> None:
    """Add header row if the sheet is empty."""
    existing = sheet.get_all_values()
    if not existing:
        headers = [
            "timestamp", "raw_input", "amount", "currency",
            "amount_base", "category", "description", "payment_method", "date",
        ]
        sheet.append_row(headers)


# ── Fallback: local JSON ───────────────────────────────────────────────────────

def _save_to_json(row: dict) -> None:
    """Append expense to a local JSON file as fallback."""
    data = []
    if FALLBACK_FILE.exists():
        try:
            data = json.loads(FALLBACK_FILE.read_text())
        except json.JSONDecodeError:
            data = []

    data.append(row)
    FALLBACK_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    logger.info(f"Saved to fallback file: {FALLBACK_FILE}")


# ── Public API ─────────────────────────────────────────────────────────────────

def append_expense(expense: dict) -> None:
    """
    Write one expense row.
    Tries Google Sheets first; falls back to local JSON if unavailable.
    """
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "raw_input": expense.get("raw_input", ""),
        "amount": expense.get("amount"),
        "currency": expense.get("currency"),
        "amount_base": expense.get("amount_base"),
        "category": expense.get("category"),
        "description": expense.get("description"),
        "payment_method": expense.get("payment_method"),
        "date": expense.get("date"),
    }

    sheet = _get_sheet()

    if sheet:
        try:
            _ensure_header(sheet)
            sheet.append_row(list(row.values()))
            logger.info("Expense written to Google Sheets ✓")
            return
        except Exception as e:
            logger.error(f"Sheets write failed: {e}. Falling back to local JSON.")

    _save_to_json(row)
