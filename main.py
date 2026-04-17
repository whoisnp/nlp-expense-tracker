"""FastAPI entry point — Telegram expense tracker webhook."""

import logging
from datetime import date

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from models import Expense
from services.ai import parse_expense
from services.currency import convert_to_base
from services.sheets import append_expense

# Load .env file if present
load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NLP Expense Tracker",
    description="Parse natural-language expense messages from Telegram and store them in Google Sheets.",
    version="0.1.0",
)


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


# ── Main webhook ───────────────────────────────────────────────────────────────
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Accept a raw Telegram Update JSON.
    Extracts the message text, parses it as an expense, converts currency,
    stores in Google Sheets, and returns the structured result.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # ── 1. Extract message text ────────────────────────────────────────────────
    message_obj = body.get("message") or body.get("edited_message")
    if not message_obj:
        logger.warning("No message found in update, ignoring.")
        return JSONResponse({"status": "ignored", "reason": "no message in update"})

    text = message_obj.get("text", "").strip()
    if not text:
        return JSONResponse({"status": "ignored", "reason": "empty message text"})

    logger.info(f"Received message: {text!r}")

    # ── 2. AI Parse ────────────────────────────────────────────────────────────
    try:
        parsed = parse_expense(text)
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        raise HTTPException(status_code=422, detail=f"Could not parse expense: {e}")

    parsed["raw_input"] = text

    # ── 3. Pydantic Validation ─────────────────────────────────────────────────
    try:
        expense = Expense(**parsed)
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid expense data: {e}")

    # ── 4. Currency Conversion ─────────────────────────────────────────────────
    expense.amount_base = convert_to_base(expense.amount, expense.currency)

    # ── 5. Storage ─────────────────────────────────────────────────────────────
    try:
        append_expense(expense.model_dump())
    except Exception as e:
        logger.error(f"Storage failed: {e}")
        # Non-fatal: still return the parsed result
        return JSONResponse(
            status_code=207,
            content={
                "status": "partial",
                "warning": "Expense parsed but could not be saved.",
                "data": expense.model_dump(),
            },
        )

    return JSONResponse({
        "status": "success",
        "data": expense.model_dump(),
    })


# ── Direct message endpoint (for testing without Telegram) ────────────────────
@app.post("/parse")
async def parse_direct(request: Request):
    """
    Convenience endpoint: accepts {"message": "..."} directly.
    Useful for local testing without setting up a Telegram bot.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    text = body.get("message", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="'message' field is required")

    # Reuse the same pipeline
    fake_update = {"message": {"text": text}}
    fake_request = Request(
        scope={
            "type": "http",
            "method": "POST",
            "path": "/parse",
            "headers": [],
            "query_string": b"",
        }
    )

    # Call the webhook pipeline directly (inline to keep it simple)
    try:
        parsed = parse_expense(text)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse expense: {e}")

    parsed["raw_input"] = text

    try:
        expense = Expense(**parsed)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid expense data: {e}")

    expense.amount_base = convert_to_base(expense.amount, expense.currency)

    try:
        append_expense(expense.model_dump())
    except Exception as e:
        logger.error(f"Storage failed: {e}")

    return JSONResponse({
        "status": "success",
        "data": expense.model_dump(),
    })
