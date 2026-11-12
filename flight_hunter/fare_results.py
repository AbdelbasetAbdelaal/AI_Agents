"""Validated fare records for transparent comparison.

This module intentionally does not fetch or scrape third-party websites.
It accepts records from explicitly permitted public feeds or user-provided CSV files.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationError, field_validator


class FareRecord(BaseModel):
    provider: str = Field(min_length=1)
    airline: str = Field(min_length=1)
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    departure_at: str
    arrival_at: str
    cabin_class: str
    price: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    stops: int = Field(ge=0)
    duration_minutes: int = Field(gt=0)
    baggage_summary: str = ""
    booking_url: str = ""
    checked_at: str

    @field_validator("origin", "destination", "currency", mode="before")
    @classmethod
    def uppercase_codes(cls, value):
        return str(value).strip().upper()

    @field_validator("cabin_class")
    @classmethod
    def normalize_cabin(cls, value):
        normalized = value.strip().lower()
        aliases = {
            "economy": "اقتصادي", "اقتصادي": "اقتصادي",
            "premium economy": "اقتصادي ممتاز", "اقتصادي ممتاز": "اقتصادي ممتاز",
            "business": "أعمال", "business class": "أعمال", "أعمال": "أعمال",
            "first": "أولى", "first class": "أولى", "أولى": "أولى",
        }
        if normalized not in aliases:
            raise ValueError("Unsupported cabin class")
        return aliases[normalized]

    @field_validator("booking_url")
    @classmethod
    def validate_booking_url(cls, value):
        value = value.strip()
        if value and urlparse(value).scheme != "https":
            raise ValueError("booking_url must use HTTPS")
        return value


CSV_COLUMNS = {
    "provider", "airline", "origin", "destination", "departure_at",
    "arrival_at", "cabin_class", "price", "currency", "stops",
    "duration_minutes", "checked_at",
}


def parse_fare_csv(content: bytes) -> tuple[list[FareRecord], list[str]]:
    """Parse a UTF-8 CSV; reject invalid rows and report their line numbers."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["الملف يجب أن يكون CSV بترميز UTF-8."]
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not CSV_COLUMNS.issubset(set(reader.fieldnames)):
        missing = sorted(CSV_COLUMNS - set(reader.fieldnames or []))
        return [], ["أعمدة CSV المطلوبة غير موجودة: " + ", ".join(missing)]
    records: list[FareRecord] = []
    errors: list[str] = []
    for line_number, row in enumerate(reader, start=2):
        try:
            records.append(FareRecord.model_validate(row))
        except ValidationError as exc:
            errors.append(f"السطر {line_number}: بيانات غير صالحة ({len(exc.errors())} أخطاء).")
    return records, errors


def filter_fares(
    records: list[FareRecord],
    *,
    origin: str,
    destination: str,
    cabin_class: str | None = None,
    currency: str | None = None,
    max_price: float | None = None,
    direct_only: bool = False,
) -> list[FareRecord]:
    """Filter only supplied verified records and sort by total fare ascending."""
    selected = [
        item for item in records
        if item.origin == origin.upper()
        and item.destination == destination.upper()
        and (cabin_class is None or item.cabin_class == cabin_class)
        and (currency is None or item.currency == currency.upper())
        and (max_price is None or item.price <= max_price)
        and (not direct_only or item.stops == 0)
    ]
    return sorted(selected, key=lambda item: item.price)


def fare_age_label(checked_at: str) -> str:
    """Return a transparent freshness label without assuming local timezone."""
    try:
        checked = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=timezone.utc)
        age_seconds = max(0, (datetime.now(timezone.utc) - checked.astimezone(timezone.utc)).total_seconds())
    except ValueError:
        return "وقت التحقق غير صالح"
    if age_seconds <= 3600:
        return "حديث (خلال ساعة)"
    if age_seconds <= 86400:
        return "تم التحقق اليوم"
    return "قديم — يلزم إعادة التحقق"
