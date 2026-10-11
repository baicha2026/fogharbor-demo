"""纯Python剧情规则。每次动作先校验再提交，Streamlit重跑不重复发奖励。"""

from copy import deepcopy
from math import ceil

from adventure.content import ENDING, INTRO, MAPS, REWARD
from game.engine import MAX_HP, MAX_MP, SKILLS


def new_game() -> dict:
    # 开局HP100/MP40/ATK20沿用策划试炼数值；30金币只够买一瓶20金币药剂。
    # 用药恢复35HP/6MP；港口赠送、宝箱与支线各自独立，通关不必付费买药。
    return {
        "phase": "EXPLORING",
        "result": "",
        "map_id": "harbor",
        "revision": 0,
        "player": {"name": "莉亚", "hp": 100, "mp": 40, "atk": 20, "gold": 30, "x": 2, "y": 5},
        "inventory": {"potion": 0, "fragment": 0, "herb": 0},
        "quest_stage": "meet",
        "side_quest": "none",
        "boss_defeated": False,
        "removed": {"harbor": [], "ruins": []},
        "combat": None,
        "kills": 0,
        "path": [{"map_id": "harbor", "x": 2, "y": 5, "event": "start"}],
        "hit_points": [],
        "battle_log": [],
        "dps_samples": [],
        "reward_paid": False,
        "dialogue": {"speaker": "序章", "portrait": "hero", "text": INTRO},
        "journal": [INTRO],
        "review": "",
        "poster": None,
    }


def active(game: dict) -> None:
    if game["phase"] == "RESULT":
        raise ValueError("本次冒险已经结束，请开始新的冒险。")


def say(game: dict, text: str, speaker: str = "莉亚", portrait: str = "hero") -> None:
    game["dialogue"] = {"speaker": speaker, "portrait": portrait, "text": text}
    game["journal"].append(text)
    game["revision"] += 1


def entities(game: dict) -> list[dict]:
    return [
        entity
        for entity in MAPS[game["map_id"]]["entities"]
        if entity["id"] not in game["removed"][game["map_id"]]
    ]


def entity_at(game: dict, x: int, y: int) -> dict | None:
    return next((e for e in entities(game) if (e["x"], e["y"]) == (x, y)), None)


def near(game: dict, entity: dict) -> bool:
    p = game["player"]
    return abs(p["x"] - entity["x"]) + abs(p["y"] - entity["y"]) <= 1


def interactions(game: dict) -> list[dict]:
    if game["phase"] != "EXPLORING":
        return []
    return [e for e in entities(game) if e["kind"] in {"npc", "rest", "beacon"} and near(game, e)]


def _interactable(game: dict, entity_id: str) -> dict:
    active(game)
    if game["phase"] != "EXPLORING":
        raise ValueError("战斗中无法与场景互动。")
    entity = next((e for e in interactions(game) if e["id"] == entity_id), None)
    if not entity:
        raise ValueError("请先走到目标旁边。")
    return entity


def interact(game: dict, entity_id: str) -> None:
    _interactable(game, entity_id)
    if entity_id == "lorn":
        if game["quest_stage"] == "meet":
            game["quest_stage"] = "fragments"
            game["inventory"]["potion"] += 2
            say(
                game,
                "莉亚，遗迹中的三名守卫封印了灯芯。带回三枚碎片，击败熄灯者。"
                "这两瓶药剂给你——别逞强，避风泉随时欢迎你回来。",
                "洛恩",
                "lorn",
            )
        elif game["quest_stage"] == "return":
            game["quest_stage"] = "complete"
            game["phase"], game["result"] = "RESULT", "victory"
            if not game["reward_paid"]:
                game["player"]["gold"] += REWARD["gold"]
                game["player"]["hp"] = min(MAX_HP, game["player"]["hp"] + REWARD["hp"])
                game["reward_paid"] = True
            say(game, ENDING, "洛恩", "lorn")
        else:
            say(
                game,
                "每枚灯芯都受一名守卫封印。找到它们，便能打开熄灯者的封印。"
                "药剂可以带入战斗，记得看清敌人蓄力时的光。",
                "洛恩",
                "lorn",
            )
    elif entity_id == "eve":
        if game["side_quest"] == "none":
            game["side_quest"] = "collect"
            say(
                game,
                "遗迹西侧长着月露草。带一株回来，我给你两瓶药剂。我也出售应急药剂，每瓶20金币。",
                "艾芙",
                "eve",
            )
        elif game["side_quest"] == "collect" and game["inventory"]["herb"]:
            game["inventory"]["herb"] -= 1
            game["inventory"]["potion"] += 2
            game["player"]["hp"] = min(MAX_HP, game["player"]["hp"] + 25)
            game["side_quest"] = "complete"
            say(
                game,
                "正是这株草！两瓶药剂是你的，我也替你包扎好了。"
                "若你看见灯塔亮起，替我向归航的人们问好。",
                "艾芙",
                "eve",
            )
        else:
            say(game, "药剂能恢复35点生命和6点魔力。别等到最后一口气才用。", "艾芙", "eve")
    elif entity_id == "fountain":
        # 港口是明确的安全区：返回可以免费恢复，但需再次走过探索路径。
        game["player"]["hp"], game["player"]["mp"] = MAX_HP, MAX_MP
        say(game, "避风泉洗去了疲惫。生命和魔力已完全恢复。", "避风泉", "fountain")
    else:
        say(game, "旧灯塔等待三枚完整的灯芯。向洛恩打听修复的方法。", "灯塔", "beacon")


