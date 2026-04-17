# NLP Expense Tracker

A minimal FastAPI backend that turns natural language Telegram messages into structured expense records stored in Google Sheets.

```
Telegram → POST /webhook/telegram → AI Parsing → Validation → Google Sheets
```

---

## Project Structure

```
nlp-expense-tracker/
├── main.py                 # FastAPI app + webhook handler
├── models.py               # Pydantic expense schema
├── services/
│   ├── ai.py               # OpenAI parser + regex fallback
│   ├── currency.py         # Currency conversion (mock rates)
│   └── sheets.py           # Google Sheets writer + JSON fallback
├── requirements.txt
├── .env.example
└── README.md
```

---

## Install

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and fill in your environment variables
cp .env.example .env
# Edit .env with your keys (see Configuration section below)
```

---

## Run

```bash
uvicorn main:app --reload
```

The server starts at `http://localhost:8000`.

- **API docs:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health

---

## Configuration

Copy `.env.example` to `.env` and fill in the values:

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | No | OpenAI key. If missing, a regex fallback parser is used. |
| `OPENAI_MODEL` | No | Defaults to `gpt-4o-mini` |
| `GOOGLE_CREDENTIALS_FILE` | No | Path to service account JSON. If missing, saves to `expenses_fallback.json`. |
| `GOOGLE_SHEET_ID` | No | ID from your Google Sheet URL. |
| `BASE_CURRENCY` | No | Base currency for conversion. Defaults to `EGP`. |

> The app works **without any API keys** — it uses a regex parser and saves to a local JSON file.

---

## Usage

### Option A — Direct test endpoint (no Telegram needed)

```bash
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"message": "paid 12 euros for coffee"}'
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "amount": 12.0,
    "currency": "EUR",
    "amount_base": 633.6,
    "category": "Food",
    "description": "coffee",
    "payment_method": "cash",
    "date": "2026-04-17",
    "raw_input": "paid 12 euros for coffee"
  }
}
```

---

### Option B — Telegram webhook (real bot)

```bash
curl -X POST http://localhost:8000/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 123456789,
    "message": {
      "text": "uber home 150 egp",
      "from": {"id": 42, "first_name": "Test"},
      "chat": {"id": 42}
    }
  }'
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "amount": 150.0,
    "currency": "EGP",
    "amount_base": 150.0,
    "category": "Transport",
    "description": "uber home",
    "payment_method": "online",
    "date": "2026-04-17",
    "raw_input": "uber home 150 egp"
  }
}
```

---

## More example inputs

| Input | What gets parsed |
|---|---|
| `"35 bucks for lunch with the team"` | amount: 35, currency: USD, category: Food |
| `"food 500 inr dinner"` | amount: 500, currency: INR, category: Food |
| `"netflix subscription 14.99 usd card"` | amount: 14.99, currency: USD, category: Entertainment |
| `"pharmacy 230"` | amount: 230, currency: EGP (default), category: Health |
| `"rent 8500 cash"` | amount: 8500, currency: EGP, category: Bills |

---

## Setting up Google Sheets (optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create a project
2. Enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → download the JSON key
4. Share your Google Sheet with the service account email (Editor access)
5. Set `GOOGLE_CREDENTIALS_FILE` to the JSON path and `GOOGLE_SHEET_ID` to your sheet's ID

If you skip this, all expenses are saved to `expenses_fallback.json` in the project directory.

---

## Setting up Telegram bot (optional)

1. Message `@BotFather` on Telegram → `/newbot` → get your token
2. Set the webhook with ngrok (for local dev):
   ```bash
   ngrok http 8000
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<ngrok-url>/webhook/telegram"
   ```

---

## Fallback behavior

| Missing | Fallback |
|---|---|
| `OPENAI_API_KEY` | Regex-based parser (works for common patterns) |
| Google Sheets credentials | Saves to `expenses_fallback.json` |
| Unknown currency | Stores original amount, logs a warning |
