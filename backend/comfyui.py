import asyncio
import base64
import json
import secrets
from typing import Any
from uuid import uuid4

import httpx

from backend.config import Settings
from backend.errors import ServiceError
from backend.models import ImageResult, Reward

MAX_IMAGE_BYTES = 20 * 1024 * 1024


def inject_workflow(value: Any, prompt: str, checkpoint: str) -> Any:
    """Return a fresh workflow; the configured template is never modified on disk."""
    if isinstance(value, str):
        return value.replace("{{checkpoint}}", checkpoint).replace("{{prompt}}", prompt)
    if isinstance(value, list):
        return [inject_workflow(item, prompt, checkpoint) for item in value]
    if isinstance(value, dict):
        return {
            key: secrets.randbelow(2**48)
            if key in {"seed", "noise_seed"}
            else inject_workflow(item, prompt, checkpoint)
            for key, item in value.items()
        }
    return value


class ComfyUIClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    def _workflow(self, reward: Reward) -> dict:
        try:
            template = json.loads(self.settings.workflow_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ServiceError(
                "无法读取 ComfyUI 工作流，请检查 COMFYUI_WORKFLOW 的 API 格式 JSON。", 503
            ) from None
        if not isinstance(template, dict) or "nodes" in template or not template:
            raise ServiceError("请从 ComfyUI 导出 API 格式工作流，不要使用画布 JSON。", 503)
        if "{{prompt}}" not in json.dumps(template):
            raise ServiceError("ComfyUI 工作流需在正向提示词中包含 {{prompt}} 占位符。", 503)
        if any(
            not isinstance(node, dict) or "class_type" not in node for node in template.values()
        ):
            raise ServiceError("ComfyUI 工作流节点格式无效，请重新导出 API 格式。", 503)
        prompt = (
            f"{reward.item_name}. {reward.item_prompt}, detailed game item concept art, no text"
        )
        return inject_workflow(template, prompt, self.settings.comfyui_checkpoint)

    @staticmethod
    def _json(response: httpx.Response, stage: str) -> dict:
        if not response.is_success:
            raise ServiceError(f"ComfyUI {stage}失败，请检查工作流、模型文件及 ComfyUI 控制台。")
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("object required")
            return data
        except ValueError:
            raise ServiceError("ComfyUI 返回了无效数据，请确认服务地址。") from None

    async def generate(self, reward: Reward) -> ImageResult:
        workflow = await asyncio.to_thread(self._workflow, reward)
        try:
            async with asyncio.timeout(self.settings.comfyui_timeout):
                async with httpx.AsyncClient(
                    base_url=self.settings.comfyui_base_url + "/",
                    timeout=httpx.Timeout(20, connect=5),
                    transport=self.transport,
                ) as client:
                    submitted = self._json(
                        await client.post(
                            "prompt",
                            json={
                                "prompt": workflow,
                                "client_id": uuid4().hex,
                            },
                        ),
                        "提交工作流",
                    )
                    prompt_id = submitted.get("prompt_id")
                    if not isinstance(prompt_id, str) or not prompt_id or len(prompt_id) > 100:
                        raise ServiceError("ComfyUI 未返回任务 ID，请检查工作流和模型。")
                    if submitted.get("node_errors"):
                        raise ServiceError("ComfyUI 工作流节点校验失败，请检查本地模型及节点。")
                    while True:
                        history = self._json(await client.get(f"history/{prompt_id}"), "查询任务")
                        result = history.get(prompt_id, {})
                        status = result.get("status", {})
                        if status.get("status_str") == "error":
                            raise ServiceError(
                                "ComfyUI 工作流执行失败，请检查模型和节点，详见本地控制台。"
                            )
                        for output in result.get("outputs", {}).values():
                            for info in output.get("images", []):
                                if info.get("type", "output") != "output":
                                    continue
                                return await self._download(
                                    client, info, prompt_id, reward.item_name
                                )
                        if status.get("completed"):
                            raise ServiceError(
                                "ComfyUI 工作流已完成但没有图片，请添加 SaveImage 输出节点。"
                            )
                        await asyncio.sleep(self.settings.comfyui_poll_interval)
        except (TimeoutError, httpx.TimeoutException):
            raise ServiceError(
                "ComfyUI 生成超时；任务可能仍在本地队列，可在 ComfyUI 查看。", 504
            ) from None
        except httpx.RequestError:
            raise ServiceError(
                "无法连接本地 ComfyUI，请启动服务并检查 COMFYUI_BASE_URL。", 503
            ) from None
        except (KeyError, TypeError, AttributeError):
            raise ServiceError("ComfyUI 返回的任务结构无效，请检查 API 工作流。") from None

    async def _download(
        self, client: httpx.AsyncClient, info: dict, prompt_id: str, item_name: str
    ) -> ImageResult:
        async with client.stream(
            "GET",
            "view",
            params={
                "filename": info["filename"],
                "subfolder": info.get("subfolder", ""),
                "type": "output",
            },
        ) as response:
            if not response.is_success:
                raise ServiceError("ComfyUI 图片下载失败，请检查输出目录。")
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > MAX_IMAGE_BYTES:
                    raise ServiceError("概念图超过 20MB，请降低输出分辨率。")
            data = bytes(content)
            if data.startswith(b"\x89PNG\r\n\x1a\n"):
                mime = "image/png"
            elif data.startswith(b"\xff\xd8\xff"):
                mime = "image/jpeg"
            elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
                mime = "image/webp"
            else:
                raise ServiceError("ComfyUI 返回的文件不是支持的 PNG、JPEG 或 WebP 图片。")
            return ImageResult(
                image_base64=base64.b64encode(data).decode("ascii"),
                mime_type=mime,
                prompt_id=prompt_id,
                item_name=item_name,
            )
