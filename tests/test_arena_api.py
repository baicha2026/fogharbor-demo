import asyncio
import base64
import json
from copy import deepcopy

import httpx
import pytest

from backend.arena_ai import ArenaAI
from backend.config import Settings
from backend.errors import ServiceError
from backend.main import create_app
from backend.models import ImageResult
from backend.poster import generate_achievement_poster
from game.contracts import ArenaReward


def generator(respond):
    return ArenaAI(Settings(deepseek_api_key="test-only"), httpx.MockTransport(respond))


def answer(content):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


async def test_task_repairs_json_and_unmet_conditions_once():
    calls = []
    valid = ArenaAI._demo_task(10, 0)
    invalid = deepcopy(valid)
    invalid["preconditions"]["min_hp"] = 80

    def respond(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert payload["response_format"] == {"type": "json_object"}
        assert request.headers["authorization"] == "Bearer test-only"
        return answer(json.dumps(invalid if len(calls) == 1 else valid))

    task = await generator(respond).task(10, 0, "deepseek")
    assert task["preconditions"]["min_hp"] == 0
    assert len(calls) == 2
    assert '"hp_ratio": 10' in calls[0]["messages"][1]["content"]


async def test_wrong_target_and_missing_branch_fail_without_fallback():
    invalid = ArenaAI._demo_task(100, 250)
    invalid["target_monsters"] = 1
    invalid["branches"].pop()
    with pytest.raises(ServiceError, match="JSON"):
        await generator(lambda _: answer(json.dumps(invalid))).task(100, 250, "deepseek")


async def test_review_retries_oversized_text_and_passes_telemetry():
    calls = []
    payload = {
        "battle_log": [{"damage": 36}],
        "path": [{"x": 1, "y": 0}],
        "hit_points": [{"x": 1, "y": 0}],
        "result": "victory",
    }

    def respond(request):
        calls.append(json.loads(request.content))
        return answer(
            json.dumps({"advice": "字" * 201 if len(calls) == 1 else "建议提高补给覆盖。"})
        )

    result = await generator(respond).review(payload, "deepseek")
    assert result == "建议提高补给覆盖。"
    assert json.loads(calls[0]["messages"][1]["content"]) == payload
    assert len(calls) == 2


@pytest.mark.parametrize("status,expected", [(401, 502), (429, 429), (500, 502)])
async def test_errors_do_not_leak_secrets(status, expected):
    with pytest.raises(ServiceError) as exc:
        await generator(lambda _: httpx.Response(status, text="SECRET")).task(100, 0, "deepseek")
    assert exc.value.status_code == expected
    assert "SECRET" not in str(exc.value)


async def test_deadline_and_missing_key():
    async def slow(request):
        await asyncio.sleep(0.1)
        return answer("{}")

    ai = ArenaAI(
        Settings(deepseek_api_key="test-only", deepseek_timeout=0.01), httpx.MockTransport(slow)
    )
    with pytest.raises(ServiceError, match="超时"):
        await ai.task(100, 0, "deepseek")
    with pytest.raises(ServiceError, match="DEEPSEEK_API_KEY"):
        await ArenaAI(Settings(deepseek_api_key="")).task(100, 0, "deepseek")


async def test_arena_endpoints_validate_modes_and_return_demo():
    app = create_app(Settings(deepseek_api_key=""))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        bad = await client.post(
            "/api/arena/task", json={"hp_ratio": 101, "gold": 0, "mode": "demo"}
        )
        assert bad.status_code == 422
        bad_mode = await client.post(
            "/api/arena/task", json={"hp_ratio": 100, "gold": 0, "mode": "typo"}
        )
        assert bad_mode.status_code == 422
        result = await client.post(
            "/api/arena/task", json={"hp_ratio": 10, "gold": 0, "mode": "demo"}
        )
        assert result.status_code == 200
        assert "补给" in result.json()["description"]
        review = await client.post("/api/arena/review", json={"mode": "demo", "result": "retreat"})
        assert review.status_code == 200 and len(review.json()["review"]) <= 200


async def test_poster_fallback_is_png_and_real_images_remain_real():
    class Client:
        fail = True

        async def generate(self, reward):
            if self.fail:
                raise ServiceError("ComfyUI 未连接", 503)
            return ImageResult(
                image_base64="cG5n",
                mime_type="image/png",
                prompt_id="test",
                item_name=reward.item_name,
            )

    reward = ArenaReward.model_validate(ArenaAI._demo_task(100, 0)["rewards"])
    client = Client()
    result = await generate_achievement_poster(client, reward)
    assert result.source == "placeholder" and "未连接" in result.notice
    assert base64.b64decode(result.image_base64).startswith(b"\x89PNG\r\n\x1a\n")
    client.fail = False
    result = await generate_achievement_poster(client, reward)
    assert result.source == "comfyui" and result.image_base64 == "cG5n"
