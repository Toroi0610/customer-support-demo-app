"""Tests for GET /memory/list endpoint."""

import pytest
from unittest.mock import AsyncMock, patch
from aiohttp.test_utils import TestClient, TestServer
from aiohttp import web
import server


@pytest.fixture
def app():
    a = web.Application()
    a.router.add_get("/memory/list", server.handle_memory_list)
    a.router.add_options("/memory/list", server.handle_memory_list)
    return a


@pytest.fixture
async def client(aiohttp_client, app):
    return await aiohttp_client(app)


FAKE_MEMORIES = [
    {"summary": "楽しく話した", "emotion": "楽しそう", "importance": 0.8, "days_ago": 3},
    {"summary": "疲れていた", "emotion": "疲れている", "importance": 0.6, "days_ago": 7},
]


class TestHandleMemoryList:
    async def test_returns_memories(self, client):
        with patch.object(server, "APP_PASSWORD", "pw"), \
             patch("server.memory_store.list_recent_memories", new=AsyncMock(return_value=FAKE_MEMORIES)):
            resp = await client.get(
                "/memory/list?user_id=u1&persona=bright_friend",
                headers={"Authorization": "Bearer pw"},
            )
        assert resp.status == 200
        data = await resp.json()
        assert data["memories"] == FAKE_MEMORIES

    async def test_missing_user_id_returns_400(self, client):
        with patch.object(server, "APP_PASSWORD", "pw"):
            resp = await client.get(
                "/memory/list?persona=bright_friend",
                headers={"Authorization": "Bearer pw"},
            )
        assert resp.status == 400

    async def test_missing_persona_returns_400(self, client):
        with patch.object(server, "APP_PASSWORD", "pw"):
            resp = await client.get(
                "/memory/list?user_id=u1",
                headers={"Authorization": "Bearer pw"},
            )
        assert resp.status == 400

    async def test_wrong_password_returns_401(self, client):
        with patch.object(server, "APP_PASSWORD", "pw"):
            resp = await client.get(
                "/memory/list?user_id=u1&persona=bright_friend",
                headers={"Authorization": "Bearer wrong"},
            )
        assert resp.status == 401

    async def test_options_returns_200(self, client):
        resp = await client.options("/memory/list")
        assert resp.status == 200

    async def test_limit_param_passed_to_store(self, client):
        mock = AsyncMock(return_value=[])
        with patch.object(server, "APP_PASSWORD", "pw"), \
             patch("server.memory_store.list_recent_memories", new=mock):
            await client.get(
                "/memory/list?user_id=u1&persona=bright_friend&limit=5",
                headers={"Authorization": "Bearer pw"},
            )
        mock.assert_called_once_with("u1", "bright_friend", 5)

    async def test_invalid_limit_returns_400(self, client):
        with patch.object(server, "APP_PASSWORD", "pw"):
            resp = await client.get(
                "/memory/list?user_id=u1&persona=bright_friend&limit=abc",
                headers={"Authorization": "Bearer pw"},
            )
        assert resp.status == 400

    async def test_zero_limit_returns_400(self, client):
        with patch.object(server, "APP_PASSWORD", "pw"):
            resp = await client.get(
                "/memory/list?user_id=u1&persona=bright_friend&limit=0",
                headers={"Authorization": "Bearer pw"},
            )
        assert resp.status == 400

    async def test_negative_limit_returns_400(self, client):
        with patch.object(server, "APP_PASSWORD", "pw"):
            resp = await client.get(
                "/memory/list?user_id=u1&persona=bright_friend&limit=-1",
                headers={"Authorization": "Bearer pw"},
            )
        assert resp.status == 400
