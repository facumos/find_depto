"""Tests for the notifier module."""

import pytest
from unittest.mock import patch, Mock
import requests
from notifier import send_message


class TestSendMessage:
    """Tests for send_message function."""

    @pytest.fixture
    def sample_apartment(self):
        """Sample apartment listing for testing."""
        return {
            "price": 500000,
            "rooms": 2,
            "expensas": 80000,
            "url": "https://www.argenprop.com/depto-test"
        }

    @patch('notifier.requests.post')
    def test_successful_send(self, mock_post, sample_apartment):
        """Successful message send should return API response."""
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = send_message("test_token", "123456", sample_apartment)

        assert result["ok"] is True
        mock_post.assert_called_once()

    @patch('notifier.requests.post')
    def test_message_format(self, mock_post, sample_apartment):
        """Message should be formatted correctly with HTML."""
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        send_message("test_token", "123456", sample_apartment)

        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        assert payload["parse_mode"] == "HTML"
        assert payload["chat_id"] == "123456"
        assert "500.000" in payload["text"]
        assert "80.000" in payload["text"]
        assert "2 ambientes" in payload["text"]
        assert sample_apartment["url"] in payload["text"]

    @patch('notifier.requests.post')
    def test_api_url_format(self, mock_post, sample_apartment):
        """API URL should include the bot token."""
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        send_message("my_bot_token", "123456", sample_apartment)

        call_args = mock_post.call_args
        url = call_args[0][0]

        assert "my_bot_token" in url
        assert "sendMessage" in url

    @patch('notifier.requests.post')
    def test_retry_on_request_exception(self, mock_post, sample_apartment):
        """Should retry on request exceptions."""
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.ConnectionError("Connection failed"),
            Mock(json=Mock(return_value={"ok": True}), raise_for_status=Mock())
        ]

        with patch('notifier.time.sleep'):  # Skip actual sleep
            result = send_message("test_token", "123456", sample_apartment, max_retries=3)

        assert result["ok"] is True
        assert mock_post.call_count == 3

    @patch('notifier.requests.post')
    def test_raises_after_max_retries(self, mock_post, sample_apartment):
        """Should raise exception after exhausting retries."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with patch('notifier.time.sleep'):
            with pytest.raises(requests.exceptions.ConnectionError):
                send_message("test_token", "123456", sample_apartment, max_retries=3)

        assert mock_post.call_count == 3

    @patch('notifier.requests.post')
    def test_telegram_api_error(self, mock_post, sample_apartment):
        """Should raise exception on Telegram API error response."""
        mock_response = Mock()
        mock_response.json.return_value = {"ok": False, "description": "Bad Request: chat not found"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as excinfo:
            send_message("test_token", "123456", sample_apartment)

        assert "Telegram API error" in str(excinfo.value)
        assert "chat not found" in str(excinfo.value)

    @patch('notifier.requests.post')
    def test_handles_missing_fields(self, mock_post):
        """Should handle apartment with missing fields gracefully."""
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        ap = {"price": 500000}  # Missing rooms, expensas, url

        result = send_message("test_token", "123456", ap)

        assert result["ok"] is True
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert "N/A" in payload["text"]  # Should show N/A for missing fields

    @patch('notifier.requests.post')
    def test_timeout_parameter(self, mock_post, sample_apartment):
        """Should pass timeout to requests."""
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        send_message("test_token", "123456", sample_apartment)

        call_args = mock_post.call_args
        assert call_args[1]["timeout"] == 10
