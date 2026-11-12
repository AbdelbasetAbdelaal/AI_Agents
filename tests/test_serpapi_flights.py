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
