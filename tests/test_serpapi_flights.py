from flight_hunter.serpapi_flights import _flatten_flights


def test_flatten_flights_normalizes_airline_price_stops_and_time():
    payload = {
        "search_parameters": {"currency": "EGP"},
        "best_flights": [{
            "flights": [
                {
                    "airline": "Air Test",
                    "flight_number": "AT 10",
                    "departure_airport": {"id": "CAI", "time": "2027-01-10 08:00"},
                    "arrival_airport": {"id": "JED", "time": "2027-01-10 11:00"},
                    "duration": 180,
                    "extensions": ["Carry-on included"],
                }
            ],
            "total_duration": 180,
            "price": 6500,
            "extensions": ["Checked baggage for a fee"],
        }],
    }
    rows = _flatten_flights(payload)
    assert len(rows) == 1
    assert rows[0]["airline"] == "Air Test"
    assert rows[0]["price"] == 6500
    assert rows[0]["currency"] == "EGP"
    assert rows[0]["stops"] == 0
    assert "Carry-on included" in rows[0]["baggage_summary"]


def test_flatten_flights_ignores_empty_or_unpriced_results():
    assert _flatten_flights({"best_flights": [{"flights": []}]}) == []


def test_round_trip_fetches_return_options_for_outbound_token(monkeypatch):
    from flight_hunter import serpapi_flights as connector

    outbound = {
        "best_flights": [{
            "price": 5000,
            "departure_token": "out-token",
            "flights": [{
                "airline": "Air Out",
                "flight_number": "AO10",
                "departure_airport": {"id": "CAI", "time": "2027-01-10 08:00"},
                "arrival_airport": {"id": "JED", "time": "2027-01-10 11:00"},
                "duration": 180,
            }],
            "total_duration": 180,
        }]
    }
    returning = {
        "best_flights": [{
            "price": 8200,
            "booking_token": "booking-token",
            "flights": [{
                "airline": "Air Back",
                "flight_number": "AB11",
                "departure_airport": {"id": "JED", "time": "2027-01-17 16:00"},
                "arrival_airport": {"id": "CAI", "time": "2027-01-17 19:00"},
                "duration": 180,
            }],
            "total_duration": 180,
        }]
    }
    calls = []

    def fake_request(params):
        calls.append(dict(params))
        return outbound if len(calls) == 1 else returning

    monkeypatch.setattr(connector, "_request_json", fake_request)
    result = connector.search_google_flights(
        api_key="test-key",
        origin="CAI",
        destination="JED",
        departure_date="2027-01-10",
        return_date="2027-01-17",
    )

    assert len(calls) == 2
    assert calls[1]["departure_token"] == "out-token"
    assert result["return_searches_performed"] == 1
    assert len(result["offers"]) == 1
    offer = result["offers"][0]
    assert offer["price"] == 8200
    assert offer["departure_at"] == "2027-01-10 08:00"
    assert offer["return_departure_at"] == "2027-01-17 16:00"
    assert offer["airline"] == "Air Out / Air Back"
