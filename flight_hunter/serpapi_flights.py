"""SerpApi Google Flights connector with outbound and return-leg retrieval.

No airline include/exclude filter is applied: Google Flights returns the carriers
available for the requested route/date. Round trips require a follow-up request
for each selected outbound departure_token, per SerpApi's documented flow.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
CABIN_CODES = {"ECONOMY": "1", "PREMIUM_ECONOMY": "2", "BUSINESS": "3", "FIRST": "4"}
MAX_ROUND_TRIP_OUTBOUNDS = 10


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
            raise FlightSearchError("تم تجاوز حصة SerpApi المجانية أو حد الطلبات.") from exc
        raise FlightSearchError(f"تعذر إكمال البحث (HTTP {exc.code}).") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise FlightSearchError("تعذر الاتصال بمصدر البحث. تحقق من الإنترنت وحاول لاحقًا.") from exc
    if payload.get("error"):
        raise FlightSearchError(str(payload["error"]))
    return payload


def _flight_groups(payload: dict) -> list[dict]:
    """Return every itinerary from both Google Flights result groups."""
    return list(payload.get("best_flights") or []) + list(payload.get("other_flights") or [])


def _normalize_itinerary(item: dict, currency: str) -> dict | None:
    segments = item.get("flights") or []
    if not segments:
        return None
    first, last = segments[0], segments[-1]
    airlines = list(dict.fromkeys(
        str(segment.get("airline", "")).strip()
        for segment in segments if segment.get("airline")
    ))
    extensions = list(item.get("extensions") or [])
    for segment in segments:
        extensions.extend(segment.get("extensions") or [])
    return {
        "airline": " / ".join(airlines) or "غير محدد",
        "departure_at": (first.get("departure_airport") or {}).get("time", ""),
        "arrival_at": (last.get("arrival_airport") or {}).get("time", ""),
        "price": item.get("price"),
        "currency": currency,
        "stops": max(0, len(segments) - 1),
        "duration_minutes": int(item.get("total_duration") or sum(
            int(segment.get("duration") or 0) for segment in segments
        )),
        "baggage_summary": "؛ ".join(dict.fromkeys(extensions)) or "تفاصيل الأمتعة غير متاحة في النتيجة",
        "flight_numbers": "، ".join(
            str(segment.get("flight_number", "")) for segment in segments if segment.get("flight_number")
        ),
        "segments": segments,
        "layovers": item.get("layovers") or [],
        "departure_token": item.get("departure_token"),
        "booking_token": item.get("booking_token"),
    }


def _flatten_flights(payload: dict) -> list[dict]:
    """Normalize one-way results (kept public for unit tests)."""
    currency = payload.get("search_parameters", {}).get("currency", "USD")
    rows = []
    for item in _flight_groups(payload):
        normalized = _normalize_itinerary(item, currency)
        if not normalized:
            continue
        first = normalized["segments"][0]
        last = normalized["segments"][-1]
        normalized.update({
            "provider": "Google Flights عبر SerpApi",
            "origin": (first.get("departure_airport") or {}).get("id", ""),
            "destination": (last.get("arrival_airport") or {}).get("id", ""),
            "booking_url": "https://www.google.com/travel/flights",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "result_type": item.get("type", ""),
        })
        rows.append(normalized)
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
    """Search available airlines; retrieve return options for selected round-trip outbounds."""
    key = api_key.strip()
    if not key:
        raise FlightSearchError("أدخل مفتاح SerpApi أولاً.")
    if origin.upper() == destination.upper():
        raise FlightSearchError("مطار المغادرة يجب أن يختلف عن مطار الوصول.")
    if return_date and return_date < departure_date:
        raise FlightSearchError("تاريخ العودة يجب أن يكون بعد تاريخ الذهاب أو مساويًا له.")

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
        "deep_search": "true",
    }
    if return_date:
        params["return_date"] = return_date

    first_payload = _request_json(params)
    checked_at = datetime.now(timezone.utc).isoformat()
    outbound_items = _flight_groups(first_payload)
    offers: list[dict] = []
    follow_up_searches = 0

    if not return_date:
        for item in outbound_items:
            normalized = _normalize_itinerary(item, currency.upper())
            if not normalized or not isinstance(normalized.get("price"), (int, float)) or normalized["price"] <= 0:
                continue
            segments = normalized.pop("segments")
            normalized.update({
                "provider": "Google Flights عبر SerpApi",
                "origin": origin.upper(),
                "destination": destination.upper(),
                "booking_url": "https://www.google.com/travel/flights",
                "checked_at": checked_at,
                "outbound_segments": segments,
                "return_segments": [],
                "return_departure_at": "",
                "return_arrival_at": "",
                "return_airline": "",
                "return_duration_minutes": None,
                "return_stops": None,
                "trip_type": "ذهاب فقط",
            })
            offers.append(normalized)
    else:
        # SerpApi returns outbound choices first. A departure_token follow-up
        # retrieves the return options for that specific outbound itinerary.
        candidates = [
            item for item in outbound_items
            if item.get("departure_token")
        ][:MAX_ROUND_TRIP_OUTBOUNDS]
        for outbound_item in candidates:
            follow_params = dict(params)
            follow_params["departure_token"] = outbound_item["departure_token"]
            return_payload = _request_json(follow_params)
            follow_up_searches += 1
            outbound = _normalize_itinerary(outbound_item, currency.upper())
            if not outbound:
                continue
            return_items = _flight_groups(return_payload)
            for return_item in return_items:
                returning = _normalize_itinerary(return_item, currency.upper())
                if not returning:
                    continue
                # The price returned after departure_token represents the
                # selected round-trip itinerary; do not add outbound price again.
                total_price = returning.get("price")
                if not isinstance(total_price, (int, float)) or total_price <= 0:
                    continue
                out_segments = outbound["segments"]
                ret_segments = returning["segments"]
                offers.append({
                    "provider": "Google Flights عبر SerpApi",
                    "airline": outbound["airline"] + " / " + returning["airline"],
                    "origin": origin.upper(),
                    "destination": destination.upper(),
                    "departure_at": outbound["departure_at"],
                    "arrival_at": outbound["arrival_at"],
                    "return_departure_at": returning["departure_at"],
                    "return_arrival_at": returning["arrival_at"],
                    "return_airline": returning["airline"],
                    "price": total_price,
                    "currency": currency.upper(),
                    "stops": outbound["stops"],
                    "return_stops": returning["stops"],
                    "duration_minutes": outbound["duration_minutes"],
                    "return_duration_minutes": returning["duration_minutes"],
                    "baggage_summary": "ذهاب: " + outbound["baggage_summary"] + " | عودة: " + returning["baggage_summary"],
                    "flight_numbers": "ذهاب: " + outbound["flight_numbers"] + " | عودة: " + returning["flight_numbers"],
                    "outbound_segments": out_segments,
                    "return_segments": ret_segments,
                    "layovers": {"outbound": outbound["layovers"], "return": returning["layovers"]},
                    "booking_token": returning.get("booking_token"),
                    "departure_token": outbound_item.get("departure_token"),
                    "booking_url": "https://www.google.com/travel/flights",
                    "checked_at": checked_at,
                    "trip_type": "ذهاب وعودة",
                })

    offers.sort(key=lambda offer: offer["price"])
    return {
        "offers": offers[:max_results],
        "checked_at": checked_at,
        "search_metadata": first_payload.get("search_metadata", {}),
        "price_insights": first_payload.get("price_insights", {}),
        "search_parameters": first_payload.get("search_parameters", {}),
        "source": "Google Flights عبر SerpApi",
        "trip_type": "ذهاب وعودة" if return_date else "ذهاب فقط",
        "outbound_candidates_found": len(outbound_items),
        "return_searches_performed": follow_up_searches,
        "airline_filter": None,
        "unique_airlines": sorted({name.strip() for offer in offers for name in offer.get("airline", "").split("/") if name.strip()}),
        "coverage_note": "لم يتم تقييد شركات الطيران؛ النتائج تشمل الشركات التي أعادها Google Flights لهذا المسار والتاريخ، وليست ضمانًا لتغطية كل شركة أو كل مخزون السوق.",
        "round_trip_note": (
            f"تم طلب خيارات العودة لما يصل إلى {MAX_ROUND_TRIP_OUTBOUNDS} من رحلات الذهاب؛ "
            "قد تستهلك الرحلة ذهابًا وعودة عدة عمليات بحث من الحصة المجانية."
            if return_date else ""
        ),
    }
