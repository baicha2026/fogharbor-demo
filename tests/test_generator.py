import json

import httpx
import pytest

from backend.config import Settings
from backend.errors import ServiceError
from backend.generator import DeepSeekGenerator, DemoGenerator
from backend.models import PlayerState


async def test_deepseek_uses_json_mode_and_passes_state(quest_data):
    calls = []

    async def respond(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert request.headers["authorization"] == "Bearer test-only"
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(quest_data)}}]}
        )

    generator = DeepSeekGenerator(
        Settings(deepseek_api_key="test-only"), transport=httpx.MockTransport(respond)
    )
    quest = await generator.generate(PlayerState(level=12), "海港", [])
    assert quest.name == quest_data["name"]
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["thinking"] == {"type": "disabled"}
    assert '"level": 12' in calls[0]["messages"][1]["content"]
    assert "json" in calls[0]["messages"][0]["content"].lower()


async def test_invalid_output_is_repaired_once(quest_data):
    attempts = []

    async def respond(request):
        attempts.append(json.loads(request.content))
        content = '{"name":"incomplete"}' if len(attempts) == 1 else json.dumps(quest_data)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    generator = DeepSeekGenerator(
        Settings(deepseek_api_key="test-only"), transport=httpx.MockTransport(respond)
    )
    await generator.generate(PlayerState(), "海港", [])
    assert len(attempts) == 2
    assert attempts[1]["messages"][-1]["role"] == "user"


@pytest.mark.parametrize("status,expected", [(401, 502), (429, 429), (500, 502)])
async def test_upstream_errors_are_sanitized(status, expected):
    generator = DeepSeekGenerator(
        Settings(deepseek_api_key="never-expose-this"),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(status, text="secret-upstream-body")
        ),
    )
    with pytest.raises(ServiceError) as error:
        await generator.generate(PlayerState(), "海港", [])
    assert error.value.status_code == expected
    assert "never-expose-this" not in str(error.value)
    assert "secret-upstream-body" not in str(error.value)


async def test_missing_key_has_actionable_error():
    with pytest.raises(ServiceError, match="DEEPSEEK_API_KEY"):
        await DeepSeekGenerator(Settings(deepseek_api_key="")).generate(PlayerState(), "海港", [])


async def test_empty_output_fails_after_two_attempts():
    generator = DeepSeekGenerator(
        Settings(deepseek_api_key="test-only"),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})
        ),
    )
    with pytest.raises(ServiceError, match="JSON"):
        await generator.generate(PlayerState(), "海港", [])


async def test_deepseek_enforces_total_deadline():
    import asyncio

    async def slow_response(request):
        await asyncio.sleep(0.2)
        return httpx.Response(200, json={})

    generator = DeepSeekGenerator(
        Settings(deepseek_api_key="test-only", deepseek_timeout=0.01),
        transport=httpx.MockTransport(slow_response),
    )
    with pytest.raises(ServiceError, match="超时") as error:
        await generator.generate(PlayerState(), "海港", [])
    assert error.value.status_code == 504


@pytest.mark.parametrize(
    "state",
    [
        PlayerState(hp=0, gold=0, reputation=-100),
        PlayerState(level=100, gold=1_000_000, reputation=100),
    ],
)
async def test_demo_adapts_to_extreme_states(state):
    quest = await DemoGenerator().generate(state, "海港", [])
    assert len(quest.branches) == 3
    assert quest.preconditions.min_level <= state.level
    assert all(state.gold + branch.effects.gold >= 0 for branch in quest.branches)
