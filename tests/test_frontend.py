from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from backend.config import Settings
from backend.errors import ServiceError
from backend.main import create_app
from frontend.tree import build_tree

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ui():
    backend = create_app(Settings(deepseek_api_key=""))

    async def no_comfy(reward):
        raise ServiceError("未连接 ComfyUI", 503)

    backend.state.images.generate = no_comfy

    async def request(method, path, payload=None, **kwargs):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=backend), base_url="http://test"
        ) as client:
            response = await client.request(method, path, json=payload)
            if not response.is_success:
                from frontend.api import APIError

                raise APIError(response.json()["detail"])
            return response.json()

    st.cache_data.clear()
    with patch("frontend.api.request", side_effect=request):
        yield AppTest.from_file(str(ROOT / "sandbox_app.py"), default_timeout=15).run()


def test_ui_generates_moves_fights_settles_and_resets(ui):
    assert not ui.exception
    assert ui.session_state["arena"]["phase"] == "SETUP"
    ui.button(key="generate_quest").click().run()
    assert not ui.exception
    arena = ui.session_state["arena"]
    assert arena["phase"] == "EXPLORING"
    assert ui.slider(key="start_hp").disabled
    arena["map"][0][1] = 2
    ui.button(key="move_right").click().run()
    assert not ui.exception
    assert ui.session_state["arena"]["phase"] == "COMBAT"
    assert ui.button(key="move_right").disabled
    ui.button(key="skill_burst").click().run()
    assert not ui.exception
    assert ui.session_state["arena"]["dps_samples"][-1]["damage"] == 36
    assert ui.button(key="skill_burst").disabled
    ui.button(key="skill_flow").click().run()
    assert not ui.exception
    assert ui.session_state["arena"]["phase"] == "EXPLORING"
    assert ui.session_state["arena"]["kills"] == 1
    ui.button(key="end_run").click().run()
    assert not ui.exception
    arena = ui.session_state["arena"]
    assert arena["phase"] == "RESULT"
    assert arena["review_attempted"] and 0 < len(arena["review"]) <= 200
    ui.button(key="poster").click().run()
    assert not ui.exception
    assert ui.session_state["arena"]["poster"]["source"] == "placeholder"
    ui.button(key="reset").click().run()
    assert not ui.exception
    arena = ui.session_state["arena"]
    assert arena["phase"] == "SETUP" and not arena["battle_log"]
    assert len(arena["path"]) == 1


def test_real_mode_failure_preserves_setup_and_shows_message(ui):
    ui.toggle(key="offline_mode").set_value(False).run()
    ui.button(key="generate_quest").click().run()
    assert not ui.exception
    assert any("DEEPSEEK_API_KEY" in error.value for error in ui.error)
    assert ui.session_state["arena"]["phase"] == "SETUP"


def test_zero_hp_generates_immediate_defeat_without_movement(ui):
    ui.slider(key="start_hp").set_value(0).run()
    ui.button(key="generate_quest").click().run()
    assert not ui.exception
    assert ui.session_state["arena"]["result"] == "defeat"
    assert ui.button(key="move_right").disabled


def test_refresh_does_not_repeat_combat_or_review(ui):
    ui.button(key="generate_quest").click().run()
    ui.session_state["arena"]["map"][0][1] = 2
    ui.button(key="move_right").click().run()
    ui.button(key="skill_burst").click().run()
    damage = len(ui.session_state["arena"]["dps_samples"])
    ui.run()
    assert len(ui.session_state["arena"]["dps_samples"]) == damage
    ui.button(key="end_run").click().run()
    review = ui.session_state["arena"]["review"]
    ui.run()
    assert ui.session_state["arena"]["review"] == review


async def test_legacy_tree_support_is_preserved():
    backend = create_app(Settings(deepseek_api_key=""))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=backend), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/quests/generate", json={"player_state": {}, "mode": "demo"}
        )
        session = response.json()
    figure = build_tree(session, session["current_id"])
    points = [
        point for trace in figure.data if trace.customdata is not None for point in trace.customdata
    ]
    assert sum(point[1] == "preview" for point in points) == 3