def buy_potion(game: dict) -> None:
    _interactable(game, "eve")
    if game["player"]["gold"] < 20:
        raise ValueError("需要20金币。遗迹宝箱和击败敌人都能获得金币。")
    game["player"]["gold"] -= 20
    game["inventory"]["potion"] += 1
    say(game, "药剂已放进背包。祝你平安。", "艾芙", "eve")


def _heal(game: dict) -> int:
    # 数量校验必须在技能冷却推进或敌人反击前完成，空背包不是有效回合。
    if game["inventory"]["potion"] <= 0:
        raise ValueError("背包里没有药剂。")
    amount = min(35, MAX_HP - game["player"]["hp"])  # 溢出治疗不计入实际恢复。
    game["inventory"]["potion"] -= 1
    game["player"]["hp"] += amount
    game["player"]["mp"] = min(MAX_MP, game["player"]["mp"] + 6)
    return amount


def use_potion(game: dict) -> None:
    active(game)
    if game["phase"] == "COMBAT":
        act(game, "potion")
    else:
        hp = _heal(game)
        say(game, f"使用药剂，恢复{hp}点生命与上限内6点魔力。")


def _remove(game: dict, entity: dict) -> None:
    game["removed"][game["map_id"]].append(entity["id"])


def _hit(game: dict, damage: int, source: str) -> int:
    # 受击数据只记录实际扣血值，附地图ID，避免两个地图同坐标错误聚合。
    p = game["player"]
    damage = min(p["hp"], damage)
    p["hp"] -= damage
    game["hit_points"].append(
        {"map_id": game["map_id"], "x": p["x"], "y": p["y"], "damage": damage, "source": source}
    )
    if p["hp"] == 0:
        game["phase"], game["result"] = "RESULT", "defeat"
    return damage


def move(game: dict, x: int, y: int) -> None:
    active(game)
    if game["phase"] != "EXPLORING":
        raise ValueError("先完成当前战斗。")
    p = game["player"]
    if not (0 <= x < 10 and 0 <= y < 10) or abs(x - p["x"]) + abs(y - p["y"]) != 1:
        raise ValueError("只能移动到四方向相邻格。")
    if MAPS[game["map_id"]]["tiles"][y][x] == "#":
        raise ValueError("石墙挡住了去路。")
    entity = entity_at(game, x, y)
    if entity:
        if entity["kind"] == "npc":
            raise ValueError(f"{entity['name']}在这里。走到旁边与其交谈。")
        if entity["id"] == "exit" and game["quest_stage"] == "meet":
            raise ValueError("先与洛恩交谈，接下委托。")
        if entity["kind"] == "boss" and game["inventory"]["fragment"] < 3:
            raise ValueError("首领封印需要三枚灯芯碎片。")
        if entity["kind"] == "fragment" and entity["guard"] not in game["removed"]["ruins"]:
            raise ValueError("这枚碎片仍被封印，先击败对应的守卫。")
    p["x"], p["y"] = x, y
    game["path"].append(
        {"map_id": game["map_id"], "x": x, "y": y, "event": entity["kind"] if entity else "move"}
    )
    if not entity:
        say(game, "石板下传来潮声。" if game["map_id"] == "ruins" else "避风站的灯火仍然温暖。")
        return
    kind = entity["kind"]
    if kind == "exit":
        game["map_id"] = "ruins" if game["map_id"] == "harbor" else "harbor"
        p["x"], p["y"] = [2, 1] if game["map_id"] == "ruins" else [7, 7]
        game["path"].append(
            {"map_id": game["map_id"], "x": p["x"], "y": p["y"], "event": "arrival"}
        )
        say(
            game,
            "进入灯塔遗迹。三枚灯芯分布在遗迹的不同角落。"
            if game["map_id"] == "ruins"
            else "回到了避风站。这里可以休息、购买药剂和交付委托。",
        )
    elif kind in {"enemy", "boss"}:
        # 每场战斗重新初始化CD；HP、MP、背包随整局继承。
        game["combat"] = {
            **deepcopy(entity),
            "entity_id": entity["id"],
            "max_hp": entity["hp"],
            "cooldowns": {"burst": 0, "flow": 0},
            "round": 0,
            "charged": False,
            "total_damage": 0,
            "battle_id": game["kills"] + 1,
        }
        game["phase"] = "COMBAT"
        say(game, f"{entity['name']}挡住了去路。战斗开始！", entity["name"], entity["sprite"])
    elif kind == "chest":
        p["gold"] += entity["gold"]
        game["inventory"]["potion"] += entity["potions"]
        _remove(game, entity)
        say(game, f"打开{entity['name']}：获得{entity['gold']}金币和{entity['potions']}瓶药剂。")
    elif kind in {"fragment", "herb"}:
        game["inventory"][kind] += 1
        _remove(game, entity)
        if kind == "fragment":
            count = game["inventory"]["fragment"]
            if count == 3:
                game["quest_stage"] = "boss"
            say(
                game,
                f"获得{entity['name']}，灯芯收集{count}/3。"
                + ("东南角的首领封印已经解开。" if count == 3 else "继续寻找其它守卫。"),
            )
        else:
            say(game, "拾起月露草。可以回避风站交给艾芙。")
    elif kind == "trap":
        damage = _hit(game, 8, "trap")
        _remove(game, entity)
        say(game, f"触发旧机关，受到{damage}点伤害。机关已失效。")
    else:
        say(game, f"来到{entity['name']}旁，可以在右侧互动。")


