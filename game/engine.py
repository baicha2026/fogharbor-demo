"""AI 技术策划试炼场的地图、移动和战斗数值。

所有函数都在传入的 arena 字典上原地提交一次完整动作；动作校验失败时先校验再
写入，保证 UI 重跑不会产生半次移动或半次攻击。
"""

from __future__ import annotations

import random
from typing import Any

WIDTH = HEIGHT = 10
# 事件格占26%，保留74%空地，允许绕行并比较“短路受伤”和“绕路补给”。
# 六个目标提供多场遭遇样本，而不是一次战斗就决定整局结果。
TRAPS, MONSTERS, SUPPLIES = 12, 6, 8
MAX_HP, MAX_MP = 100, 40
# 基准ATK20使双技能组合伤害=36+14=50；敌人HP跨越50形成两种循环。
START_ATK = 20
TRAP_DAMAGE = 8
# 单个补给25HP约覆盖5次普通反击，12MP等于一次爆发技能成本。
SUPPLY_HP, SUPPLY_MP = 25, 12
SKILLS = {
    "burst": {"name": "技能1 · 破阵重击", "multiplier": 1.8, "mana": 12, "cooldown": 3},
    "flow": {"name": "技能2 · 潮汐回响", "multiplier": 0.7, "mana": 0, "cooldown": 1},
}


def new_game(
    task: dict[str, Any] | None = None, *, hp_ratio: int = 100, gold: int = 250, seed: int = 42
) -> dict[str, Any]:
    """建立可复现的新局；出生点和两个起步格固定为补给，保证教学路径可走。"""
    rng = random.Random(seed)
    grid = [[0 for _ in range(WIDTH)] for _ in range(HEIGHT)]
    reserved = {(0, 0), (1, 0), (0, 1)}
    candidates = [(x, y) for y in range(HEIGHT) for x in range(WIDTH) if (x, y) not in reserved]
    rng.shuffle(candidates)
    # 两个固定教学补给占据供应总数中的两个名额。
    for value, count in ((1, TRAPS), (2, MONSTERS), (3, SUPPLIES - 2)):
        for _ in range(count):
            x, y = candidates.pop()
            grid[y][x] = value
    grid[0][1] = grid[1][0] = 3
    player_hp = max(0, min(MAX_HP, round(MAX_HP * hp_ratio / 100)))
    return {
        "phase": ("RESULT" if player_hp == 0 else "EXPLORING") if task else "SETUP",
        "result": "defeat" if task and player_hp == 0 else "",
        "seed": seed,
        "map": grid,
        "player": {
            "hp": player_hp,
            "mp": MAX_MP,
            "atk": START_ATK,
            "x": 0,
            "y": 0,
            "gold": max(0, int(gold)),
        },
        "path": [{"x": 0, "y": 0, "event": "start"}],
        "hit_points": [],
        "battle_log": [],
        "dps_samples": [],
        "kills": 0,
        "monsters_total": MONSTERS,
        "combat": None,
        "task": task or {},
        "reward_paid": False,
        "earned_item": "",
        "review": "",
        "poster": None,
        "review_attempted": False,
    }


def _ensure_active(game: dict[str, Any]) -> None:
    if game["phase"] == "RESULT":
        raise ValueError("试炼已经结束，请重新开始一局")
    if game["phase"] == "SETUP":
        raise ValueError("请先生成任务开启试炼")


def _set_result(game: dict[str, Any], result: str) -> None:
    game["phase"] = "RESULT"
    game["result"] = result
    if result == "victory" and not game["reward_paid"]:
        # 在终态入口结算奖励，而不是页面渲染时结算；重跑和导出不重复发放。
        reward = game.get("task", {}).get("rewards", {})
        game["player"]["gold"] = min(1_000_000, game["player"]["gold"] + int(reward.get("gold", 0)))
        game["player"]["hp"] = min(MAX_HP, game["player"]["hp"] + int(reward.get("hp", 0)))
        game["earned_item"] = str(reward.get("item_name", "胜利徽章"))
        game["reward_paid"] = True


def finish(game: dict[str, Any], reason: str = "retreat") -> dict[str, Any]:
    if game["phase"] in {"EXPLORING", "COMBAT"}:
        _set_result(game, "retreat")
    return game


