# ruff: noqa: E501

"""大型 2D 远征模式的规则层。

这套规则与原有的《雾港守灯人》短篇剧情隔离，玩家可以在同一个 Streamlit
项目中选择它。所有地图、路线、技能和结局都由数据驱动，方便策划继续扩展；
战斗仍然是短回合，但每次技能会写入可视化的 effect 事件，前端可以播放短时
演出而不把伤害逻辑交给 UI。
"""

from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from runtime_paths import user_root

WIDTH = HEIGHT = 10
MAX_HP = 120
MAX_MP = 60
SAVE_VERSION = 1

ROUTES: dict[str, dict[str, Any]] = {
    "keeper": {
        "name": "守灯路线",
        "color": "#e9b95f",
        "ending": "守住港口并点亮灯塔",
        "levels": ["salt_marsh", "ash_docks", "lighthouse_sanctum"],
    },
    "tide": {
        "name": "逐潮路线",
        "color": "#63c6cf",
        "ending": "封印迷雾源头",
        "levels": ["deep_mine", "tide_cavern", "abyssal_rift"],
    },
    "oath": {
        "name": "破誓路线",
        "color": "#c98ade",
        "ending": "成为雾中守望者",
        "levels": ["echo_belltower", "sunken_archive", "deep_throne"],
    },
}

# 11 本技能书：共享 2 本、每条路线 3 本、隐藏 2 本。伤害数值刻意保持在
# 18–42 的短回合范围内，避免一键秒杀，也便于在 DPS 图中观察真空期。
SKILL_BOOKS: dict[str, dict[str, Any]] = {
    "ember_arc": {
        "name": "余烬弧斩",
        "damage": 28,
        "cost": 8,
        "cooldown": 2,
        "kind": "aoe",
        "color": "#ed885c",
        "route": "keeper",
        "description": "扇形灼烧，命中后留下1层灼烧。",
    },
    "bulwark": {
        "name": "灯盾反击",
        "damage": 20,
        "cost": 10,
        "cooldown": 3,
        "kind": "shield",
        "color": "#e9b95f",
        "route": "keeper",
        "description": "获得护盾并在本回合降低反击伤害。",
    },
    "tidal_step": {
        "name": "潮汐步",
        "damage": 24,
        "cost": 6,
        "cooldown": 2,
        "kind": "dash",
        "color": "#63c6cf",
        "route": "tide",
        "description": "位移斩击，恢复少量MP。",
    },
    "undertow": {
        "name": "暗流牵引",
        "damage": 34,
        "cost": 14,
        "cooldown": 4,
        "kind": "pull",
        "color": "#4f9fb4",
        "route": "tide",
        "description": "高伤并施加迟缓，敌人下回合反击减半。",
    },
    "mist_seal": {
        "name": "迷雾封印",
        "damage": 22,
        "cost": 12,
        "cooldown": 3,
        "kind": "cleanse",
        "color": "#8ce0db",
        "route": "tide",
        "description": "伤害并净化自身负面状态。",
    },
    "echo_blade": {
        "name": "回声连斩",
        "damage": 32,
        "cost": 10,
        "cooldown": 3,
        "kind": "combo",
        "color": "#c98ade",
        "route": "oath",
        "description": "连续两段伤害，第二段会触发暴击音效。",
    },
    "bell_fear": {
        "name": "钟声震慑",
        "damage": 18,
        "cost": 7,
        "cooldown": 2,
        "kind": "fear",
        "color": "#a46ac2",
        "route": "oath",
        "description": "低伤但令敌人恐惧，下一次反击失效。",
    },
    "oath_blood": {
        "name": "破誓献血",
        "damage": 42,
        "cost": 18,
        "cooldown": 5,
        "kind": "sacrifice",
        "color": "#e76977",
        "route": "oath",
        "description": "消耗8HP换取爆发伤害。",
    },
    "mirror_decoy": {
        "name": "镜像诱饵",
        "damage": 16,
        "cost": 9,
        "cooldown": 3,
        "kind": "decoy",
        "color": "#bd9fe0",
        "route": "hidden",
        "description": "制造诱饵，敌方反击伤害减半。",
    },
    "harbor_song": {
        "name": "港湾颂歌",
        "damage": 20,
        "cost": 5,
        "cooldown": 1,
        "kind": "heal",
        "color": "#f0d38b",
        "route": "hidden",
        "description": "造成伤害并恢复12HP。",
    },
    "starfall": {
        "name": "星屑坠落",
        "damage": 38,
        "cost": 16,
        "cooldown": 4,
        "kind": "burst",
        "color": "#f5f0c2",
        "route": "hidden",
        "description": "大范围终结技，视觉演出持续更久。",
    },
}

