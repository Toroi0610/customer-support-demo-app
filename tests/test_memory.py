"""Tests for memory utility functions in server.py."""

import pytest
import server


class TestFormatMemoriesForPrompt:
    def test_empty_memories(self):
        assert server.format_memories_for_prompt([]) == ""

    def test_single_memory(self):
        memories = [{"summary": "楽しく話した", "emotion": "楽しそう", "importance": 0.8, "days_ago": 2}]
        result = server.format_memories_for_prompt(memories)
        assert "[過去の記憶]" in result
        assert "楽しく話した" in result
        assert "楽しそう" in result

    def test_multiple_memories(self):
        memories = [
            {"summary": "A", "emotion": "X", "importance": 0.9, "days_ago": 1},
            {"summary": "B", "emotion": "Y", "importance": 0.5, "days_ago": 7},
        ]
        result = server.format_memories_for_prompt(memories)
        assert "A" in result
        assert "B" in result

    def test_today_label(self):
        memories = [{"summary": "今日話した", "emotion": "楽しそう", "importance": 0.8, "days_ago": 0}]
        result = server.format_memories_for_prompt(memories)
        assert "今日" in result

    def test_yesterday_label(self):
        memories = [{"summary": "昨日話した", "emotion": "楽しそう", "importance": 0.8, "days_ago": 1}]
        result = server.format_memories_for_prompt(memories)
        assert "昨日" in result

    def test_missing_importance_uses_default(self):
        memories = [{"summary": "話した", "emotion": "楽しそう", "days_ago": 2}]  # no importance key
        result = server.format_memories_for_prompt(memories)
        assert "話した" in result  # should not raise KeyError


class TestInjectMemoriesIntoSetup:
    def test_injects_into_system_instruction(self):
        session_data = {
            "setup": {
                "system_instruction": {"parts": [{"text": "あなたは彼女です。"}]}
            }
        }
        memories = [{"summary": "疲れていた", "emotion": "疲れている", "importance": 0.7, "days_ago": 3}]
        server.inject_memories_into_setup(session_data, memories)
        text = session_data["setup"]["system_instruction"]["parts"][0]["text"]
        assert "あなたは彼女です。" in text
        assert "[過去の記憶]" in text
        assert "疲れていた" in text

    def test_no_op_on_empty_memories(self):
        session_data = {
            "setup": {
                "system_instruction": {"parts": [{"text": "original"}]}
            }
        }
        server.inject_memories_into_setup(session_data, [])
        assert session_data["setup"]["system_instruction"]["parts"][0]["text"] == "original"

    def test_no_op_when_setup_key_missing(self):
        session_data = {"other": "data"}
        server.inject_memories_into_setup(session_data, [{"summary": "x", "emotion": "y", "importance": 0.5, "days_ago": 1}])
        assert "setup" not in session_data

    def test_no_op_when_parts_empty(self):
        session_data = {
            "setup": {
                "system_instruction": {"parts": []}
            }
        }
        # Should not raise — no-op on IndexError
        server.inject_memories_into_setup(session_data, [{"summary": "x", "emotion": "y", "importance": 0.5, "days_ago": 1}])

    def test_no_op_when_part_has_no_text_key(self):
        session_data = {
            "setup": {
                "system_instruction": {"parts": [{"other": "data"}]}
            }
        }
        # Should not raise — no-op on KeyError
        server.inject_memories_into_setup(session_data, [{"summary": "x", "emotion": "y", "importance": 0.5, "days_ago": 1}])
