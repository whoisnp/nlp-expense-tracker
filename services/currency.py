"""Currency conversion service — mock rates with optional API support."""

import os
import logging

logger = logging.getLogger(__name__)

BASE_CURRENCY = os.getenv("BASE_CURRENCY", "INR")

# Hardcoded mock rates to INR (as of approx. April 2026)
MOCK_RATES_TO_INR: dict[str, float] = {
    "INR": 1.0,
    "USD": 84.0,
    "EUR": 91.5,
    "GBP": 106.0,
    "EGP": 1.73,
    "AED": 22.9,
    "SAR": 22.4,
    "JPY": 0.55,
    "CAD": 61.8,
    "AUD": 54.3,
    "CHF": 94.5,
    "SGD": 62.7,
    "BDT": 0.72,
}


def convert_to_base(amount: float, currency: str) -> float:
    """
    Convert amount from given currency to base currency (INR).
    Falls back to storing in original currency if rate is unknown.
    """
    currency = currency.upper()

    if currency == BASE_CURRENCY:
        return round(amount, 2)

    rate = MOCK_RATES_TO_INR.get(currency)
    if rate is None:
        logger.warning(f"No conversion rate for {currency}. Storing original amount.")
        return round(amount, 2)

    converted = amount * rate
    logger.info(f"Converted {amount} {currency} → {converted:.2f} {BASE_CURRENCY} (rate: {rate})")
    return round(converted, 2)
