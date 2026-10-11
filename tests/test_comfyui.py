import base64
import json

import httpx
import pytest

from backend.comfyui import ComfyUIClient
from backend.config import Settings
from backend.errors import ServiceError
from backend.models import Reward


async def test_workflow_submit_poll_and_download(quest_data):
    requests = []
    image_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
    )

    async def respond(request):
        requests.append(request)
        path = request.url.path
        if path == "/prompt":
            payload = json.loads(request.content)
            positive = payload["prompt"]["6"]["inputs"]["text"]
            assert quest_data["rewards"]["item_name"] in positive
            assert "{{prompt}}" not in positive
            return httpx.Response(200, json={"prompt_id": "job-1"})
        if path == "/history/job-1":
            return httpx.Response(
                200,
                json={
                    "job-1": {
                        "outputs": {
                            "9": {
                                "images": [
                                    {"filename": "reward.png", "subfolder": "", "type": "output"}
                                ]
                            }
                        },
                        "status": {"completed": True},
                    }
                },
            )
        if path == "/view":
            assert request.url.params["filename"] == "reward.png"
            return httpx.Response(200, content=image_bytes, headers={"content-type": "image/png"})
        raise AssertionError(f"Unexpected path {path}")

    service = ComfyUIClient(Settings(), transport=httpx.MockTransport(respond))
    result = await service.generate(Reward.model_validate(quest_data["rewards"]))
    assert base64.b64decode(result.image_base64) == image_bytes
    assert result.mime_type == "image/png"
    assert len(requests) == 3


async def test_comfyui_timeout_is_actionable(quest_data):
    def respond(request):
        return httpx.Response(
            200, json={"prompt_id": "slow"} if request.url.path == "/prompt" else {}
        )

    service = ComfyUIClient(
        Settings(comfyui_timeout=0.01, comfyui_poll_interval=0.01),
        transport=httpx.MockTransport(respond),
    )
    with pytest.raises(ServiceError, match="超时"):
        await service.generate(Reward.model_validate(quest_data["rewards"]))


async def test_comfyui_execution_error_stops_polling(quest_data):
    def respond(request):
        body = (
            {"prompt_id": "bad"}
            if request.url.path == "/prompt"
            else {
                "bad": {"status": {"status_str": "error", "messages": [["error", "private data"]]}}
            }
        )
        return httpx.Response(200, json=body)

    service = ComfyUIClient(Settings(), transport=httpx.MockTransport(respond))
    with pytest.raises(ServiceError, match="工作流") as error:
        await service.generate(Reward.model_validate(quest_data["rewards"]))
    assert "private data" not in str(error.value)
