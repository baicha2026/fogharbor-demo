import asyncio
import os
from typing import Any

import httpx
from dotenv import dotenv_values

from runtime_paths import user_root

_configuration = dotenv_values(user_root() / ".env")
BACKEND_URL = os.getenv(
    "BACKEND_URL", _configuration.get("BACKEND_URL") or "http://127.0.0.1:8000"
).rstrip("/")
del _configuration


class APIError(Exception):
    """A message suitable for rendering without exposing upstream internals."""


async def request(
    method: str, path: str, payload: dict | None = None, *, request_timeout: float = 190
) -> Any:
    try:
        async with asyncio.timeout(request_timeout):
            async with httpx.AsyncClient(
                base_url=BACKEND_URL,
                timeout=httpx.Timeout(request_timeout, connect=5),
            ) as client:
                response = await client.request(method, path, json=payload)
        if not response.is_success:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = None
            if isinstance(detail, str):
                raise APIError(detail)
            if response.status_code == 422:
                raise APIError("请求参数无效，请检查玩家状态与世界设定。")
            raise APIError(f"后端请求失败（HTTP {response.status_code}），请检查服务日志。")
        return response.json()
    except (TimeoutError, httpx.TimeoutException):
        raise APIError("等待后端超时，请稍后重试；分支结算可安全重试。") from None
    except httpx.RequestError:
        raise APIError("无法连接 FastAPI，请运行 python run.py，或检查 BACKEND_URL。") from None
    except ValueError:
        raise APIError(
            "后端返回了无效数据，请确认 BACKEND_URL 指向本项目的 FastAPI 服务。"
        ) from None
