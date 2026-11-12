"""SerpApi Google Flights connector.

Uses the documented Google Flights engine. API keys are supplied at runtime
and are never written to disk by this module.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
CABIN_CODES = {"ECONOMY": "1", "PREMIUM_ECONOMY": "2", "BUSINESS": "3", "FIRST": "4"}


class FlightSearchError(RuntimeError):
    """A safe, user-displayable flight search error."""


def _request_json(params: dict, timeout: int = 35) -> dict:
    url = SERPAPI_ENDPOINT + "?" + urlencode(params)
    request = Request(url, headers={"User-Agent": "FlightHunterAI/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise FlightSearchError("مفتاح SerpApi غير صحيح أو غير مصرح له.") from exc
        if exc.code == 429:
            raise FlightSearchError("تم تجاوز حد الاستخدام أو الحصة المتاحة في SerpApi.") from exc
        raise FlightSearchError(f"تعذر إكمال البحث (HTTP {exc.code}).") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise FlightSearchError("تعذر الاتصال بمصدر البحث. تحقق من الإنترنت وحاول لاحقًا.") from exc
    if payload.get("error"):
        raise FlightSearchError(str(payload["error"]))
    return payload


def _flatten_flights(payload: dict) -> list[dict]:
    rows = []
    for group in ("best_flights", "other_flights"):
        for item in payload.get(group) or []:
            segments = item.get("flights") or []
            if not segments:
                continue
            first, last = segments[0], segments[-1]
            dep = (first.get("departure_airport") or {}).get("time", "")
            arr = (last.get("arrival_airport") or {}).get("time", "")
            airlines = list(dict.fromkeys(
                str(segment.get("airline", "")).strip()
                for segment in segments if segment.get("airline")
            ))
            extensions = list(item.get("extensions") or [])
            for segment in segments:
                extensions.extend(segment.get("extensions") or [])
            rows.append({
                "provider": "Google Flights عبر SerpApi",
                "airline": " / ".join(airlines) or "غير محدد",
                "origin": (first.get("departure_airport") or {}).get("id", ""),
                "destination": (last.get("arrival_airport") or {}).get("id", ""),
                "departure_at": dep,
                "arrival_at": arr,
                "price": item.get("price"),
                "currency": payload.get("search_parameters", {}).get("currency", "USD"),
                "stops": max(0, len(segments) - 1),
                "duration_minutes": int(item.get("total_duration") or sum(
                    int(segment.get("duration") or 0) for segment in segments
                )),
                "baggage_summary": "؛ ".join(dict.fromkeys(extensions)) or "تفاصيل الأمتعة غير متاحة في النتيجة",
                "booking_url": "https://www.google.com/travel/flights",
                "flight_numbers": "، ".join(
                    str(segment.get("flight_number", "")) for segment in segments if segment.get("flight_number")
                ),
                "layovers": item.get("layovers") or [],
                "departure_token": item.get("departure_token"),
                "booking_token": item.get("booking_token"),
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "result_type": item.get("type", ""),
            })
    return rows


def search_google_flights(
    *,
    api_key: str,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    adults: int = 1,
    children: int = 0,
    currency: str = "EGP",
    cabin_class: str = "ECONOMY",
    country: str = "eg",
    language: str = "ar",
    max_results: int = 20,
) -> dict:
    """Search Google Flights via SerpApi and return normalized, timestamped offers."""
    key = api_key.strip()
    if not key:
        raise FlightSearchError("أدخل مفتاح SerpApi أولاً.")
    if origin.upper() == destination.upper():
        raise FlightSearchError("مطار المغادرة يجب أن يختلف عن مطار الوصول.")
    params = {
        "engine": "google_flights",
        "api_key": key,
        "departure_id": origin.upper(),
        "arrival_id": destination.upper(),
        "outbound_date": departure_date,
        "type": "1" if return_date else "2",
        "adults": str(adults),
        "children": str(children),
        "currency": currency.upper(),
        "travel_class": CABIN_CODES.get(cabin_class.upper(), "1"),
        "gl": country,
        "hl": language,
        "sort_by": "2",
        "show_hidden": "true",
    }
    if return_date:
        params["return_date"] = return_date
    payload = _request_json(params)
    offers = _flatten_flights(payload)
    offers = [offer for offer in offers if isinstance(offer.get("price"), (int, float)) and offer["price"] > 0]
    offers.sort(key=lambda offer: offer["price"])
    return {
        "offers": offers[:max_results],
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "search_metadata": payload.get("search_metadata", {}),
        "price_insights": payload.get("price_insights", {}),
        "search_parameters": payload.get("search_parameters", {}),
        "source": "Google Flights عبر SerpApi",
        "trip_type": "ذهاب وعودة" if return_date else "ذهاب فقط",
    }
