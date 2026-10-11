"""E盘Chromium实际通关，所有动作通过网页完成，保存本地截图。"""

import heapq
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from adventure import engine
from adventure.content import MAPS
from runtime_paths import configure_local_paths

ROOT = Path(__file__).resolve().parents[1]


def route(game, target):
    p = game["player"]
    queue = [(0, (p["x"], p["y"]), [])]
    seen = set()
    while queue:
        cost, pos, path = heapq.heappop(queue)
        if pos == target:
            return path
        if pos in seen:
            continue
        seen.add(pos)
        for dx, dy in ((0, -1), (-1, 0), (0, 1), (1, 0)):
            x, y = pos[0] + dx, pos[1] + dy
            if not (0 <= x < 10 and 0 <= y < 10) or MAPS[game["map_id"]]["tiles"][y][x] == "#":
                continue
            entity = engine.entity_at(game, x, y)
            if entity and (x, y) != target:
                if entity["kind"] in {"npc", "exit", "enemy", "boss", "fragment"}:
                    continue
            weight = 12 if entity and entity["kind"] == "trap" else 1
            heapq.heappush(queue, (cost + weight, (x, y), path + [(x, y)]))
    raise AssertionError(f"没有到{target}的路线")


class Driver:
    def __init__(self, page):
        self.page = page
        self.game = engine.new_game()

    def check(self):
        g, p = self.game, self.game["player"]
        steps = sum(row["event"] != "arrival" for row in g["path"]) - 1
        text = f"莉亚位置 ({p['x']},{p['y']}) · 移动 {steps} 步 · 击败 {g['kills']} 个敌人"
        expect(self.page.get_by_text(text, exact=True)).to_be_visible()
        assert self.page.locator('[data-testid="stException"]').count() == 0

    def move(self, x, y, method="button"):
        if method == "canvas":
            canvas = self.page.locator('canvas[aria-label="可点击的冒险地图"]')
            canvas.scroll_into_view_if_needed()
            bounds = canvas.bounding_box()
            self.page.mouse.click(
                bounds["x"] + (x + 0.5) * bounds["width"] / 10,
                bounds["y"] + (y + 0.5) * bounds["height"] / 10,
            )
        elif method == "keyboard":
            self.page.locator(".game-board").focus()
            p = self.game["player"]
            key = {
                (0, -1): "ArrowUp",
                (0, 1): "ArrowDown",
                (-1, 0): "ArrowLeft",
                (1, 0): "ArrowRight",
            }[(x - p["x"], y - p["y"])]
            self.page.keyboard.press(key)
        else:
            p = self.game["player"]
            label = {(0, -1): "↑ 上", (0, 1): "↓ 下", (-1, 0): "← 左", (1, 0): "→ 右"}[
                (x - p["x"], y - p["y"])
            ]
            self.page.get_by_role("button", name=label, exact=True).click()
        engine.move(self.game, x, y)
        self.check()

    def walk(self, target):
        for x, y in route(self.game, target):
            self.move(x, y)

    def interact(self, entity_id, method="button"):
        labels = {"lorn": "与洛恩交谈", "eve": "与艾芙交谈", "fountain": "在避风泉休息"}
        if method == "keyboard":
            self.page.locator(".game-board").focus()
            self.page.keyboard.press("e")
        else:
            self.page.get_by_role("button", name=labels[entity_id], exact=True).click()
        engine.interact(self.game, entity_id)
        expect(
            self.page.get_by_text(self.game["dialogue"]["text"], exact=True).last
        ).to_be_visible()

    def fight(self):
        count = 0
        while self.game["phase"] == "COMBAT":
            p, c = self.game["player"], self.game["combat"]
            if c["charged"]:
                action = "guard"
            elif p["hp"] < 55 and self.game["inventory"]["potion"]:
                action = "potion"
            elif c["cooldowns"]["burst"] == 0 and p["mp"] >= 12:
                action = "burst"
            elif c["cooldowns"]["flow"] == 0:
                action = "flow"
            else:
                action = "guard"
            name = {
                "burst": "破阵重击",
                "flow": "潮汐回响",
                "guard": "防御 · 减伤 / 回4MP",
                "potion": "使用药剂",
            }[action]
            if action == "burst" and count == 0:
                self.page.locator(".game-board").focus()
                self.page.keyboard.press("1")
            else:
                self.page.get_by_role("button", name=name, exact=True).click()
            engine.act(self.game, action)
            expect(
                self.page.get_by_text(self.game["dialogue"]["text"], exact=True).last
            ).to_be_visible()
            count += 1
            assert count < 40
        self.check()
        assert self.game["phase"] == "EXPLORING"