def move(game: dict[str, Any], x: int, y: int) -> dict[str, Any]:
    _ensure_active(game)
    if game["phase"] == "COMBAT":
        raise ValueError("战斗中必须先完成当前遭遇")
    player = game["player"]
    if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
        raise ValueError("目标位置超出地图")
    if abs(x - player["x"]) + abs(y - player["y"]) != 1:
        raise ValueError("只能移动到相邻格")
    game["phase"] = "EXPLORING"
    player["x"], player["y"] = x, y
    cell = game["map"][y][x]
    event = "move"
    if cell == 1:
        # 陷阱的实际伤害取剩余 HP，热力图统计挫败感而非越界数值。
        damage = min(TRAP_DAMAGE, player["hp"])
        player["hp"] -= damage
        game["hit_points"].append({"x": x, "y": y, "damage": damage, "source": "trap"})
        event = "trap"
        game["map"][y][x] = 0
    elif cell == 2:
        # 坐标哈希提供确定性的HP42–54、ATK4–6。相同布局有相同难度，
        # 便于对比技能和路线；HP>50的敌人需要多一个回蓝/冷却窗口。
        enemy_hp = 42 + ((x * 7 + y * 3) % 13)
        game["combat"] = {
            "hp": enemy_hp,
            "max_hp": enemy_hp,
            "atk": 4 + ((x + y) % 3),
            "cooldowns": {"burst": 0, "flow": 0},
            "elapsed": 0,
            "total_damage": 0,
            "battle_id": game["kills"] + 1,
            "enemy_name": f"坐标异兽 ({x},{y})",
        }
        game["phase"] = "COMBAT"
        event = "monster"
    elif cell == 3:
        # 补给不可储存或刷取：即使已满也消耗该格，路线应考虑使用时机。
        player["hp"] = min(MAX_HP, player["hp"] + SUPPLY_HP)
        player["mp"] = min(MAX_MP, player["mp"] + SUPPLY_MP)
        game["map"][y][x] = 0
        event = "supply"
    game["path"].append({"x": x, "y": y, "event": event})
    if player["hp"] <= 0:
        _set_result(game, "defeat")
    elif len(game["path"]) >= 401:
        _set_result(game, "retreat")
    return game


def _record_round(game: dict[str, Any], action: str, damage: int, vacuum: bool) -> None:
    combat = game["combat"]
    combat["elapsed"] += 2  # 一个按钮动作代表策划验证中的两秒回合。
    combat["total_damage"] += damage
    elapsed = combat["elapsed"]
    sample = {
        # 全局时间保持跨战斗递增，本场时间独立，用于每个遭遇的平均DPS。
        "elapsed": (len(game["dps_samples"]) + 1) * 2,
        "battle_elapsed": elapsed,
        "battle_id": combat["battle_id"],
        "damage": damage,
        "dps": damage / 2,
        "avg_dps": combat["total_damage"] / elapsed,
        "action": action,
        "vacuum": vacuum,
    }
    game["dps_samples"].append(sample)
    game["battle_log"].append(
        {
            "round": len(game["dps_samples"]),
            "action": action,
            "damage": damage,
            "enemy_hp": combat["hp"],
            "player_hp": game["player"]["hp"],
            "player_mp": game["player"]["mp"],
            "dps": sample["dps"],
            "vacuum": vacuum,
            "x": game["player"]["x"],
            "y": game["player"]["y"],
            "battle_id": combat["battle_id"],
        }
    )


def act(game: dict[str, Any], action: str) -> dict[str, Any]:
    _ensure_active(game)
    if game["phase"] != "COMBAT" or not game["combat"]:
        raise ValueError("当前没有进行中的战斗")
    if action not in (*SKILLS, "wait"):
        raise ValueError("未知战斗动作")
    combat = game["combat"]
    player = game["player"]
    # 先校验后写入：按钮重复点击不能通过失败动作偷偷推进冷却。
    if action in SKILLS:
        skill = SKILLS[action]
        if combat["cooldowns"][action] > 0:
            raise ValueError(f"{skill['name']} 还在冷却中")
        if player["mp"] < skill["mana"]:
            raise ValueError("MP 不足，无法施放技能1")
    available = [
        name
        for name, skill in SKILLS.items()
        if combat["cooldowns"][name] == 0 and player["mp"] >= skill["mana"]
    ]
    # CD=3 代表接下来三个完整动作不能再用。当前动作结束时递减其它技能，
    # 本回合施放的技能最后赋值，避免“施放当回合就减掉一格”的常见偏差。
    for key in combat["cooldowns"]:
        combat["cooldowns"][key] = max(0, combat["cooldowns"][key] - 1)
    if action in SKILLS:
        skill = SKILLS[action]
        player["mp"] -= skill["mana"]
        damage = min(combat["hp"], round(player["atk"] * skill["multiplier"]))
        # DPS仅计实际伤害：打掉最后4HP不应被统计成36点爆发。
        combat["hp"] -= damage
        if action == "flow":
            player["mp"] = min(MAX_MP, player["mp"] + 8)
        combat["cooldowns"][action] = skill["cooldown"]
        vacuum = False
    else:
        damage = 0
        vacuum = not available
        # 等待回3MP，避免低蓝且全技能冷却时无合法动作，但承受反击作为成本。
        player["mp"] = min(MAX_MP, player["mp"] + 3)
    if combat["hp"] <= 0:
        game["kills"] += 1
        player["gold"] = min(1_000_000, player["gold"] + 12)  # 每个击杀的策划验证积分。
        x, y = player["x"], player["y"]
        game["map"][y][x] = 0
        _record_round(game, action, damage, vacuum)
        game["combat"] = None
        game["phase"] = "EXPLORING"
        if game["kills"] >= int(game.get("task", {}).get("target_monsters", MONSTERS)):
            _set_result(game, "victory")
        elif len(game["dps_samples"]) >= 200:
            _set_result(game, "retreat")
        return game
    # 敌人仅在存活时反击；击杀回合不应产生隐形受击点。
    counter = min(combat["atk"], player["hp"])
    player["hp"] -= counter
    game["hit_points"].append(
        {"x": player["x"], "y": player["y"], "damage": counter, "source": "enemy"}
    )
    _record_round(game, action, damage, vacuum)
    if player["hp"] <= 0:
        _set_result(game, "defeat")
    elif len(game["dps_samples"]) >= 200:
        _set_result(game, "retreat")
    return game
