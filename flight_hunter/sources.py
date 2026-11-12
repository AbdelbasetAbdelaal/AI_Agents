"""Public flight-search destinations; no credentials, APIs, scraping, or booking."""
from dataclasses import dataclass
from urllib.parse import quote

from .models import FlightSearchRequest


@dataclass(frozen=True)
class FlightSource:
    name: str
    category: str
    url: str
    note: str


SOURCES = [
    FlightSource("مصر للطيران", "شركات مصرية", "https://www.egyptair.com/ar/Pages/HomePage.aspx", "الموقع الرسمي"),
    FlightSource("إير كايرو", "شركات مصرية", "https://www.flyaircairo.com/", "الموقع الرسمي"),
    FlightSource("النيل للطيران", "شركات مصرية", "https://www.nileair.com/ar/", "الموقع الرسمي"),
    FlightSource("فلاي إيجيبت", "شركات مصرية", "https://www.flyegypt.com/", "الموقع الرسمي"),
    FlightSource("الخطوط السعودية", "شركات سعودية", "https://www.saudia.com/", "الموقع الرسمي"),
    FlightSource("طيران ناس", "شركات سعودية", "https://www.flynas.com/", "الموقع الرسمي"),
    FlightSource("طيران أديل", "شركات سعودية", "https://www.flyadeal.com/", "الموقع الرسمي"),
    FlightSource("طيران الرياض", "شركات سعودية", "https://www.riyadhair.com/", "الموقع الرسمي"),
    FlightSource("ويجو مصر", "مواقع مقارنة", "https://eg.wego.com/", "بحث يدوي فقط؛ شروط الاستخدام تمنع الاستعلامات الآلية"),
    FlightSource("ويجو السعودية", "مواقع مقارنة", "https://sa.wego.com/", "بحث يدوي فقط؛ شروط الاستخدام تمنع الاستعلامات الآلية"),
    FlightSource("المسافر مصر", "مواقع مقارنة", "https://eg.almosafer.com/", "مقارنة خيارات السفر في مصر"),
    FlightSource("المسافر السعودية", "مواقع مقارنة", "https://sa.almosafer.com/", "مقارنة خيارات السفر في السعودية"),
    FlightSource("الرحلة", "مواقع مقارنة", "https://www.alrehlah.com/", "منصة سفر سعودية"),
    FlightSource("وينجي مصر", "مواقع مقارنة", "https://eg.wingie.com/", "بحث يدوي فقط؛ شروط الاستخدام تمنع جمع الأسعار آلياً"),
    FlightSource("وينجي السعودية", "مواقع مقارنة", "https://sa.wingie.com/", "بحث يدوي فقط؛ شروط الاستخدام تمنع جمع الأسعار آلياً"),
    FlightSource("Google Flights", "مواقع مقارنة", "https://www.google.com/travel/flights", "بحث خارجي"),
]


def build_google_flights_url(request: FlightSearchRequest) -> str:
    """Build a prefilled Google Flights search URL; it does not fetch or claim prices."""
    route = (
        f"Flights from {request.origin} to {request.destination} "
        f"on {request.departure_date.isoformat()}"
    )
    if request.return_date:
        route += f" returning {request.return_date.isoformat()}"
    route += f" for {request.adults + request.children} passengers"
    return "https://www.google.com/travel/flights?q=" + quote(route)


def sources_by_category() -> dict[str, list[FlightSource]]:
    grouped: dict[str, list[FlightSource]] = {}
    for source in SOURCES:
        grouped.setdefault(source.category, []).append(source)
    return grouped