INITIAL_SKILLS = ["basic", "burst", "echo", "guard"]
SKILL_NAMES = {
    "basic": "普攻 · 灯刃",
    "burst": "破阵重击",
    "echo": "潮汐回响",
    "guard": "防御姿态",
}

LEVELS: dict[str, dict[str, Any]] = {
    "harbor": {
        "name": "避风站",
        "route": "shared",
        "objective": "清理码头上的迷雾兽，熟悉移动与技能。",
        "next": "lighthouse_ruins",
        "book": "ember_arc",
        "palette": "harbor",
    },
    "lighthouse_ruins": {
        "name": "灯塔遗迹",
        "route": "shared",
        "objective": "寻找路线线索，击败遗迹守卫后选择命运。",
        "next": "route_gate",
        "book": "bulwark",
        "palette": "ruins",
    },
    "salt_marsh": {
        "name": "盐雾滩",
        "route": "keeper",
        "objective": "护送港口工人穿过盐雾滩。",
        "next": "ash_docks",
        "book": "harbor_song",
        "palette": "keeper",
    },
    "ash_docks": {
        "name": "灰烬码头",
        "route": "keeper",
        "objective": "保护燃料车，击破灼烧区域的护甲敌人。",
        "next": "lighthouse_sanctum",
        "book": "mirror_decoy",
        "palette": "keeper",
    },
    "lighthouse_sanctum": {
        "name": "灯塔圣坛",
        "route": "keeper",
        "objective": "击败灰烬领主，点亮灯塔。",
        "next": None,
        "book": "starfall",
        "palette": "keeper",
    },
    "deep_mine": {
        "name": "沉矿井",
        "route": "tide",
        "objective": "在窄路伏击中找到破甲窗口。",
        "next": "tide_cavern",
        "book": "tidal_step",
        "palette": "tide",
    },
    "tide_cavern": {
        "name": "潮汐洞窟",
        "route": "tide",
        "objective": "管理水位与迟缓地带，抵达洞窟深处。",
        "next": "abyssal_rift",
        "book": "undertow",
        "palette": "tide",
    },
    "abyssal_rift": {
        "name": "深海裂隙",
        "route": "tide",
        "objective": "击败潮汐核心，封印迷雾源头。",
        "next": None,
        "book": "mist_seal",
        "palette": "tide",
    },
    "echo_belltower": {
        "name": "回声钟楼",
        "route": "oath",
        "objective": "以生命换强化，击破精英组合。",
        "next": "sunken_archive",
        "book": "echo_blade",
        "palette": "oath",
    },
    "sunken_archive": {
        "name": "沉没档案馆",
        "route": "oath",
        "objective": "寻找隐藏房间，收集高价值技能书。",
        "next": "deep_throne",
        "book": "bell_fear",
        "palette": "oath",
    },
    "deep_throne": {
        "name": "深海王座",
        "route": "oath",
        "objective": "击败王座守卫，成为新的雾中守望者。",
        "next": None,
        "book": "oath_blood",
        "palette": "oath",
    },
}

HIDDEN_BOOKS = ["mirror_decoy", "starfall"]


def _runtime_dir() -> Path:
    path = user_root() / ".runtime" / "campaign"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _grid(level_id: str) -> list[str]:
    """为每关生成固定 10x10 网格；内部障碍不依赖随机数，便于复盘和测试。"""
    seed = sum(ord(c) for c in level_id)
    rows = [["." for _ in range(WIDTH)] for _ in range(HEIGHT)]
    for i in range(WIDTH):
        rows[0][i] = rows[-1][i] = "#"
        rows[i][0] = rows[i][-1] = "#"
    for i in range(2, 8):
        if (seed + i) % 3 == 0:
            rows[4][i] = "#"
        if (seed + i) % 4 == 0:
            rows[6][i] = "#"
    rows[1][1] = rows[8][8] = "."
    return ["".join(row) for row in rows]


