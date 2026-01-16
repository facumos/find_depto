"""Integration tests for the apartment bot."""

import pytest
from unittest.mock import patch, Mock
import json

from filters import matches
from storage import load_sent, save_sent
import storage


class TestEndToEndFlow:
    """Tests that simulate the full bot flow."""

    @pytest.fixture
    def mock_listings(self):
        """Sample listings as would come from the scraper."""
        return [
            {
                "id": "https://www.argenprop.com/depto-1",
                "price": 450000,
                "rooms": 2,
                "expensas": 70000,
                "url": "https://www.argenprop.com/depto-1",
                "source": "argenprop"
            },
            {
                "id": "https://www.argenprop.com/depto-2",
                "price": 800000,  # Too expensive
                "rooms": 3,
                "expensas": 90000,
                "url": "https://www.argenprop.com/depto-2",
                "source": "argenprop"
            },
            {
                "id": "https://www.argenprop.com/depto-3",
                "price": 500000,
                "rooms": 1,  # Too few rooms
                "expensas": 60000,
                "url": "https://www.argenprop.com/depto-3",
                "source": "argenprop"
            },
            {
                "id": "https://www.argenprop.com/depto-4",
                "price": 550000,
                "rooms": 3,
                "expensas": 150000,  # Expensas too high
                "url": "https://www.argenprop.com/depto-4",
                "source": "argenprop"
            },
            {
                "id": "https://www.argenprop.com/depto-5",
                "price": 480000,
                "rooms": 2,
                "expensas": 85000,
                "url": "https://www.argenprop.com/depto-5",
                "source": "argenprop"
            },
        ]

    @pytest.fixture
    def criteria(self):
        """Test criteria matching main.py defaults."""
        return {
            "max_price": 600000,
            "min_rooms": 2,
            "max_expensas": 100000
        }

    def test_filtering_flow(self, mock_listings, criteria):
        """Test that filtering correctly identifies matching listings."""
        matching = [ap for ap in mock_listings if matches(ap, criteria)]

        # Should match depto-1 and depto-5 only
        assert len(matching) == 2
        urls = {ap["url"] for ap in matching}
        assert "https://www.argenprop.com/depto-1" in urls
        assert "https://www.argenprop.com/depto-5" in urls

    def test_deduplication_flow(self, mock_listings, criteria, tmp_path, monkeypatch):
        """Test that already-sent listings are not processed again."""
        db_file = tmp_path / "sent.json"
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        # Simulate first run - save one listing as already sent
        already_sent = {"https://www.argenprop.com/depto-1"}
        save_sent(already_sent)

        # Load sent listings
        sent = load_sent()

        # Filter: matching + not already sent
        new_matching = [
            ap for ap in mock_listings
            if matches(ap, criteria) and ap["id"] not in sent
        ]

        # Should only get depto-5 (depto-1 was already sent)
        assert len(new_matching) == 1
        assert new_matching[0]["url"] == "https://www.argenprop.com/depto-5"

    def test_full_check_and_notify_simulation(self, mock_listings, criteria, tmp_path, monkeypatch):
        """Simulate the full check_and_notify flow from main.py."""
        db_file = tmp_path / "sent.json"
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        # Track what would be sent
        sent_notifications = []

        def mock_send_message(token, chat_id, ap):
            sent_notifications.append(ap)
            return {"ok": True}

        # Simulate check_and_notify logic
        sent = load_sent()
        new_count = 0

        for ap in mock_listings:
            if ap["id"] in sent:
                continue
            if not matches(ap, criteria):
                continue

            # Would send notification here
            mock_send_message("token", "chat_id", ap)
            sent.add(ap["id"])
            new_count += 1

        save_sent(sent)

        # Verify results
        assert new_count == 2
        assert len(sent_notifications) == 2

        # Run again - should find nothing new
        sent_notifications.clear()
        sent = load_sent()
        new_count = 0

        for ap in mock_listings:
            if ap["id"] in sent:
                continue
            if not matches(ap, criteria):
                continue

            mock_send_message("token", "chat_id", ap)
            sent.add(ap["id"])
            new_count += 1

        assert new_count == 0
        assert len(sent_notifications) == 0


class TestScraperIntegration:
    """Test scraper with mocked HTTP responses."""

    @patch('scrappers.argenprop.requests.get')
    def test_scrape_with_mock_html(self, mock_get):
        """Test scraper parses HTML correctly."""
        from scrappers.argenprop import scrape_argenprop

        # Sample HTML mimicking ArgenProp structure
        mock_html = """
        <html>
        <body>
            <div class="listing__item">
                <a href="/departamento/depto-1">
                    <div class="card__price">$450.000+ $70.000 expensas</div>
                </a>
                <span>2 amb</span>
            </div>
            <div class="listing__item">
                <a href="/departamento/depto-2">
                    <div class="card__price">$600.000+ $90.000 expensas</div>
                </a>
                <span>3 ambientes</span>
            </div>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        listings = scrape_argenprop(max_pages=1, delay=0)

        assert len(listings) == 2

        # Check first listing
        assert listings[0]["price"] == 450000
        assert listings[0]["expensas"] == 70000
        assert listings[0]["rooms"] == 2

        # Check second listing
        assert listings[1]["price"] == 600000
        assert listings[1]["expensas"] == 90000
        assert listings[1]["rooms"] == 3


class TestNotifierIntegration:
    """Test notifier message formatting."""

    @patch('notifier.requests.post')
    def test_notification_message_content(self, mock_post):
        """Verify notification message contains all required info."""
        from notifier import send_message

        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        listing = {
            "price": 450000,
            "rooms": 2,
            "expensas": 70000,
            "url": "https://www.argenprop.com/depto-test"
        }

        send_message("test_token", "test_chat", listing)

        # Get the message that was sent
        call_args = mock_post.call_args
        message_text = call_args[1]["json"]["text"]

        # Verify all info is present
        assert "450.000" in message_text
        assert "70.000" in message_text
        assert "2 ambientes" in message_text
        assert "https://www.argenprop.com/depto-test" in message_text
        assert "Nuevo depto" in message_text
        assert "La Plata" in message_text
