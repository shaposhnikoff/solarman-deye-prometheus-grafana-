from solarman_exporter.parser import ParameterParser

from .conftest import sample_profile


def test_parser_decodes_signed_values_and_lookups() -> None:
    parser = ParameterParser(sample_profile())

    parser.parse([0xFFFF, 5], start=1, length=2)

    assert parser.get_result() == {
        "Grid Power": -1,
        "Total Production": 5,
        "Battery SOC": 5,
        "Battery Status": "Charge",
    }