def build_level(level_id: str) -> dict[str, Any]:
    definition = LEVELS[level_id]
    seed = sum(ord(c) for c in level_id)
    tiles = _grid(level_id)
    reserved = {(1, 1), (8, 8)}

    def next_free(preferred: tuple[int, int]) -> tuple[int, int]:
        """在固定偏好点附近找到可走且未占用的格，保证地图物件不互相覆盖。"""
        candidates = [preferred]
        candidates.extend(
            (x, y) for y in range(1, HEIGHT - 1) for x in range(1, WIDTH - 1) if (x, y) != preferred
        )
        for x, y in candidates:
            if tiles[y][x] != "#" and (x, y) not in reserved:
                reserved.add((x, y))
                return x, y
        raise ValueError(f"关卡 {level_id} 没有足够的可用格。")

    trap_cells = [next_free((3, 3)), next_free((6, 6))]
    supply_cells = [next_free((2, 7)), next_free((7, 2))]
    book_cell = next_free((5, 8))
    enemy_types = [
        ("盐壳蟹", "armor"),
        ("灰烬灯蛾", "burn"),
        ("钟摆傀儡", "stun"),
        ("深潜猎手", "pull"),
        ("潮汐女巫", "slow"),
        ("迷雾镜像", "copy"),
    ]
    count = 2 + seed % 3
    enemies = []
    for index in range(count):
        x, y = next_free((2 + (index * 2 + seed) % 6, 2 + (index * 3 + seed) % 5))
        kind = enemy_types[(seed + index) % len(enemy_types)]
        enemies.append(
            {
                "id": f"enemy_{index}",
                "name": kind[0],
                "behavior": kind[1],
                "x": x,
                "y": y,
                "hp": 42 + (index * 9) + seed % 10,
                "atk": 7 + index,
            }
        )
    return {
        "id": level_id,
        "definition": deepcopy(definition),
        "tiles": tiles,
        "enemies": enemies,
        "traps": [{"x": x, "y": y} for x, y in trap_cells],
        "supplies": [{"x": x, "y": y} for x, y in supply_cells],
        "exit": {"x": 8, "y": 8},
        "book": {"id": definition["book"], "x": book_cell[0], "y": book_cell[1], "claimed": False},
        "completed": False,
    }


def new_game() -> dict[str, Any]:
    return {
        "version": SAVE_VERSION,
        "phase": "EXPLORING",
        "result": "",
        "route": None,
        "level_id": "harbor",
        "level": build_level("harbor"),
        "player": {
            "name": "莉亚",
            "hp": MAX_HP,
            "max_hp": MAX_HP,
            "mp": MAX_MP,
            "max_mp": MAX_MP,
            "atk": 20,
            "gold": 80,
            "x": 1,
            "y": 1,
        },
        "learned_books": [],
        "equipped": INITIAL_SKILLS.copy(),
        "skill_cooldowns": {key: 0 for key in INITIAL_SKILLS},
        "statuses": {},
        "combat": None,
        "completed_levels": [],
        "path": [{"level_id": "harbor", "x": 1, "y": 1, "event": "start"}],
        "hit_points": [],
        "battle_log": [],
        "dps_samples": [],
        "effects": [],
        "stats": {
            "kills": 0,
            "damage": 0,
            "damage_taken": 0,
            "skill_casts": 0,
            "books_learned": 0,
            "highest_dps": 0.0,
        },
        "achievements": [],
        "last_message": "避风站的雾灯刚刚亮起。",
        "revision": 0,
        "poster": None,
    }


def _active(game: dict[str, Any]) -> None:
    if game["phase"] == "RESULT":
        raise ValueError("本次远征已经结束，请开始新的远征。")


def _message(game: dict[str, Any], text: str) -> None:
    game["last_message"] = text
    game["revision"] += 1


def _effect(
    game: dict[str, Any], skill_id: str, label: str, color: str, duration_ms: int = 650
) -> None:
    game["effects"].append(
        {
            "skill_id": skill_id,
            "label": label,
            "color": color,
            "duration_ms": duration_ms,
            "started_at": time.time(),
        }
    )
    game["effects"] = game["effects"][-6:]


def available_route_choices(game: dict[str, Any]) -> list[dict[str, Any]]:
    return (
        [{"id": key, **value} for key, value in ROUTES.items()]
        if game["phase"] == "ROUTE_CHOICE"
        else []
    )


def choose_route(game: dict[str, Any], route_id: str) -> None:
    _active(game)
    if game["phase"] != "ROUTE_CHOICE" or route_id not in ROUTES:
        raise ValueError("当前不能选择这条路线。")
    game["route"] = route_id
    next_level = ROUTES[route_id]["levels"][0]
    game["level_id"] = next_level
    game["level"] = build_level(next_level)
    game["player"].update(x=1, y=1)
    game["phase"] = "EXPLORING"
    game["path"].append({"level_id": next_level, "x": 1, "y": 1, "event": "route:" + route_id})
    _message(game, f"已选择{ROUTES[route_id]['name']}：{ROUTES[route_id]['ending']}。")


