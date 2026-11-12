from datetime import date

import httpx

from config.settings import Settings
from flight_hunter.amadeus import AmadeusClient, _duration_minutes
from flight_hunter.models import FlightSearchRequest


def test_duration_parser_supports_days_hours_and_minutes():
    assert _duration_minutes("PT2H35M") == 155
    assert _duration_minutes("P1DT1H") == 1500
    assert _duration_minutes("invalid") == 0


def test_amadeus_search_uses_oauth_and_normalizes_offer():
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "test-token", "expires_in": 1800})
        return httpx.Response(
            200,
            json={
                "dictionaries": {"carriers": {"MS": "EgyptAir"}},
                "data": [{
                    "id": "1",
                    "price": {"total": "1234.50", "currency": "EGP"},
                    "itineraries": [{
                        "duration": "PT2H10M",
                        "segments": [
                            {
                                "departure": {"iataCode": "CAI", "at": "2027-02-10T08:00:00"},
                                "arrival": {"iataCode": "JED", "at": "2027-02-10T10:10:00"},
                                "carrierCode": "MS",
                            }
                        ],
                    }],
                }],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    settings = Settings(
        amadeus_client_id="id",
        amadeus_client_secret="secret",
        amadeus_environment="test",
    )
    api = AmadeusClient(settings, client)
    request = FlightSearchRequest(
        origin="CAI",
        destination="JED",
        departure_date=date(2027, 2, 10),
        currency="EGP",
    )
    offers = api.search(request)
    assert len(offers) == 1
    assert offers[0].airline == "EgyptAir"
    assert offers[0].price == 1234.50
    assert offers[0].duration_minutes == 130
    assert offers[0].booking_url is None
    assert calls[0].url.path.endswith("/oauth2/token")
    assert calls[1].headers["authorization"] == "Bearer test-token"
    client.close()
