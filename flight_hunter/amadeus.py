"""Amadeus Self-Service Flight Offers Search integration."""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

import httpx

from config.settings import Settings
from .models import FlightOffer, FlightSearchRequest


class AmadeusError(RuntimeError):
    """Safe, user-displayable Amadeus integration error."""


class AmadeusClient:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=25.0)
        self._owns_client = http_client is None
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    def close(self) -> None:
        if self._owns_client:
            self.http.close()

    def _get_access_token(self) -> str:
        now = datetime.now(timezone.utc).timestamp()
        if self._access_token and now < self._token_expires_at - 60:
            return self._access_token

        if not self.settings.amadeus_client_id or not self.settings.amadeus_client_secret:
            raise AmadeusError(
                "أدخل AMADEUS_CLIENT_ID و AMADEUS_CLIENT_SECRET في ملف .env أولاً."
            )

        try:
            response = self.http.post(
                f"{self.settings.amadeus_base_url}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.amadeus_client_id,
                    "client_secret": self.settings.amadeus_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise AmadeusError(
                f"فشل تسجيل الدخول إلى Amadeus (HTTP {exc.response.status_code}). "
                "راجع مفاتيح API وبيئة الحساب."
            ) from None
        except (httpx.HTTPError, ValueError):
            raise AmadeusError("تعذر الاتصال بخدمة تسجيل الدخول في Amadeus.") from None

        token = payload.get("access_token")
        if not token:
            raise AmadeusError("لم تُرجع Amadeus رمز وصول صالحاً.")
        self._access_token = token
        self._token_expires_at = now + int(payload.get("expires_in", 1799))
        return token

    def search(self, request: FlightSearchRequest, max_results: int = 50) -> list[FlightOffer]:
        token = self._get_access_token()
        params: dict[str, Any] = {
            "originLocationCode": request.origin.upper(),
            "destinationLocationCode": request.destination.upper(),
            "departureDate": request.departure_date.isoformat(),
            "adults": request.adults,
            "children": request.children,
            "currencyCode": request.currency.upper(),
            "travelClass": request.cabin_class,
            "max": max(1, min(max_results, 250)),
        }
        if request.return_date:
            params["returnDate"] = request.return_date.isoformat()

        try:
            response = self.http.get(
                f"{self.settings.amadeus_base_url}/v2/shopping/flight-offers",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                self._access_token = None
                raise AmadeusError("رفضت Amadeus صلاحية الوصول. تحقق من مفاتيح API والبيئة.") from None
            if status == 400:
                raise AmadeusError(
                    "رفضت Amadeus معايير البحث. قد لا تكون العملة أو المسار أو التاريخ مدعوماً."
                ) from None
            if status == 429:
                raise AmadeusError("تم تجاوز حد طلبات Amadeus مؤقتاً. حاول لاحقاً.") from None
            raise AmadeusError(f"تعذر إكمال البحث لدى Amadeus (HTTP {status}).") from None
        except (httpx.HTTPError, ValueError):
            raise AmadeusError("حدث خطأ في الاتصال أو في قراءة رد Amadeus.") from None

        dictionaries = payload.get("dictionaries", {})
        carriers = dictionaries.get("carriers", {})
        offers: list[FlightOffer] = []
        for raw in payload.get("data", []):
            try:
                itineraries = raw.get("itineraries", [])
                if not itineraries:
                    continue
                outbound = itineraries[0]
                segments = outbound.get("segments", [])
                if not segments:
                    continue
                first, last = segments[0], segments[-1]
                carrier_codes = list(dict.fromkeys(
                    segment.get("carrierCode", "") for segment in segments
                    if segment.get("carrierCode")
                ))
                airline_names = [carriers.get(code, code) for code in carrier_codes]
                duration = _duration_minutes(outbound.get("duration", ""))
                price_data = raw.get("price", {})
                total = float(price_data.get("grandTotal", price_data.get("total")))
                baggage = _baggage_summary(raw)
                offers.append(
                    FlightOffer(
                        provider="Amadeus",
                        airline=" / ".join(airline_names) or "غير محددة",
                        origin=first.get("departure", {}).get("iataCode", request.origin),
                        destination=last.get("arrival", {}).get("iataCode", request.destination),
                        departure_at=first.get("departure", {}).get("at", ""),
                        arrival_at=last.get("arrival", {}).get("at", ""),
                        price=total,
                        currency=price_data.get("currency", request.currency),
                        stops=max(0, len(segments) - 1),
                        duration_minutes=duration,
                        booking_url=None,
                        baggage_summary=baggage,
                        offer_id=raw.get("id"),
                        itinerary_details=[
                            _summarize_itinerary(item, index, carriers)
                            for index, item in enumerate(itineraries)
                        ],
                    )
                )
            except (KeyError, TypeError, ValueError):
                # Ignore malformed individual offers without failing the whole search.
                continue
        return offers


def _duration_minutes(value: str) -> int:
    match = re.fullmatch(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?", value or "")
    if not match:
        return 0
    days, hours, minutes = (int(part or 0) for part in match.groups())
    return days * 1440 + hours * 60 + minutes


def _summarize_itinerary(item: dict[str, Any], index: int, carriers: dict[str, str]) -> dict[str, Any]:
    segments = item.get("segments", [])
    if not segments:
        return {"direction": "الذهاب" if index == 0 else "العودة"}
    first, last = segments[0], segments[-1]
    codes = list(dict.fromkeys(s.get("carrierCode", "") for s in segments if s.get("carrierCode")))
    return {
        "direction": "الذهاب" if index == 0 else "العودة",
        "from": first.get("departure", {}).get("iataCode", ""),
        "to": last.get("arrival", {}).get("iataCode", ""),
        "departure": first.get("departure", {}).get("at", ""),
        "arrival": last.get("arrival", {}).get("at", ""),
        "stops": max(0, len(segments) - 1),
        "duration_minutes": _duration_minutes(item.get("duration", "")),
        "airlines": " / ".join(carriers.get(code, code) for code in codes),
    }


def _baggage_summary(offer: dict[str, Any]) -> str | None:
    details = offer.get("travelerPricings", [])
    quantities: list[str] = []
    for traveler in details:
        for fare in traveler.get("fareDetailsBySegment", []):
            allowance = fare.get("includedCheckedBags", {})
            if allowance.get("quantity") is not None:
                quantities.append(f'{allowance["quantity"]} قطعة')
            elif allowance.get("weight") is not None:
                quantities.append(f'{allowance["weight"]} {allowance.get("weightUnit", "KG")}')
    return "، ".join(dict.fromkeys(quantities)) if quantities else None
