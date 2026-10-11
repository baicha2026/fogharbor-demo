from copy import deepcopy

import pytest

from game.charts import dps_frame, hit_frame
from game.engine import act, finish, move, new_game

TASK = {
    "name": "清除雾港威胁",
    "description": "先补给，再战斗。",
    "preconditions": {"min_hp": 0, "min_gold": 0},
    "rewards": {"gold": 80, "hp": 10, "item_name": "潮汐徽章", "item_prompt": "silver badge"},
    "target_monsters": 6,
    "branches": [],
}


def battle():
    game = new_game(TASK)
    game["map"][0][1] = 2
    move(game, 1, 0)
    return game


def test_map_is_deterministic_safe_and_has_exact_counts():
    game = new_game(TASK, seed=17)
    assert game["map"] == new_game(TASK, seed=17)["map"]
    assert game["map"] != new_game(TASK, seed=18)["map"]
    cells = [cell for row in game["map"] for cell in row]
    assert (cells.count(1), cells.count(2), cells.count(3)) == (12, 6, 8)
    assert game["map"][0][0] == 0
    assert game["map"][0][1] == game["map"][1][0] == 3


@pytest.mark.parametrize("target", [(2, 0), (1, 1), (-1, 0), (0, 10), (0, 0)])
def test_illegal_movement_is_atomic(target):
    game = new_game(TASK)
    before = deepcopy(game)
    with pytest.raises(ValueError):
        move(game, *target)
    assert game == before


def test_supplies_cap_resources_and_are_consumed_once():
    game = new_game(TASK, hp_ratio=90)
    game["player"]["mp"] = 35
    move(game, 1, 0)
    assert game["player"]["hp"] == 100 and game["player"]["mp"] == 40
    assert game["map"][0][1] == 0
    game["player"]["hp"] = 90
    move(game, 0, 0)
    move(game, 1, 0)
    assert game["player"]["hp"] == 90
    assert len(game["path"]) == 4


def test_trap_records_actual_damage_and_failure():
    game = new_game(TASK, hp_ratio=5)
    game["map"][0][1] = 1
    move(game, 1, 0)
    assert game["phase"] == "RESULT"
    assert game["player"]["hp"] == 0
    assert game["hit_points"][0]["damage"] == 5
    assert game["result"] == "defeat"
    assert game["map"][0][1] == 0


def test_combat_blocks_movement_and_enforces_cooldowns():
    game = battle()
    assert game["phase"] == "COMBAT"
    with pytest.raises(ValueError):
        move(game, 0, 0)
    game["combat"]["hp"] = 500
    act(game, "burst")
    assert game["combat"]["cooldowns"]["burst"] == 3
    assert game["player"]["mp"] == 28
    before = deepcopy(game)
    with pytest.raises(ValueError):
        act(game, "burst")
    assert game == before
    act(game, "flow")
    assert game["player"]["mp"] == 36
    act(game, "wait")
    assert game["dps_samples"][-1]["vacuum"] is True
    assert game["dps_samples"][-1]["dps"] == 0
    act(game, "flow")
    assert game["combat"]["cooldowns"]["burst"] == 0
    act(game, "burst")
    assert game["dps_samples"][-1]["damage"] == 36


def test_insufficient_mana_is_atomic_and_flow_recovers_mana():
    game = battle()
    game["player"]["mp"] = 0
    before = deepcopy(game)
    with pytest.raises(ValueError):
        act(game, "burst")
    assert game == before
    act(game, "flow")
    assert game["player"]["mp"] == 8


def test_kill_has_no_counterattack_and_dps_excludes_overkill():
    game = battle()
    game["combat"]["hp"] = 5
    hp = game["player"]["hp"]
    act(game, "burst")
    assert game["player"]["hp"] == hp
    assert game["phase"] == "EXPLORING"
    assert game["map"][0][1] == 0
    assert game["kills"] == 1
    assert game["dps_samples"][-1]["damage"] == 5
    assert game["dps_samples"][-1]["dps"] == 2.5
    assert game["dps_samples"][-1]["avg_dps"] == 2.5


def test_victory_rewards_once_and_terminal_state_blocks_actions():
    game = battle()
    game["kills"] = 5
    game["combat"]["hp"] = 5
    act(game, "burst")
    assert game["phase"] == "RESULT" and game["result"] == "victory"
    assert game["player"]["gold"] == 250 + 12 + 80
    assert game["earned_item"] == "潮汐徽章"
    before = deepcopy(game)
    finish(game, "retreat")
    assert game == before
    with pytest.raises(ValueError):
        act(game, "wait")


def test_heatmap_counts_hits_and_keeps_x_y_orientation():
    game = battle()
    game["combat"]["hp"] = 500
    act(game, "flow")
    act(game, "wait")
    frame = hit_frame(game)
    assert frame.loc[0, 1] == 2
    assert frame.loc[1, 0] == 0
    assert frame.to_numpy().sum() == 2
    assert dps_frame(game)["elapsed"].tolist() == [2, 4]


def test_empty_analytics_and_setup_phase():
    game = new_game()
    assert game["phase"] == "SETUP"
    assert hit_frame(game).to_numpy().sum() == 0
    assert dps_frame(game).empty


def test_enemy_kill_ends_game_without_reward():
    game = battle()
    game["player"]["hp"] = 1
    act(game, "wait")
    assert game["phase"] == "RESULT" and game["result"] == "defeat"
    assert not game["reward_paid"] and not game["earned_item"]


def test_dps_time_continues_across_encounters_but_local_average_resets():
    game = battle()
    game["combat"]["hp"] = 5
    act(game, "burst")
    game["map"][0][2] = 2
    move(game, 2, 0)
    assert game["combat"]["cooldowns"] == {"burst": 0, "flow": 0}
    act(game, "flow")
    sample = game["dps_samples"][-1]
    assert sample["elapsed"] == 4 and sample["battle_elapsed"] == 2
    assert sample["battle_id"] == 2 and sample["avg_dps"] == 7


def test_action_limit_also_applies_to_nonfinal_killing_round():
    game = battle()
    game["combat"]["hp"] = 5
    game["dps_samples"] = [{"damage": 0}] * 199
    act(game, "burst")
    assert game["phase"] == "RESULT" and game["result"] == "retreat"
    assert not game["reward_paid"]


def test_move_limit_prevents_unbounded_path():
    game = new_game(TASK)
    game["path"] = [{"x": 0, "y": 0}] * 400
    move(game, 1, 0)
    assert game["phase"] == "RESULT" and game["result"] == "retreat"
