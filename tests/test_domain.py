import copy

import pytest
from pydantic import ValidationError

from backend.models import PlayerState, Quest, StateEffects, apply_effects, validate_for_player


def test_effects_clamp_hp_reputation_without_mutating_snapshot():
    player = PlayerState(level=10, gold=100, hp=5, reputation=95)
    result = apply_effects(player, StateEffects(gold=-25, hp=-20, reputation=20))
    assert (result.gold, result.hp, result.reputation) == (75, 0, 100)
    assert (player.gold, player.hp, player.reputation) == (100, 5, 95)


@pytest.mark.parametrize(
    "field,value", [("level", 0), ("gold", -1), ("hp", 101), ("reputation", -101), ("level", "10")]
)
def test_player_rejects_out_of_bounds_or_coerced_values(field, value):
    with pytest.raises(ValidationError):
        PlayerState(**{field: value})


def test_duplicate_or_missing_actions_rejected(quest_data):
    quest_data["branches"][2]["action"] = "accept"
    with pytest.raises(ValidationError):
        Quest.model_validate(quest_data)


def test_unreachable_precondition_rejected(quest_data):
    quest_data["preconditions"]["min_level"] = 50
    quest = Quest.model_validate(quest_data)
    with pytest.raises(ValueError, match="前置条件"):
        validate_for_player(quest, PlayerState(level=5))


def test_unaffordable_branch_rejected(quest_data):
    quest_data["branches"][2]["effects"]["gold"] = -500
    with pytest.raises(ValueError, match="金币"):
        validate_for_player(Quest.model_validate(quest_data), PlayerState(gold=100))


def test_accept_reward_must_match_panel(quest_data):
    quest_data["branches"][0]["effects"]["gold"] = 999
    with pytest.raises(ValueError, match="奖励"):
        validate_for_player(Quest.model_validate(quest_data), PlayerState())


def test_valid_quest_and_snapshot_can_be_serialized(quest_data):
    original = copy.deepcopy(quest_data)
    quest = Quest.model_validate(quest_data)
    validate_for_player(quest, PlayerState())
    assert quest.model_dump() == original