def act(game: dict, action: str) -> None:
    active(game)
    c, p = game["combat"], game["player"]
    if game["phase"] != "COMBAT" or not c:
        raise ValueError("当前没有战斗。")
    if action not in {*SKILLS, "guard", "wait", "potion"}:
        raise ValueError("未知战斗动作。")
    if action in SKILLS:
        skill = SKILLS[action]
        if c["cooldowns"][action] or p["mp"] < skill["mana"]:
            raise ValueError("技能冷却中或魔力不足。")
    if action == "potion" and game["inventory"]["potion"] == 0:
        raise ValueError("背包里没有药剂。")
    unavailable = all(c["cooldowns"][name] or p["mp"] < s["mana"] for name, s in SKILLS.items())
    # CD在合法行动开始时推进；新施放的技能最后写入CD，保证完整的后续等待回合。
    for key in c["cooldowns"]:
        c["cooldowns"][key] = max(0, c["cooldowns"][key] - 1)
    damage = 0
    if action in SKILLS:
        skill = SKILLS[action]
        p["mp"] -= skill["mana"]
        damage = min(c["hp"], round(p["atk"] * skill["multiplier"]))
        c["hp"] -= damage
        c["cooldowns"][action] = skill["cooldown"]
        if action == "flow":
            p["mp"] = min(MAX_MP, p["mp"] + 8)
    elif action == "potion":
        _heal(game)
    else:
        # 防御回4MP、等待回3MP；防御也消耗回合但反击减至1/3，二者都不会免疫攻击。
        p["mp"] = min(MAX_MP, p["mp"] + (4 if action == "guard" else 3))
    c["round"] += 1
    c["total_damage"] += damage
    counter = 0
    if c["hp"] > 0:
        if c["kind"] == "boss":
            # 首领每两回合一次重击：第一回合普通攻击并蓄力，第二回合18伤害。
            # 提前显示charged，防御将伤害降为1/3，向上取整，不能降成零风险。
            raw = c["atk"] * (2 if c["charged"] else 1)
            c["charged"] = not c["charged"]
        else:
            raw = c["atk"]
        counter = _hit(game, ceil(raw / 3) if action == "guard" else raw, c["name"])
    elapsed = (len(game["dps_samples"]) + 1) * 2  # 同现有策划系统，每回合2秒。
    vacuum = unavailable and action not in SKILLS  # 主动防御/喝药不自动算技能真空。
    game["dps_samples"].append(
        {
            "elapsed": elapsed,
            "battle_elapsed": c["round"] * 2,
            "battle_id": c["battle_id"],
            "damage": damage,
            "dps": damage / 2,
            "avg_dps": c["total_damage"] / (c["round"] * 2),
            "action": action,
            "vacuum": vacuum,
        }
    )
    game["battle_log"].append(
        {
            "map_id": game["map_id"],
            "battle_id": c["battle_id"],
            "round": c["round"],
            "action": action,
            "damage": damage,
            "counter": counter,
            "enemy_hp": c["hp"],
            "player_hp": p["hp"],
            "player_mp": p["mp"],
            "x": p["x"],
            "y": p["y"],
            "vacuum": vacuum,
        }
    )
    if c["hp"] == 0:
        _remove(game, c)
        game["kills"] += 1
        p["gold"] += 25 if c["kind"] == "boss" else 12  # 击杀收益独立于80金币主线奖励。
        game["phase"], game["combat"] = "EXPLORING", None
        if c["kind"] == "boss":
            game["boss_defeated"], game["quest_stage"] = True, "return"
        say(
            game,
            f"击败{c['name']}！"
            + (
                "灯芯重获光芒。回去找洛恩吧。"
                if c["kind"] == "boss"
                else "它所守护的灯芯封印已经解除。"
            ),
        )
    elif p["hp"] == 0:
        say(game, "莉亚倒在了迷雾中。灯塔仍在等待下一位守灯人。", "迷雾", "boss")
    else:
        label = (
            SKILLS[action]["name"]
            if action in SKILLS
            else {"guard": "防御", "wait": "等待", "potion": "药剂"}[action]
        )
        say(
            game,
            f"{label}：造成{damage}伤害，受到{counter}伤害。"
            + ("熄灯者正在蓄力！下回合重击，建议防御。" if c["charged"] else ""),
        )
