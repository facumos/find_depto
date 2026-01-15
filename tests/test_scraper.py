"""Tests for the ArgenProp scraper module."""

import pytest
from scrappers.argenprop import parse_price_and_expensas, parse_rooms


class TestParsePriceAndExpensas:
    """Tests for parse_price_and_expensas function."""

    def test_standard_format(self):
        """Parse standard format: '$510.000+ $70.000 expensas'."""
        text = "$510.000+ $70.000 expensas"
        price, expensas = parse_price_and_expensas(text)
        assert price == 510000
        assert expensas == 70000

    def test_no_spaces(self):
        """Parse format without spaces: '$510.000+$70.000 expensas'."""
        text = "$510.000+$70.000 expensas"
        price, expensas = parse_price_and_expensas(text)
        assert price == 510000
        assert expensas == 70000

    def test_extra_spaces(self):
        """Parse format with extra spaces."""
        text = "$510.000  +  $70.000 expensas"
        price, expensas = parse_price_and_expensas(text)
        assert price == 510000
        assert expensas == 70000

    def test_with_newlines(self):
        """Parse format with newlines."""
        text = "$510.000\n+ $70.000 expensas"
        price, expensas = parse_price_and_expensas(text)
        assert price == 510000
        assert expensas == 70000

    def test_price_only(self):
        """Parse when only price is present (no expensas)."""
        text = "$450.000"
        price, expensas = parse_price_and_expensas(text)
        assert price == 450000
        assert expensas is None

    def test_large_numbers(self):
        """Parse large price values."""
        text = "$1.200.000+ $150.000 expensas"
        price, expensas = parse_price_and_expensas(text)
        assert price == 1200000
        assert expensas == 150000

    def test_small_numbers(self):
        """Parse small price values."""
        text = "$50.000+ $5.000 expensas"
        price, expensas = parse_price_and_expensas(text)
        assert price == 50000
        assert expensas == 5000

    def test_no_dots_in_numbers(self):
        """Parse numbers without thousand separators."""
        text = "$500000+ $70000 expensas"
        price, expensas = parse_price_and_expensas(text)
        assert price == 500000
        assert expensas == 70000

    def test_empty_string(self):
        """Empty string should return None, None."""
        text = ""
        price, expensas = parse_price_and_expensas(text)
        assert price is None
        assert expensas is None

    def test_invalid_text(self):
        """Invalid text should return None, None."""
        text = "contact for price"
        price, expensas = parse_price_and_expensas(text)
        assert price is None
        assert expensas is None


class TestParseRooms:
    """Tests for parse_rooms function."""

    def test_ambientes_short(self):
        """Parse '2 amb' format."""
        text = "Departamento 2 amb en alquiler"
        rooms = parse_rooms(text)
        assert rooms == 2

    def test_ambientes_full(self):
        """Parse '3 ambientes' format."""
        text = "Departamento 3 ambientes"
        rooms = parse_rooms(text)
        assert rooms == 3

    def test_ambiente_singular(self):
        """Parse '1 ambiente' format."""
        text = "Monoambiente 1 ambiente"
        rooms = parse_rooms(text)
        assert rooms == 1

    def test_dormitorio_singular(self):
        """Parse '1 dormitorio' - should convert to 2 ambientes."""
        text = "Departamento con 1 dormitorio"
        rooms = parse_rooms(text)
        assert rooms == 2  # 1 bedroom + living = 2 ambientes

    def test_dormitorios_plural(self):
        """Parse '2 dormitorios' - should convert to 3 ambientes."""
        text = "Departamento con 2 dormitorios"
        rooms = parse_rooms(text)
        assert rooms == 3  # 2 bedrooms + living = 3 ambientes

    def test_dorm_short(self):
        """Parse '1 dorm' short format."""
        text = "Depto 1 dorm luminoso"
        rooms = parse_rooms(text)
        assert rooms == 2  # 1 bedroom + living = 2 ambientes

    def test_dorms_short(self):
        """Parse '3 dorms' short format."""
        text = "Depto 3 dorms muy amplio"
        rooms = parse_rooms(text)
        assert rooms == 4  # 3 bedrooms + living = 4 ambientes

    def test_ambientes_takes_priority(self):
        """When both formats present, 'ambientes' should be used."""
        text = "2 amb 1 dormitorio"
        rooms = parse_rooms(text)
        assert rooms == 2  # 'amb' pattern matches first

    def test_no_room_info(self):
        """When no room info present, should return None."""
        text = "Hermoso departamento en alquiler"
        rooms = parse_rooms(text)
        assert rooms is None

    def test_empty_string(self):
        """Empty string should return None."""
        text = ""
        rooms = parse_rooms(text)
        assert rooms is None

    def test_case_insensitive(self):
        """Parsing should be case insensitive."""
        text = "2 AMB departamento"
        rooms = parse_rooms(text)
        assert rooms == 2

    def test_ambientes_with_extra_s(self):
        """Handle 'ambientes' with trailing s."""
        text = "3 ambientes"
        rooms = parse_rooms(text)
        assert rooms == 3