def _enemy_at(game: dict[str, Any], x: int, y: int) -> dict[str, Any] | None:
    return next(
        (
            e
            for e in game["level"]["enemies"]
            if not e.get("defeated") and (e["x"], e["y"]) == (x, y)
        ),
        None,
    )


def _can_exit(game: dict[str, Any]) -> bool:
    return all(enemy.get("defeated") for enemy in game["level"]["enemies"])


def _advance_level(game: dict[str, Any]) -> None:
    current = game["level_id"]
    if current not in game["completed_levels"]:
        game["completed_levels"].append(current)
    definition = game["level"]["definition"]
    next_level = definition["next"]
    if next_level == "route_gate":
        game["phase"] = "ROUTE_CHOICE"
        _message(game, "遗迹核心裂成三道潮光，选择一条路线决定后续地图与结局。")
        return
    if next_level is None:
        route = game["route"]
        game["phase"] = "RESULT"
        game["result"] = route
        _message(game, f"{ROUTES[route]['name']}完成：{ROUTES[route]['ending']}。")
        update_achievements(game)
        return
    game["level_id"] = next_level
    game["level"] = build_level(next_level)
    game["player"].update(
        x=1,
        y=1,
        hp=min(MAX_HP, game["player"]["hp"] + 18),
        mp=min(MAX_MP, game["player"]["mp"] + 12),
    )
    game["path"].append({"level_id": next_level, "x": 1, "y": 1, "event": "arrival"})
    _message(game, f"抵达{LEVELS[next_level]['name']}。{LEVELS[next_level]['objective']}")


def move(game: dict[str, Any], x: int, y: int) -> None:
    _active(game)
    if game["phase"] != "EXPLORING":
        raise ValueError("当前需要先完成路线选择或战斗。")
    player = game["player"]
    if abs(x - player["x"]) + abs(y - player["y"]) != 1 or not (0 <= x < WIDTH and 0 <= y < HEIGHT):
        raise ValueError("只能移动到四方向相邻格。")
    if game["level"]["tiles"][y][x] == "#":
        raise ValueError("墙体挡住了去路。")
    # 出口条件必须在提交坐标前校验，否则失败动作会把玩家留在出口格，
    # 破坏重试、轨迹和存档的一致性。
    is_exit = (x, y) == (game["level"]["exit"]["x"], game["level"]["exit"]["y"])
    if is_exit and not _can_exit(game):
        raise ValueError("出口被敌人封锁，先清理本关所有敌人。")
    enemy = _enemy_at(game, x, y)
    current_level_id = game["level_id"]
    player.update(x=x, y=y)
    event = "move"
    if enemy:
        game["combat"] = {
            **deepcopy(enemy),
            "max_hp": enemy["hp"],
            "round": 0,
            "total_damage": 0,
            "cooldowns": {key: 0 for key in game["equipped"]},
            "telegraph": False,
            "shield": 0,
        }
        game["phase"] = "COMBAT"
        event = "combat"
        _message(game, f"{enemy['name']}发动{enemy['behavior']}行为，观察预警后使用技能。")
    elif (x, y) in {(item["x"], item["y"]) for item in game["level"]["traps"]}:
        damage = min(8, player["hp"])
        player["hp"] -= damage
        game["hit_points"].append(
            {"level_id": game["level_id"], "x": x, "y": y, "damage": damage, "source": "trap"}
        )
        game["level"]["traps"] = [
            item for item in game["level"]["traps"] if (item["x"], item["y"]) != (x, y)
        ]
        game["stats"]["damage_taken"] += damage
        event = "trap"
        _message(game, f"触发盐雾陷阱，受到{damage}点伤害。")
    elif (x, y) in {(item["x"], item["y"]) for item in game["level"]["supplies"]}:
        player["hp"] = min(player["max_hp"], player["hp"] + 22)
        player["mp"] = min(player["max_mp"], player["mp"] + 12)
        game["level"]["supplies"] = [
            item for item in game["level"]["supplies"] if (item["x"], item["y"]) != (x, y)
        ]
        event = "supply"
        _message(game, "拾取潮光补给，恢复生命与魔力。")
    elif not game["level"]["book"]["claimed"] and (x, y) == (
        game["level"]["book"]["x"],
        game["level"]["book"]["y"],
    ):
        game["level"]["book"]["claimed"] = True
        book_id = game["level"]["book"]["id"]
        if book_id not in game["learned_books"]:
            game["learned_books"].append(book_id)
            game["stats"]["books_learned"] += 1
        event = "skill_book"
        _message(game, f"获得技能书《{SKILL_BOOKS[book_id]['name']}》，可在右侧装备。")
    elif (x, y) == (game["level"]["exit"]["x"], game["level"]["exit"]["y"]):
        event = "exit"
        _advance_level(game)
    game["path"].append({"level_id": current_level_id, "x": x, "y": y, "event": event})
    if player["hp"] <= 0:
        game["phase"], game["result"] = "RESULT", "defeat"
        _message(game, "莉亚倒在了迷雾中，远征失败。")
        update_achievements(game)


