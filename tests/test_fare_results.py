from flight_hunter.fare_results import FareRecord, filter_fares, parse_fare_csv


def fare(price, cabin="اقتصادي", stops=0):
    return FareRecord(
        provider="Public permitted feed",
        airline="Test Air",
        origin="CAI",
        destination="JED",
        departure_at="2027-02-10T08:00:00",
        arrival_at="2027-02-10T11:00:00",
        cabin_class=cabin,
        price=price,
        currency="EGP",
        stops=stops,
        duration_minutes=180,
        checked_at="2027-02-01T08:00:00Z",
        booking_url="https://example.com/flight",
    )


def test_fares_filter_by_cabin_and_sort_lowest_price_first():
    results = filter_fares(
        [fare(9000), fare(7000), fare(20000, "أعمال")],
        origin="CAI", destination="JED", cabin_class="اقتصادي",
    )
    assert [item.price for item in results] == [7000, 9000]


def test_direct_only_filter_excludes_connections():
    results = filter_fares(
        [fare(5000, stops=1), fare(8000, stops=0)],
        origin="CAI", destination="JED", direct_only=True,
    )
    assert [item.price for item in results] == [8000]


def test_csv_parser_accepts_valid_row_and_reports_invalid_row():
    csv_text = (
        "provider,airline,origin,destination,departure_at,arrival_at,cabin_class,"
        "price,currency,stops,duration_minutes,checked_at\n"
        "Feed,Air,CAI,JED,2027-02-10T08:00,2027-02-10T11:00,economy,"
        "7500,EGP,0,180,2027-02-01T08:00:00Z\n"
        "Feed,Air,CAI,JED,2027-02-10T08:00,2027-02-10T11:00,economy,"
        "-5,EGP,0,180,2027-02-01T08:00:00Z\n"
    )
    records, errors = parse_fare_csv(csv_text.encode())
    assert len(records) == 1
    assert records[0].cabin_class == "اقتصادي"
    assert len(errors) == 1


def test_non_https_booking_url_is_rejected():
    data = fare(1000).model_dump()
    data["booking_url"] = "http://example.com"
    try:
        FareRecord.model_validate(data)
    except ValueError:
        pass
    else:
        raise AssertionError("HTTP booking URL should be rejected")
