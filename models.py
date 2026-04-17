"""Pydantic models for expense parsing and validation."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class Expense(BaseModel):
    """Validated expense record extracted from user input."""

    amount: float = Field(..., gt=0, description="Expense amount")
    currency: str = Field(default="INR", description="ISO 4217 currency code")
    amount_base: Optional[float] = Field(default=None, description="Amount converted to base currency (INR)")
    category: str = Field(default="Uncategorized", description="Expense category")
    description: str = Field(default="", description="Short description of the expense")
    payment_method: str = Field(default="cash", description="Payment method used")
    date: str = Field(default_factory=lambda: date.today().isoformat(), description="Date of expense (YYYY-MM-DD)")
    raw_input: str = Field(default="", description="Original user message")


class TelegramMessage(BaseModel):
    """Minimal Telegram Update structure."""

    update_id: int
    message: Optional[dict] = None
