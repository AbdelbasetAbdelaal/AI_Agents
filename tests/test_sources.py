from datetime import date
from urllib.parse import unquote, urlparse

from flight_hunter.models import FlightSearchRequest
from flight_hunter.sources import SOURCES, build_google_flights_url, sources_by_category


def test_source_catalog_includes_egyptian_and_saudi_airlines_and_comparison_sites():
    grouped = sources_by_category()
    assert len(grouped["شركات مصرية"]) >= 4
    assert len(grouped["شركات سعودية"]) >= 4
    assert len(grouped["مواقع مقارنة"]) >= 3
    assert all(source.url.startswith("https://") for source in SOURCES)


def test_google_flights_link_contains_route_and_dates():
    request = FlightSearchRequest(
        origin="CAI",
        destination="JED",
        departure_date=date(2027, 2, 10),
        return_date=date(2027, 2, 17),
        adults=2,
    )
    url = build_google_flights_url(request)
    query = unquote(urlparse(url).query)
    assert "CAI" in query and "JED" in query
    assert "2027-02-10" in query and "2027-02-17" in query


def test_source_catalog_never_requires_credentials():
    assert all("api" not in source.url.lower() for source in SOURCES)