def _skill_data(skill_id: str) -> dict[str, Any]:
    if skill_id in SKILL_BOOKS:
        return SKILL_BOOKS[skill_id]
    return {
        "name": SKILL_NAMES[skill_id],
        "damage": {"basic": 16, "burst": 36, "echo": 14, "guard": 0}[skill_id],
        "cost": {"basic": 0, "burst": 12, "echo": 0, "guard": 0}[skill_id],
        "cooldown": {"basic": 0, "burst": 3, "echo": 1, "guard": 1}[skill_id],
        "kind": skill_id,
        "color": "#e9b95f",
        "description": "初始技能",
    }


def equip_skill(game: dict[str, Any], skill_id: str, slot: int) -> None:
    _active(game)
    if skill_id not in INITIAL_SKILLS and skill_id not in game["learned_books"]:
        raise ValueError("尚未学习这本技能书。")
    if not 0 <= slot < 4:
        raise ValueError("主动技能栏只有4个。")
    if skill_id in game["equipped"]:
        old = game["equipped"].index(skill_id)
        game["equipped"][old], game["equipped"][slot] = (
            game["equipped"][slot],
            game["equipped"][old],
        )
    else:
        game["equipped"][slot] = skill_id
    _message(game, f"技能栏{slot + 1}已装备{_skill_data(skill_id)['name']}。")


def act(game: dict[str, Any], skill_id: str) -> None:
    _active(game)
    if game["phase"] != "COMBAT" or not game["combat"]:
        raise ValueError("当前没有战斗。")
    if skill_id not in game["equipped"] and skill_id != "wait":
        raise ValueError("该技能不在主动技能栏。")
    combat, player = game["combat"], game["player"]
    data = (
        _skill_data(skill_id)
        if skill_id != "wait"
        else {
            "name": "等待",
            "damage": 0,
            "cost": -3,
            "cooldown": 0,
            "kind": "wait",
            "color": "#809098",
        }
    )
    if skill_id != "wait" and combat["cooldowns"].get(skill_id, 0) > 0:
        raise ValueError("技能还在冷却中。")
    if skill_id != "wait" and player["mp"] < data["cost"]:
        raise ValueError("MP不足。")
    for equipped_id in list(combat["cooldowns"]):
        combat["cooldowns"][equipped_id] = max(0, combat["cooldowns"][equipped_id] - 1)
    damage = 0
    if skill_id == "wait":
        player["mp"] = min(player["max_mp"], player["mp"] + 3)
    elif skill_id == "guard":
        player["mp"] = min(player["max_mp"], player["mp"] + 4)
        combat["shield"] = 12
        combat["cooldowns"][skill_id] = data["cooldown"]
    else:
        player["mp"] -= data["cost"]
        damage = min(combat["hp"], data["damage"] + (player["atk"] - 20))
        combat["hp"] -= damage
        combat["cooldowns"][skill_id] = data["cooldown"]
        if data["kind"] == "heal":
            player["hp"] = min(player["max_hp"], player["hp"] + 12)
        elif data["kind"] == "shield":
            combat["shield"] = 16
        elif data["kind"] == "sacrifice":
            player["hp"] = max(1, player["hp"] - 8)
        elif data["kind"] in {"fear", "decoy", "pull"}:
            combat["telegraph"] = False
    combat["round"] += 1
    combat["total_damage"] += damage
    game["stats"]["skill_casts"] += int(skill_id != "wait")
    game["stats"]["damage"] += damage
    elapsed = combat["round"] * 1.5
    dps = damage / 1.5
    game["stats"]["highest_dps"] = max(game["stats"]["highest_dps"], dps)
    game["dps_samples"].append(
        {
            "elapsed": len(game["dps_samples"]) * 1.5,
            "battle_elapsed": elapsed,
            "damage": damage,
            "dps": dps,
            "action": skill_id,
            "vacuum": damage == 0,
        }
    )
    game["battle_log"].append(
        {
            "level_id": game["level_id"],
            "round": combat["round"],
            "action": skill_id,
            "damage": damage,
            "enemy_hp": combat["hp"],
            "player_hp": player["hp"],
            "player_mp": player["mp"],
            "counter": 0,
        }
    )
    _effect(
        game, skill_id, data["name"], data["color"], 1100 if data.get("kind") == "burst" else 650
    )
    if combat["hp"] <= 0:
        enemy = _enemy_at(game, player["x"], player["y"])
        if enemy:
            enemy["defeated"] = True
        game["stats"]["kills"] += 1
        player["gold"] += 15
        game["combat"] = None
        game["phase"] = "EXPLORING"
        _message(game, f"{combat['name']}被击败。技能演出完成，可以继续探索。")
        update_achievements(game)
        return
    # 敌方反击在技能结算后发生；护盾/恐惧/诱饵只改变本次反击，保证技能有清晰成本。
    counter = combat["atk"]
    if combat.get("shield", 0):
        counter = max(0, counter - combat["shield"])
        combat["shield"] = 0
    if data.get("kind") in {"fear", "decoy", "pull"}:
        counter //= 2
    if combat.get("telegraph"):
        counter *= 2
    combat["telegraph"] = combat["round"] % 3 == 1
    counter = min(player["hp"], counter)
    player["hp"] -= counter
    game["stats"]["damage_taken"] += counter
    game["hit_points"].append(
        {
            "level_id": game["level_id"],
            "x": player["x"],
            "y": player["y"],
            "damage": counter,
            "source": combat["name"],
        }
    )
    game["battle_log"][-1]["counter"] = counter
    _message(
        game,
        f"{data['name']}造成{damage}伤害，敌人反击{counter}。"
        + ("敌人正在蓄力！" if combat["telegraph"] else ""),
    )
    if player["hp"] <= 0:
        game["phase"], game["result"] = "RESULT", "defeat"
        update_achievements(game)


