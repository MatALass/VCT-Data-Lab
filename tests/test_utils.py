from vlr_analytics.utils import normalize_map_name, percent_to_float


def test_normalize_map_name_removes_prefix():
    assert normalize_map_name("L Lotus") == "Lotus"


def test_normalize_map_name_empty_is_all_maps():
    assert normalize_map_name("") == "All Maps"


def test_percent_to_float():
    assert percent_to_float("42%") == 0.42
