from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from runtime_paths import resource_root, user_root

PROJECT_ROOT = resource_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=user_root() / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    deepseek_api_key: SecretStr = SecretStr("")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    deepseek_timeout: float = Field(default=60, gt=0, le=600)
    comfyui_base_url: str = "http://127.0.0.1:8188"
    comfyui_workflow: Path = Path("workflows/reward_api.json")
    comfyui_checkpoint: str = "v1-5-pruned-emaonly.safetensors"
    comfyui_timeout: float = Field(default=120, gt=0, le=1800)
    comfyui_poll_interval: float = Field(default=1, gt=0, le=10)
    max_depth: int = Field(default=12, ge=1, le=30)
    max_nodes: int = Field(default=80, ge=2, le=500)
    max_sessions: int = Field(default=100, ge=1, le=1000)
    session_ttl_seconds: int = Field(default=7200, ge=1)

    @field_validator("deepseek_base_url", "comfyui_base_url")
    @classmethod
    def http_url(cls, value: str) -> str:
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("API 地址必须是 http(s) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("API 地址不应包含认证信息、查询参数或片段")
        return value.rstrip("/")

    @property
    def workflow_path(self) -> Path:
        path = self.comfyui_workflow
        if path.is_absolute():
            return path
        custom = user_root() / path
        return custom if custom.is_file() else PROJECT_ROOT / path