def update_achievements(game: dict[str, Any]) -> None:
    checks = {
        "first_skill": game["stats"]["skill_casts"] > 0,
        "first_book": game["stats"]["books_learned"] > 0,
        "route_keeper": game["result"] == "keeper",
        "route_tide": game["result"] == "tide",
        "route_oath": game["result"] == "oath",
        "explorer": len(game["completed_levels"]) >= 5,
        "all_books": game["stats"]["books_learned"] >= 11,
        "no_defeat": game["result"] in ROUTES and game["stats"]["damage_taken"] == 0,
    }
    for key, passed in checks.items():
        if passed and key not in game["achievements"]:
            game["achievements"].append(key)
    # 先写入本次结局，再判断三路线成就，避免遗漏当前刚完成的路线。
    if all(key in game["achievements"] for key in ("route_keeper", "route_tide", "route_oath")):
        if "all_routes" not in game["achievements"]:
            game["achievements"].append("all_routes")


def save_game(game: dict[str, Any], slot: int = 1) -> Path:
    if slot not in {1, 2, 3}:
        raise ValueError("存档位必须是1、2或3。")
    path = _runtime_dir() / f"slot{slot}.json"
    temporary = path.with_suffix(".tmp")
    payload = deepcopy(game)
    payload["combat"] = None if game["phase"] != "COMBAT" else payload["combat"]
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return path


def load_game(slot: int = 1) -> dict[str, Any]:
    if slot not in {1, 2, 3}:
        raise ValueError("存档位必须是1、2或3。")
    path = _runtime_dir() / f"slot{slot}.json"
    if not path.is_file():
        raise FileNotFoundError("该存档位为空。")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != SAVE_VERSION:
            raise ValueError("存档版本不兼容。")
        return payload
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        broken = path.with_suffix(".broken")
        path.replace(broken)
        raise ValueError(f"存档损坏，已备份为{broken.name}。") from exc


def save_summary(slot: int) -> dict[str, Any]:
    path = _runtime_dir() / f"slot{slot}.json"
    if not path.is_file():
        return {"slot": slot, "exists": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "slot": slot,
            "exists": True,
            "level_id": data.get("level_id"),
            "route": data.get("route"),
            "result": data.get("result"),
            "updated": path.stat().st_mtime,
        }
    except (OSError, json.JSONDecodeError):
        return {"slot": slot, "exists": True, "broken": True}
