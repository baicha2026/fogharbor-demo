"""AI 只填充受约束的任务合同，不修改地图和战斗公式。"""

from typing import Literal

from pydantic import Field, model_validator

from backend.models import Mode, StrictModel


class ArenaConditions(StrictModel):
    min_hp: int = Field(ge=0, le=100)
    min_gold: int = Field(ge=0, le=1_000_000)


class ArenaReward(StrictModel):
    gold: int = Field(ge=0, le=1000)
    hp: int = Field(ge=0, le=30)
    item_name: str = Field(min_length=1, max_length=80)
    item_prompt: str = Field(min_length=1, max_length=800)


class Tactic(StrictModel):
    action: Literal["accept", "refuse", "befriend"]
    title: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1, max_length=200)


class ArenaTask(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    preconditions: ArenaConditions
    rewards: ArenaReward
    target_monsters: Literal[6] = 6
    branches: list[Tactic] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def actions_are_unique(self) -> "ArenaTask":
        if {item.action for item in self.branches} != {"accept", "refuse", "befriend"}:
            raise ValueError("战术建议必须包含 accept/refuse/befriend 三种不同选项")
        return self


class TaskRequest(StrictModel):
    hp_ratio: int = Field(ge=0, le=100)
    gold: int = Field(ge=0, le=1_000_000)
    mode: Mode = "deepseek"


class ReviewSummary(StrictModel):
    steps: int = Field(ge=0)
    battle_rounds: int = Field(ge=0)
    hit_count: int = Field(ge=0)
    vacuum_rounds: int = Field(ge=0)
    sampled: bool


class ReviewRequest(StrictModel):
    battle_log: list[dict] = Field(default_factory=list, max_length=200)
    path: list[dict] = Field(default_factory=list, max_length=401)
    hit_points: list[dict] = Field(default_factory=list, max_length=400)
    dps_samples: list[dict] = Field(default_factory=list, max_length=200)
    result: Literal["victory", "defeat", "retreat"]
    mode: Mode = "deepseek"
    summary: ReviewSummary | None = None


class ReviewResult(StrictModel):
    advice: str = Field(min_length=1, max_length=200)


class PosterResult(StrictModel):
    image_base64: str
    mime_type: str
    item_name: str
    source: Literal["comfyui", "placeholder"]
    notice: str = ""
