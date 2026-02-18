"""Tests for server.py authentication logic."""

import pytest
from unittest.mock import patch
import server


class TestVerifyAppPassword:
    """Tests for verify_app_password()"""

    def test_correct_password_accepted(self):
        """Correct password returns True."""
        with patch.object(server, "APP_PASSWORD", "secret123"):
            assert server.verify_app_password("secret123") is True

    def test_wrong_password_rejected(self):
        """Wrong password returns False."""
        with patch.object(server, "APP_PASSWORD", "secret123"):
            assert server.verify_app_password("wrong") is False

    def test_empty_input_rejected_when_password_set(self):
        """Empty string is rejected when APP_PASSWORD is configured."""
        with patch.object(server, "APP_PASSWORD", "secret123"):
            assert server.verify_app_password("") is False

    def test_no_app_password_rejects_all(self):
        """When APP_PASSWORD is not set, ALL connections are rejected
        (including empty string — no dev-mode bypass)."""
        with patch.object(server, "APP_PASSWORD", ""):
            assert server.verify_app_password("") is False
            assert server.verify_app_password("anypassword") is False
            assert server.verify_app_password("secret123") is False

    def test_password_is_case_sensitive(self):
        """Password comparison is case-sensitive."""
        with patch.object(server, "APP_PASSWORD", "Secret123"):
            assert server.verify_app_password("secret123") is False
            assert server.verify_app_password("SECRET123") is False
            assert server.verify_app_password("Secret123") is True

    def test_password_with_special_characters(self):
        """Passwords with special characters are handled correctly."""
        pw = "Ui0610Tup0609@TM"
        with patch.object(server, "APP_PASSWORD", pw):
            assert server.verify_app_password(pw) is True
            assert server.verify_app_password("Ui0610Tup0609@tm") is False

    def test_partial_match_rejected(self):
        """A prefix of the correct password is rejected."""
        with patch.object(server, "APP_PASSWORD", "secret123"):
            assert server.verify_app_password("secret") is False

    def test_padded_password_rejected(self):
        """Password with extra whitespace is rejected."""
        with patch.object(server, "APP_PASSWORD", "secret123"):
            assert server.verify_app_password(" secret123") is False
            assert server.verify_app_password("secret123 ") is False
