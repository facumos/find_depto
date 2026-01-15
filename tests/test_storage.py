"""Tests for the storage module."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch
import storage


class TestLoadSent:
    """Tests for load_sent function."""

    def test_load_empty_file(self, tmp_path, monkeypatch):
        """Loading an empty JSON array should return empty set."""
        db_file = tmp_path / "sent.json"
        db_file.write_text("[]")
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        result = storage.load_sent()
        assert result == set()

    def test_load_with_items(self, tmp_path, monkeypatch):
        """Loading a JSON array with items should return a set with those items."""
        db_file = tmp_path / "sent.json"
        db_file.write_text('["url1", "url2", "url3"]')
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        result = storage.load_sent()
        assert result == {"url1", "url2", "url3"}

    def test_load_nonexistent_file(self, tmp_path, monkeypatch):
        """Loading when file doesn't exist should return empty set."""
        db_file = tmp_path / "sent.json"
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        result = storage.load_sent()
        assert result == set()

    def test_load_corrupted_json(self, tmp_path, monkeypatch):
        """Loading corrupted JSON should return empty set and create backup."""
        db_file = tmp_path / "sent.json"
        db_file.write_text("not valid json {{{")
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        result = storage.load_sent()
        assert result == set()
        # Check backup was created
        backup_file = tmp_path / "sent.json.bak"
        assert backup_file.exists()

    def test_load_invalid_data_type(self, tmp_path, monkeypatch):
        """Loading JSON that is not a list should return empty set."""
        db_file = tmp_path / "sent.json"
        db_file.write_text('{"key": "value"}')  # Object instead of array
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        result = storage.load_sent()
        assert result == set()


class TestSaveSent:
    """Tests for save_sent function."""

    def test_save_empty_set(self, tmp_path, monkeypatch):
        """Saving an empty set should create a file with empty array."""
        db_file = tmp_path / "sent.json"
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        storage.save_sent(set())

        assert db_file.exists()
        data = json.loads(db_file.read_text())
        assert data == []

    def test_save_with_items(self, tmp_path, monkeypatch):
        """Saving a set with items should persist them."""
        db_file = tmp_path / "sent.json"
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        storage.save_sent({"url1", "url2", "url3"})

        assert db_file.exists()
        data = json.loads(db_file.read_text())
        assert set(data) == {"url1", "url2", "url3"}

    def test_save_overwrites_existing(self, tmp_path, monkeypatch):
        """Saving should overwrite existing file."""
        db_file = tmp_path / "sent.json"
        db_file.write_text('["old_url"]')
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        storage.save_sent({"new_url1", "new_url2"})

        data = json.loads(db_file.read_text())
        assert set(data) == {"new_url1", "new_url2"}
        assert "old_url" not in data

    def test_save_utf8_content(self, tmp_path, monkeypatch):
        """Saving URLs with special characters should work."""
        db_file = tmp_path / "sent.json"
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        urls_with_unicode = {"https://example.com/depto-ñoño", "https://example.com/café"}
        storage.save_sent(urls_with_unicode)

        data = json.loads(db_file.read_text(encoding='utf-8'))
        assert set(data) == urls_with_unicode


class TestRoundTrip:
    """Test save and load together."""

    def test_save_then_load(self, tmp_path, monkeypatch):
        """Data saved should be loadable."""
        db_file = tmp_path / "sent.json"
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        original = {"url1", "url2", "url3"}
        storage.save_sent(original)
        loaded = storage.load_sent()

        assert loaded == original

    def test_multiple_save_load_cycles(self, tmp_path, monkeypatch):
        """Multiple save/load cycles should work correctly."""
        db_file = tmp_path / "sent.json"
        monkeypatch.setattr(storage, "DB_FILE", db_file)

        # First cycle
        storage.save_sent({"url1"})
        assert storage.load_sent() == {"url1"}

        # Second cycle - add more
        current = storage.load_sent()
        current.add("url2")
        storage.save_sent(current)
        assert storage.load_sent() == {"url1", "url2"}

        # Third cycle - replace
        storage.save_sent({"url3"})
        assert storage.load_sent() == {"url3"}
