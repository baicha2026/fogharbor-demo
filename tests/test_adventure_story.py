"""用真实移动与战斗规则走完主线，检测出口瞬移、封印和跨图持久化。"""

from collections import deque
from copy import deepcopy

import pytest

from adventure import engine
from adventure.content import MAPS
from adventure.telemetry import review_payload
from backend.arena_ai import ArenaAI
from backend.config import Settings
from game.contracts import ReviewRequest


def walk(game, target):
    player = game["player"]
    queue = deque([((player["x"], player["y"]), [])])
    seen = set()
    while queue:
        pos, path = queue.popleft()
        if pos == target:
            for x, y in path:
                engine.move(game, x, y)
            return
        if pos in seen:
            continue
        seen.add(pos)
        for dx, dy in ((0, -1), (-1, 0), (0, 1), (1, 0)):
            x, y = pos[0] + dx, pos[1] + dy
            if not (0 <= x < 10 and 0 <= y < 10):
                continue
            if MAPS[game["map_id"]]["tiles"][y][x] == "#":
                continue
            entity = engine.entity_at(game, x, y)
            if entity and (x, y) != target:
                if entity["kind"] in {"npc", "exit", "enemy", "boss", "fragment"}:
                    continue
            queue.append(((x, y), path + [(x, y)]))
    pytest.fail(f"当前地图没有到{target}的可用路线")


def fight(game):
    rounds = 0
    while game["phase"] == "COMBAT":
        player, combat = game["player"], game["combat"]
        if combat["charged"]:
            action = "guard"
        elif player["hp"] < 55 and game["inventory"]["potion"]:
            action = "potion"
        elif not combat["cooldowns"]["burst"] and player["mp"] >= 12:
            action = "burst"
        elif not combat["cooldowns"]["flow"]:
            action = "flow"
        else:
            action = "guard"
        engine.act(game, action)
        rounds += 1
        assert rounds < 40
    assert game["phase"] == "EXPLORING"


def test_complete_story_with_side_quest_and_real_map_transitions():
    game = engine.new_game()
    walk(game, (2, 2))
    engine.interact(game, "lorn")
    walk(game, (5, 2))
    engine.interact(game, "eve")
    walk(game, (8, 7))
    assert game["map_id"] == "ruins"
    assert (game["player"]["x"], game["player"]["y"]) == (2, 1)
    walk(game, (3, 1))
    for enemy, fragment in [((5, 1), (7, 1)), ((7, 3), (8, 4)), ((4, 5), (2, 7))]:
        walk(game, enemy)
        fight(game)
        walk(game, fragment)
    assert game["quest_stage"] == "boss" and game["inventory"]["fragment"] == 3
    walk(game, (1, 6))
    walk(game, (5, 6))
    removed = game["removed"]["ruins"].copy()
    walk(game, (1, 1))
    walk(game, (5, 2))
    engine.interact(game, "eve")
    assert game["side_quest"] == "complete"
    walk(game, (6, 5))
    engine.interact(game, "fountain")
    assert game["player"]["hp"] == 100 and game["player"]["mp"] == 40
    walk(game, (8, 7))
    assert all(item in game["removed"]["ruins"] for item in removed)
    walk(game, (8, 7))
    fight(game)
    assert game["quest_stage"] == "return" and game["kills"] == 4
    walk(game, (1, 1))
    walk(game, (2, 2))
    engine.interact(game, "lorn")
    assert game["phase"] == "RESULT" and game["result"] == "victory"
    assert game["reward_paid"]
    assert {row["map_id"] for row in game["path"]} == {"harbor", "ruins"}
    ReviewRequest.model_validate(review_payload(game))


def test_fragment_requires_its_guard_and_trap_cannot_be_farmed():
    game = engine.new_game()
    game["map_id"] = "ruins"
    game["quest_stage"] = "fragments"
    game["player"].update(x=6, y=1)
    before = deepcopy(game)
    with pytest.raises(ValueError, match="封印"):
        engine.move(game, 7, 1)
    assert game == before
    game["player"].update(x=3, y=4)
    engine.move(game, 3, 3)
    hp = game["player"]["hp"]
    assert hp == 92 and len(game["hit_points"]) == 1
    engine.move(game, 3, 4)
    engine.move(game, 3, 3)
    assert game["player"]["hp"] == hp and len(game["hit_points"]) == 1


@pytest.mark.asyncio
async def test_long_run_review_is_bounded_without_changing_full_record_or_totals():
    game = engine.new_game()
    game["result"] = "victory"
    game["path"].extend(
        {"map_id": "harbor", "x": i % 8 + 1, "y": 5, "event": "move"} for i in range(900)
    )
    game["battle_log"] = [{"round": i} for i in range(230)]
    game["dps_samples"] = [{"elapsed": i * 2, "vacuum": i % 2 == 0} for i in range(230)]
    game["hit_points"] = [{"map_id": "ruins", "x": 5, "y": 1} for _ in range(420)]
    before = deepcopy(game)
    payload = review_payload(game)
    ReviewRequest.model_validate(payload)
    assert len(payload["path"]) == 401
    assert payload["path"][0] == game["path"][0] and payload["path"][-1] == game["path"][-1]
    assert payload["summary"] == {
        "steps": 900,
        "battle_rounds": 230,
        "hit_count": 420,
        "vacuum_rounds": 115,
        "sampled": True,
    }
    assert game == before
    advice = await ArenaAI(Settings(_env_file=None)).review(payload, "demo")
    assert "420次受击、230个战斗回合、115个技能真空回合" in advice
