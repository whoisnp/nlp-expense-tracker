"""AI parsing service — OpenAI-powered or mock fallback."""

import os
import re
import json
import logging
from datetime import date
from openai import OpenAI

logger = logging.getLogger(__name__)

# Categories the AI can assign
CATEGORIES = [
    "Food", "Transport", "Shopping", "Entertainment", "Health",
    "Bills", "Education", "Travel", "Groceries", "Uncategorized",
]

SYSTEM_PROMPT = f"""You are an expense parser. Extract structured data from natural language expense messages.

Return ONLY valid JSON with these fields:
- "amount": number (required, must be positive)
- "currency": string (ISO 4217 code, e.g. "USD", "EGP", "EUR", "INR". Default to "INR" if ambiguous)
- "category": string (one of: {', '.join(CATEGORIES)})
- "description": string (short summary of what the expense was for)
- "payment_method": string (one of: "cash", "card", "online", "bank_transfer". Default to "cash")
- "date": string (YYYY-MM-DD, default to today: {date.today().isoformat()})

Examples:
Input: "paid 12 euros for coffee"
Output: {{"amount": 12, "currency": "EUR", "category": "Food", "description": "coffee", "payment_method": "cash", "date": "{date.today().isoformat()}"}}

Input: "uber home 150 egp"
Output: {{"amount": 150, "currency": "EGP", "category": "Transport", "description": "uber home", "payment_method": "online", "date": "{date.today().isoformat()}"}}

Return ONLY the JSON object, no markdown, no explanation."""


def parse_with_openai(message: str) -> dict:
    """Parse expense message using OpenAI API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0.1,
        max_tokens=256,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw)


def parse_with_mock(message: str) -> dict:
    """Regex-based fallback parser for when no API key is available."""
    text = message.lower().strip()

    # Try to extract amount
    amount_match = re.search(r"(\d+(?:\.\d+)?)", text)
    amount = float(amount_match.group(1)) if amount_match else 0.0

    # Try to detect currency
    currency = "EGP"
    currency_map = {
        "usd": "USD", "dollar": "USD", "dollars": "USD", "$": "USD", "bucks": "USD",
        "eur": "EUR", "euro": "EUR", "euros": "EUR", "€": "EUR",
        "gbp": "GBP", "pound": "GBP", "pounds": "GBP", "£": "GBP",
        "inr": "INR", "rupee": "INR", "rupees": "INR", "₹": "INR",
        "egp": "EGP",
    }
    for keyword, code in currency_map.items():
        if keyword in text:
            currency = code
            break

    # Try to detect category
    category = "Uncategorized"
    category_keywords = {
        "Food": ["food", "lunch", "dinner", "breakfast", "coffee", "restaurant", "eat", "meal", "snack"],
        "Transport": ["uber", "taxi", "bus", "metro", "fuel", "gas", "ride", "careem", "transport"],
        "Shopping": ["shopping", "clothes", "bought", "amazon", "store"],
        "Entertainment": ["movie", "netflix", "game", "concert", "fun"],
        "Health": ["pharmacy", "doctor", "medicine", "hospital", "gym"],
        "Bills": ["bill", "rent", "electric", "water", "internet", "phone"],
        "Groceries": ["grocery", "groceries", "supermarket", "market"],
        "Education": ["book", "course", "class", "tuition", "school"],
        "Travel": ["hotel", "flight", "airbnb", "travel", "trip"],
    }
    for cat, keywords in category_keywords.items():
        if any(kw in text for kw in keywords):
            category = cat
            break

    # Build description: remove the amount from the text
    description = re.sub(r"\d+(?:\.\d+)?", "", text).strip()
    # Clean up extra spaces and currency words
    for word in list(currency_map.keys()) + list(category_keywords.keys()):
        description = description.replace(word, "")
    description = " ".join(description.split()).strip(" -,.")

    return {
        "amount": amount,
        "currency": currency,
        "category": category,
        "description": description or "expense",
        "payment_method": "cash",
        "date": date.today().isoformat(),
    }


def parse_expense(message: str) -> dict:
    """Main entry point: try OpenAI first, fall back to mock parser."""
    # Try OpenAI if API key is available
    if os.getenv("OPENAI_API_KEY"):
        try:
            logger.info("Parsing with OpenAI...")
            result = parse_with_openai(message)
            logger.info("OpenAI parse successful")
            return result
        except Exception as e:
            logger.warning(f"OpenAI parsing failed: {e}, falling back to mock parser")

    # Fallback: mock/regex parser
    logger.info("Using mock parser (no API key or OpenAI failed)")
    return parse_with_mock(message)
