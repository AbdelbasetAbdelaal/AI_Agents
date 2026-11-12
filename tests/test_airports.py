from flight_hunter.airports import AIRPORTS, AIRPORT_LABELS


def test_main_egyptian_airports_have_iata_codes():
    assert AIRPORTS["القاهرة — CAI"] == "CAI"
    assert AIRPORTS["سفنكس — SPX"] == "SPX"
    assert AIRPORTS["الإسكندرية / برج العرب — HBE"] == "HBE"
    assert len(AIRPORTS) >= 8


def test_saudi_airports_are_available_for_search():
    assert AIRPORTS["جدة — JED"] == "JED"
    assert AIRPORTS["المدينة المنورة — MED"] == "MED"
    assert AIRPORTS["الرياض — RUH"] == "RUH"
    assert AIRPORTS["الدمام — DMM"] == "DMM"


def test_airport_labels_are_unique_and_match_catalog():
    assert len(AIRPORT_LABELS) == len(set(AIRPORT_LABELS))
    assert set(AIRPORT_LABELS) == set(AIRPORTS)
