"""Pytest configuration and shared fixtures."""

import pytest
import logging

# Suppress logging during tests
logging.disable(logging.CRITICAL)


@pytest.fixture
def sample_listing():
    """A complete sample listing for testing."""
    return {
        "id": "https://www.argenprop.com/depto-test-123",
        "price": 500000,
        "rooms": 2,
        "expensas": 80000,
        "url": "https://www.argenprop.com/depto-test-123",
        "source": "argenprop"
    }


@pytest.fixture
def default_criteria():
    """Default search criteria for testing."""
    return {
        "max_price": 600000,
        "min_rooms": 2,
        "max_expensas": 100000
    }