def main():
    configure_local_paths()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--disable-gpu-shader-disk-cache"])
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(
            os.getenv("FOGHARBOR_TEST_URL", "http://127.0.0.1:8501"), wait_until="domcontentloaded"
        )
        # 大型2D远征现在是默认首页；本脚本覆盖旧版剧情冒险，因此显式切换模式。
        expect(page.get_by_text("AI技术策划试炼场 · 大型远征", exact=True)).to_be_visible()
        page.locator('[data-testid="stExpandSidebarButton"]').click()
        expect(page.locator('[data-testid="stSidebar"]')).to_have_attribute("aria-expanded", "true")
        page.get_by_text("剧情冒险", exact=True).click()
        page.locator('[data-testid="stSidebarCollapseButton"]').click()
        expect(page.get_by_role("button", name="开始冒险", exact=True)).to_be_visible()
        page.screenshot(path=str(ROOT / "artifacts/fogharbor-title.png"), full_page=True)
        page.get_by_role("button", name="开始冒险", exact=True).click()
        d = Driver(page)
        d.check()
        d.move(2, 4, method="canvas")
        d.move(2, 3, method="keyboard")
        d.move(2, 2)
        d.interact("lorn", method="keyboard")
        d.walk((5, 2))
        d.interact("eve")
        page.get_by_role("button", name="购买药剂 · 20金币", exact=True).click()
        engine.buy_potion(d.game)
        expect(page.get_by_text(d.game["dialogue"]["text"], exact=True).last).to_be_visible()
        page.locator('[data-testid="stMain"]').evaluate("e=>e.scrollTo(0,0)")
        page.screenshot(path=str(ROOT / "artifacts/fogharbor-harbor.png"), full_page=True)
        d.walk((8, 7))
        assert d.game["map_id"] == "ruins"
        d.walk((3, 1))
        for foe, fragment in [((5, 1), (7, 1)), ((7, 3), (8, 4)), ((4, 5), (2, 7))]:
            d.walk(foe)
            page.screenshot(path=str(ROOT / "artifacts/fogharbor-combat.png"), full_page=True)
            d.fight()
            d.walk(fragment)
        assert d.game["inventory"]["fragment"] == 3
        d.walk((1, 6))
        d.walk((5, 6))
        d.walk((1, 1))
        d.walk((5, 2))
        d.interact("eve")
        assert d.game["side_quest"] == "complete"
        d.walk((6, 5))
        d.interact("fountain")
        d.walk((8, 7))
        d.walk((8, 7))
        assert d.game["combat"]["kind"] == "boss"
        d.fight()
        assert d.game["boss_defeated"]
        page.locator('[data-testid="stMain"]').evaluate("e=>e.scrollTo(0,0)")
        page.screenshot(path=str(ROOT / "artifacts/fogharbor-ruins.png"), full_page=True)
        d.walk((1, 1))
        d.walk((2, 2))
        d.interact("lorn")
        expect(page.get_by_text("灯塔已点亮 · 雾港重明", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="与洛恩交谈", exact=True)).not_to_be_visible()
        assert d.game["result"] == "victory"
        page.locator('[data-testid="stMain"]').evaluate("e=>e.scrollTo(0,0)")
        page.screenshot(path=str(ROOT / "artifacts/fogharbor-ending.png"), full_page=True)
        page.get_by_text("策划复盘 · 战斗、路径与AI", exact=True).click()
        page.get_by_role("button", name="生成系统优化建议", exact=True).click()
        expect(page.get_by_text("本局记录", exact=False).last).to_be_visible(timeout=15000)
        page.get_by_text("成就海报 · ComfyUI彩蛋", exact=True).click()
        page.get_by_role("button", name="生成守灯人成就海报", exact=True).click()
        expect(page.get_by_text("本地占位图 ·", exact=False)).to_be_visible(timeout=150000)
        page.get_by_role("button", name="重新开始", exact=True).click()
        expect(page.get_by_text("灯芯碎片 0 / 3", exact=True)).to_be_visible()
        page.set_viewport_size({"width": 430, "height": 932})
        expect(page.get_by_role("button", name="重新开始", exact=True)).to_be_visible()
        page.locator('[data-testid="stMain"]').evaluate("e=>e.scrollTo(0,0)")
        canvas = page.locator('canvas[aria-label="可点击的冒险地图"]')
        bounds = canvas.bounding_box()
        assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 431
        mobile = Driver(page)
        mobile.move(2, 4, method="canvas")
        page.screenshot(path=str(ROOT / "artifacts/fogharbor-mobile.png"), full_page=True)
        expect(page.locator('[data-testid="stSidebar"]')).to_have_attribute(
            "aria-expanded", "false"
        )
        assert not errors, errors
        print(
            f"Browser victory: {sum(row['event'] != 'arrival' for row in d.game['path']) - 1}"
            f" moves, {len(d.game['battle_log'])} rounds, side quest complete."
        )
        print(
            "Verified canvas, keyboard, NPCs, shop, map transitions, boss guard, "
            "ending, AI review, poster, restart."
        )
        browser.close()


if __name__ == "__main__":
    main()
