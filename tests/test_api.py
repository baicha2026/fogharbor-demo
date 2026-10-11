import asyncio

import httpx
import pytest

from backend.config import Settings
from backend.errors import ServiceError
from backend.main import create_app


@pytest.fixture
async def client():
    app = create_app(Settings(deepseek_api_key=""))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def create_session(client, state=None):
    response = await client.post(
        "/api/quests/generate",
        json={
            "player_state": state or {"level": 10, "gold": 250, "hp": 70, "reputation": 15},
            "theme": "雾港",
            "mode": "demo",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_generate_choose_and_revisit_are_idempotent(client):
    session = await create_session(client)
    root = session["nodes"][0]
    branch = root["quest"]["branches"][0]
    payload = {"node_id": root["id"], "action": branch["action"]}
    route = f"/api/sessions/{session['id']}/choose"
    response = await client.post(route, json=payload)
    assert response.status_code == 200
    extended = response.json()
    child = extended["nodes"][1]
    assert len(extended["nodes"]) == 2
    assert child["player_state"]["gold"] == root["player_state"]["gold"] + branch["effects"]["gold"]
    assert child["parent_id"] == root["id"]
    repeated = (await client.post(route, json=payload)).json()
    assert len(repeated["nodes"]) == 2
    assert repeated["current_id"] == child["id"]
    sibling = (await client.post(route, json={"node_id": root["id"], "action": "refuse"})).json()
    assert len(sibling["nodes"]) == 3
    assert sibling["nodes"][2]["parent_id"] == root["id"]


async def test_concurrent_double_click_creates_one_child(client):
    session = await create_session(client)
    route = f"/api/sessions/{session['id']}/choose"
    payload = {"node_id": session["root_id"], "action": "accept"}
    responses = await asyncio.gather(
        client.post(route, json=payload), client.post(route, json=payload)
    )
    assert all(response.status_code == 200 for response in responses)
    snapshot = (await client.get(f"/api/sessions/{session['id']}")).json()
    assert len(snapshot["nodes"]) == 2


async def test_invalid_input_and_missing_session(client):
    response = await client.post("/api/quests/generate", json={"player_state": {"hp": -1}})
    assert response.status_code == 422
    response = await client.post(
        "/api/sessions/missing/choose", json={"node_id": "missing", "action": "accept"}
    )
    assert response.status_code == 404


async def test_real_mode_never_silently_falls_back(client):
    response = await client.post(
        "/api/quests/generate",
        json={
            "player_state": {},
            "theme": "海港",
            "mode": "deepseek",
        },
    )
    assert response.status_code == 503
    assert "DEEPSEEK_API_KEY" in response.json()["detail"]


async def test_generation_failure_does_not_commit_state():
    app = create_app(Settings(deepseek_api_key=""))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        session = await create_session(c)

        class BrokenGenerator:
            async def generate(self, player, theme, history):
                raise ServiceError("模拟上游超时", 504)

        app.state.sessions.generators["demo"] = BrokenGenerator()
        response = await c.post(
            f"/api/sessions/{session['id']}/choose",
            json={
                "node_id": session["root_id"],
                "action": "accept",
            },
        )
        assert response.status_code == 504
        saved = (await c.get(f"/api/sessions/{session['id']}")).json()
        assert saved["nodes"] == session["nodes"]
        assert saved["current_id"] == session["current_id"]


async def test_depth_limit_is_explicit():
    app = create_app(Settings(max_depth=1))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        session = await create_session(c)
        route = f"/api/sessions/{session['id']}/choose"
        child = (
            await c.post(route, json={"node_id": session["root_id"], "action": "accept"})
        ).json()
        response = await c.post(route, json={"node_id": child["current_id"], "action": "accept"})
        assert response.status_code == 409


async def test_expired_sessions_are_removed():
    app = create_app(Settings(session_ttl_seconds=1))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        session = await create_session(c)
        app.state.sessions.entries[session["id"]].touched -= 2
        response = await c.get(f"/api/sessions/{session['id']}")
        assert response.status_code == 404
        assert session["id"] not in app.state.sessions.entries


async def test_image_endpoint_uses_selected_node_reward(quest_data):
    import base64

    from backend.models import ImageResult

    app = create_app(Settings(deepseek_api_key=""))

    class ImageGenerator:
        async def generate(self, reward):
            return ImageResult(
                image_base64=base64.b64encode(b"image-test").decode(),
                mime_type="image/png",
                prompt_id="test",
                item_name=reward.item_name,
            )

    app.state.images.generate = ImageGenerator().generate
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        session = await create_session(c)
        response = await c.post(
            f"/api/sessions/{session['id']}/nodes/{session['root_id']}/reward-image"
        )
        assert response.status_code == 200
        assert response.json()["item_name"] == session["nodes"][0]["quest"]["rewards"]["item_name"]
