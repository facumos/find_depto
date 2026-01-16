"""Tests for the filters module."""

import pytest
from filters import matches


class TestMatches:
    """Tests for the matches function."""

    @pytest.fixture
    def criteria(self):
        """Default test criteria."""
        return {
            "max_price": 600000,
            "min_rooms": 2,
            "max_expensas": 100000
        }

    def test_matching_listing(self, criteria):
        """A listing that meets all criteria should match."""
        ap = {
            "price": 500000,
            "rooms": 2,
            "expensas": 80000
        }
        assert matches(ap, criteria) is True

    def test_price_too_high(self, criteria):
        """A listing with price above max should not match."""
        ap = {
            "price": 700000,
            "rooms": 2,
            "expensas": 80000
        }
        assert matches(ap, criteria) is False

    def test_price_at_limit(self, criteria):
        """A listing with price exactly at max should match."""
        ap = {
            "price": 600000,
            "rooms": 2,
            "expensas": 100000
        }
        assert matches(ap, criteria) is True

    def test_rooms_too_few(self, criteria):
        """A listing with fewer rooms than min should not match."""
        ap = {
            "price": 500000,
            "rooms": 1,
            "expensas": 80000
        }
        assert matches(ap, criteria) is False

    def test_rooms_at_minimum(self, criteria):
        """A listing with exactly min rooms should match."""
        ap = {
            "price": 500000,
            "rooms": 2,
            "expensas": 80000
        }
        assert matches(ap, criteria) is True

    def test_rooms_above_minimum(self, criteria):
        """A listing with more than min rooms should match."""
        ap = {
            "price": 500000,
            "rooms": 4,
            "expensas": 80000
        }
        assert matches(ap, criteria) is True

    def test_expensas_too_high(self, criteria):
        """A listing with expensas above max should not match."""
        ap = {
            "price": 500000,
            "rooms": 2,
            "expensas": 150000
        }
        assert matches(ap, criteria) is False

    def test_expensas_at_limit(self, criteria):
        """A listing with expensas exactly at max should match."""
        ap = {
            "price": 500000,
            "rooms": 2,
            "expensas": 100000
        }
        assert matches(ap, criteria) is True

    def test_missing_price(self, criteria):
        """A listing with None price should not match."""
        ap = {
            "price": None,
            "rooms": 2,
            "expensas": 80000
        }
        assert matches(ap, criteria) is False

    def test_missing_rooms(self, criteria):
        """A listing with None rooms should not match."""
        ap = {
            "price": 500000,
            "rooms": None,
            "expensas": 80000
        }
        assert matches(ap, criteria) is False

    def test_missing_expensas(self, criteria):
        """A listing with None expensas should match (to include MercadoLibre listings)."""
        ap = {
            "price": 500000,
            "rooms": 2,
            "expensas": None
        }
        assert matches(ap, criteria) is True

    def test_max_rooms_constraint(self):
        """When max_rooms is set, listings above it should not match."""
        criteria = {
            "max_price": 600000,
            "min_rooms": 2,
            "max_rooms": 3,
            "max_expensas": 100000
        }
        ap = {
            "price": 500000,
            "rooms": 4,
            "expensas": 80000
        }
        assert matches(ap, criteria) is False

    def test_max_rooms_at_limit(self):
        """When max_rooms is set, listings at exactly max should match."""
        criteria = {
            "max_price": 600000,
            "min_rooms": 2,
            "max_rooms": 3,
            "max_expensas": 100000
        }
        ap = {
            "price": 500000,
            "rooms": 3,
            "expensas": 80000
        }
        assert matches(ap, criteria) is True

    def test_max_rooms_not_set(self, criteria):
        """When max_rooms is not set, any number of rooms above min should match."""
        ap = {
            "price": 500000,
            "rooms": 10,
            "expensas": 80000
        }
        assert matches(ap, criteria) is True

    def test_zero_price(self, criteria):
        """A listing with zero price should match (edge case)."""
        ap = {
            "price": 0,
            "rooms": 2,
            "expensas": 80000
        }
        assert matches(ap, criteria) is True

    def test_zero_expensas(self, criteria):
        """A listing with zero expensas should match."""
        ap = {
            "price": 500000,
            "rooms": 2,
            "expensas": 0
        }
        assert matches(ap, criteria) is True
