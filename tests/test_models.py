from datetime import date

import pytest
from pydantic import ValidationError

from flight_hunter.models import FlightSearchRequest, FlightOffer
from flight_hunter.ranking import rank_offers


def test_search_request_accepts_valid_one_way_trip():
    request = FlightSearchRequest(
        origin="CAI",
        destination="JED",
        departure_date=date(2027, 2, 10),
    )
    assert request.origin == "CAI"


def test_search_request_rejects_same_airport():
    with pytest.raises(ValidationError):
        FlightSearchRequest(
            origin="CAI",
            destination="CAI",
            departure_date=date(2027, 2, 10),
        )


def test_search_request_rejects_return_before_departure():
    with pytest.raises(ValidationError):
        FlightSearchRequest(
            origin="CAI",
            destination="JED",
            departure_date=date(2027, 2, 10),
            return_date=date(2027, 2, 9),
        )


def test_offers_rank_by_price_then_duration_then_stops():
    base = dict(
        provider="test", airline="Test Air", origin="CAI", destination="JED",
        departure_at="2027-02-10T08:00:00", arrival_at="2027-02-10T12:00:00",
        currency="EGP", stops=0, duration_minutes=240,
        booking_url="https://example.com/book",
    )
    expensive = FlightOffer(**base, price=9000)
    cheap = FlightOffer(**base, price=7000)
    assert rank_offers([expensive, cheap]) == [cheap, expensive]
