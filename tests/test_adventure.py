from copy import deepcopy

import pytest

from adventure.content import MAPS
from adventure.engine import act, buy_potion, interact, move, new_game, use_potion


def at(game, map_id, x, y):
    game["map_id"] = map_id
    game["player"]["x"], game["player"]["y"] = x, y


def accepted():
    game = new_game()
    at(game, "harbor", 2, 2)
    interact(game, "lorn")
    return game


def test_maps_are_ten_square_and_required_objectives_are_reachable():
    for world in MAPS.values():
        assert len(world["tiles"]) == 10 and all(len(row) == 10 for row in world["tiles"])
        seen = {tuple(world["spawn"])}
        pending = list(seen)
        while pending:
            x, y = pending.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                p = x + dx, y + dy
                if 0 <= p[0] < 10 and 0 <= p[1] < 10:
                    if world["tiles"][p[1]][p[0]] != "#" and p not in seen:
                        seen.add(p)
                        pending.append(p)
        for entity in world["entities"]:
            assert (entity["x"], entity["y"]) in seen


def test_npc_grants_initial_quest_and_potions_once():
    game = accepted()
    assert game["quest_stage"] == "fragments"
    assert game["inventory"]["potion"] == 2
    interact(game, "lorn")
    assert game["inventory"]["potion"] == 2
    before = deepcopy(game)
    at(game, "harbor", 8, 8)
    with pytest.raises(ValueError):
        interact(game, "lorn")
    assert game["quest_stage"] == before["quest_stage"]


def test_wall_diagonal_and_remote_moves_do_not_mutate_state():
    game = accepted()
    at(game, "harbor", 1, 1)
    for p in [(0, 1), (2, 2), (7, 7)]:
        before = deepcopy(game)
        with pytest.raises(ValueError):
            move(game, *p)
        assert game == before


def test_exit_is_locked_until_quest_and_maps_keep_collected_entities():
    game = new_game()
    at(game, "harbor", 7, 7)
    with pytest.raises(ValueError):
        move(game, 8, 7)
    game = accepted()
    at(game, "harbor", 7, 7)
    move(game, 8, 7)
    assert game["map_id"] == "ruins" and game["player"]["x"] == 2
    move(game, 3, 1)
    gold = game["player"]["gold"]
    assert "chest_start" in game["removed"]["ruins"]
    move(game, 2, 1)
    move(game, 3, 1)
    assert game["player"]["gold"] == gold


def test_shop_checks_distance_money_and_potion_caps():
    game = accepted()
    with pytest.raises(ValueError):
        buy_potion(game)
    at(game, "harbor", 5, 2)
    game["player"]["gold"] = 20
    buy_potion(game)
    assert game["player"]["gold"] == 0 and game["inventory"]["potion"] == 3
    with pytest.raises(ValueError):
        buy_potion(game)
    game["player"]["hp"] = 95
    use_potion(game)
    assert game["player"]["hp"] == 100 and game["inventory"]["potion"] == 2


def test_herb_delivery_once_does_not_gate_main_story():
    game = accepted()
    at(game, "harbor", 5, 2)
    interact(game, "eve")
    assert game["side_quest"] == "collect"
    game["inventory"]["herb"] = 1
    interact(game, "eve")
    assert game["side_quest"] == "complete" and game["inventory"]["herb"] == 0
    count = game["inventory"]["potion"]
    interact(game, "eve")
    assert game["inventory"]["potion"] == count


def test_guard_deflects_telegraphed_boss_and_logs_real_damage():
    game = accepted()
    game["inventory"]["fragment"] = 3
    game["quest_stage"] = "boss"
    at(game, "ruins", 7, 7)
    move(game, 8, 7)
    assert game["phase"] == "COMBAT"
    act(game, "guard")
    assert game["combat"]["charged"]
    hp = game["player"]["hp"]
    act(game, "guard")
    assert hp - game["player"]["hp"] == 6
    assert game["hit_points"][-1]["damage"] == 6
    assert game["battle_log"][-1]["counter"] == 6
    assert game["dps_samples"][-1]["dps"] == 0


def test_skills_validate_before_cooldowns_and_kill_without_counter():
    game = accepted()
    at(game, "ruins", 4, 1)
    move(game, 5, 1)
    assert game["combat"]["entity_id"] == "rat"
    act(game, "burst")
    before = deepcopy(game)
    with pytest.raises(ValueError):
        act(game, "burst")
    assert game == before
    hp = game["player"]["hp"]
    act(game, "flow")
    assert game["phase"] == "EXPLORING" and game["player"]["hp"] == hp
    assert "rat" in game["removed"]["ruins"]


def test_boss_unlock_return_and_final_rewards_only_once():
    game = accepted()
    at(game, "ruins", 7, 7)
    before = deepcopy(game)
    with pytest.raises(ValueError):
        move(game, 8, 7)
    assert game == before
    game["inventory"]["fragment"] = 3
    game["quest_stage"] = "boss"
    move(game, 8, 7)
    game["combat"]["hp"] = 1
    act(game, "burst")
    assert game["quest_stage"] == "return" and game["boss_defeated"]
    at(game, "harbor", 2, 2)
    interact(game, "lorn")
    assert game["result"] == "victory" and game["quest_stage"] == "complete"
    before = deepcopy(game)
    with pytest.raises(ValueError):
        interact(game, "lorn")
    assert game == before


def test_empty_potion_fails_atomically_and_death_is_terminal():
    game = accepted()
    game["inventory"]["potion"] = 0
    before = deepcopy(game)
    with pytest.raises(ValueError):
        use_potion(game)
    assert game == before
    at(game, "ruins", 4, 1)
    move(game, 5, 1)
    game["player"]["hp"] = 1
    act(game, "wait")
    assert game["phase"] == "RESULT" and game["result"] == "defeat"
    with pytest.raises(ValueError):
        move(game, 4, 1)
