from __future__ import annotations

import json

import pytest

from adventure import campaign


def _move_to(game: dict, target: tuple[int, int]) -> None:
    """把测试角色直接放到出口旁，验证出口校验不会半提交。"""
    game["player"].update(x=target[0] - 1, y=target[1])


def test_campaign_has_eleven_levels_and_unique_books() -> None:
    assert len(campaign.LEVELS) == 11
    assert len(campaign.SKILL_BOOKS) == 11
    books = [definition["book"] for definition in campaign.LEVELS.values()]
    assert len(set(books)) == 11
    assert set(books) == set(campaign.SKILL_BOOKS)
    levels = (campaign.build_level(key) for key in campaign.LEVELS)
    assert all(len(level["tiles"]) == 10 for level in levels)


def test_blocked_exit_does_not_change_player_position() -> None:
    game = campaign.new_game()
    exit_cell = game["level"]["exit"]
    _move_to(game, (exit_cell["x"], exit_cell["y"]))
    before = dict(game["player"])
    with pytest.raises(ValueError, match="出口被敌人封锁"):
        campaign.move(game, exit_cell["x"], exit_cell["y"])
    assert game["player"] == before
    assert game["phase"] == "EXPLORING"


def test_skill_cooldown_and_four_slot_limit() -> None:
    game = campaign.new_game()
    game["learned_books"].append("ember_arc")
    game["player"].update(x=2, y=2)
    game["level"]["enemies"][0].update(x=3, y=2)
    campaign.move(game, 3, 2)
    assert game["phase"] == "COMBAT"
    campaign.act(game, "basic")
    assert game["combat"]["cooldowns"]["basic"] == 0
    campaign.equip_skill(game, "ember_arc", 0)
    assert len(game["equipped"]) == 4
    campaign.act(game, "ember_arc")
    with pytest.raises(ValueError, match="技能还在冷却"):
        campaign.act(game, "ember_arc")
    with pytest.raises(ValueError, match="主动技能栏只有4个"):
        campaign.equip_skill(game, "ember_arc", 4)


def test_route_choice_leads_to_route_specific_ending() -> None:
    game = campaign.new_game()
    game["phase"] = "ROUTE_CHOICE"
    campaign.choose_route(game, "tide")
    assert game["route"] == "tide"
    assert game["level_id"] == campaign.ROUTES["tide"]["levels"][0]
    assert game["phase"] == "EXPLORING"


def test_save_and_corrupted_save_backup(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(campaign, "user_root", lambda: tmp_path)
    game = campaign.new_game()
    path = campaign.save_game(game, 1)
    assert path.is_file()
    assert campaign.load_game(1)["version"] == campaign.SAVE_VERSION
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError, match="存档损坏"):
        campaign.load_game(1)
    assert path.with_suffix(".broken").is_file()


def test_achievement_route_flags_are_updated_before_all_routes() -> None:
    game = campaign.new_game()
    game["result"] = "keeper"
    campaign.update_achievements(game)
    game["result"] = "tide"
    campaign.update_achievements(game)
    game["result"] = "oath"
    campaign.update_achievements(game)
    assert {"route_keeper", "route_tide", "route_oath", "all_routes"}.issubset(game["achievements"])


def test_json_save_is_valid() -> None:
    payload = campaign.new_game()
    json.dumps(payload, ensure_ascii=False)
