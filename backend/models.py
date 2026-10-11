from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Action = Literal["accept", "refuse", "befriend"]
Mode = Literal["demo", "deepseek"]
ACTION_LABELS = {"accept": "接受", "refuse": "拒绝", "befriend": "交好"}
FACTIONS = ("晨曦议会", "灰烬商会", "北境守卫")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class PlayerState(StrictModel):
    model_config = ConfigDict(frozen=True)
    level: int = Field(default=10, ge=1, le=100)
    gold: int = Field(default=250, ge=0, le=1_000_000)
    hp: int = Field(default=70, ge=0, le=100)
    faction: Literal["晨曦议会", "灰烬商会", "北境守卫"] = "晨曦议会"
    reputation: int = Field(default=15, ge=-100, le=100)


class StateEffects(StrictModel):
    gold: int = Field(ge=-100_000, le=100_000)
    hp: int = Field(ge=-100, le=100)
    reputation: int = Field(ge=-100, le=100)


class Preconditions(StrictModel):
    min_level: int = Field(ge=1, le=100)
    min_gold: int = Field(ge=0, le=1_000_000)
    min_hp: int = Field(ge=0, le=100)
    min_reputation: int = Field(ge=-100, le=100)
    description: str = Field(min_length=1, max_length=300)


class Reward(StrictModel):
    gold: int = Field(ge=0, le=100_000)
    hp: int = Field(ge=0, le=100)
    reputation: int = Field(ge=0, le=100)
    item_name: str = Field(min_length=1, max_length=80)
    item_prompt: str = Field(min_length=1, max_length=800)


class Branch(StrictModel):
    action: Action
    title: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1, max_length=300)
    outcome: str = Field(min_length=1, max_length=300)
    effects: StateEffects


class Quest(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=1200)
    location: str = Field(min_length=1, max_length=60)
    difficulty: Literal["低", "中", "高"]
    preconditions: Preconditions
    rewards: Reward
    branches: list[Branch] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def three_unique_actions(self) -> "Quest":
        if {branch.action for branch in self.branches} != set(ACTION_LABELS):
            raise ValueError("必须包含且仅包含 accept/refuse/befriend 三个唯一分支")
        return self


def validate_for_player(quest: Quest, player: PlayerState) -> None:
    conditions = quest.preconditions
    if any(
        (
            conditions.min_level > player.level,
            conditions.min_gold > player.gold,
            conditions.min_hp > player.hp,
            conditions.min_reputation > player.reputation,
        )
    ):
        raise ValueError("任务前置条件必须满足当前玩家状态")
    for branch in quest.branches:
        if player.gold + branch.effects.gold < 0:
            raise ValueError("每条分支的金币成本都必须支付得起")
        if branch.action == "accept":
            if branch.effects.gold != quest.rewards.gold:
                raise ValueError("接受分支的金币变化必须等于奖励金币")
            if branch.effects.reputation != quest.rewards.reputation:
                raise ValueError("接受分支的声望变化必须等于奖励声望")
            if quest.rewards.hp and branch.effects.hp != quest.rewards.hp:
                raise ValueError("接受分支的恢复量必须等于奖励血量")


def apply_effects(player: PlayerState, effects: StateEffects) -> PlayerState:
    if player.gold + effects.gold < 0:
        raise ValueError("金币不足，无法选择此分支")
    values = player.model_dump()
    values.update(
        gold=min(1_000_000, player.gold + effects.gold),
        hp=max(0, min(100, player.hp + effects.hp)),
        reputation=max(-100, min(100, player.reputation + effects.reputation)),
    )
    return PlayerState.model_validate(values)


class GenerateRequest(StrictModel):
    player_state: PlayerState
    theme: str = Field(
        default="雾港城中，失踪的信使带来了一场新的风暴。", min_length=1, max_length=500
    )
    mode: Mode = "deepseek"


class ChooseRequest(StrictModel):
    node_id: str = Field(min_length=1, max_length=64)
    action: Action


class QuestNode(StrictModel):
    id: str
    parent_id: str | None = None
    parent_action: Action | None = None
    depth: int
    quest: Quest
    player_state: PlayerState
    incoming_outcome: str = ""
    earned_items: list[str] = Field(default_factory=list)


class QuestSession(StrictModel):
    id: str
    root_id: str
    current_id: str
    source: Mode
    theme: str
    nodes: list[QuestNode]
    generation_ms: int


class ImageResult(StrictModel):
    image_base64: str
    mime_type: str
    prompt_id: str
    item_name: str
