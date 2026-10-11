"""实际浏览器的一局验证。先运行 run.py，再用 Python 执行此脚本。"""

import heapq
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from game.engine import new_game
from runtime_paths import configure_local_paths

ROOT = Path(__file__).resolve().parents[1]


def route(grid, start, target):
    # 以地图公开信息规划测试路线：陷阱增加代价，不跨过非目标怪物。
    queue = [(0, start, [])]
    seen = set()
    while queue:
        cost, pos, steps = heapq.heappop(queue)
        if pos == target:
            return steps
        if pos in seen:
            continue
        seen.add(pos)
        for dx, dy in ((0, -1), (-1, 0), (0, 1), (1, 0)):
            p = (pos[0] + dx, pos[1] + dy)
            if not (0 <= p[0] < 10 and 0 <= p[1] < 10):
                continue
            if grid[p[1]][p[0]] == 2 and p != target:
                continue
            weight = 10 if grid[p[1]][p[0]] == 1 else 1
            heapq.heappush(queue, (cost + weight, p, steps + [p]))
    raise AssertionError("路线不可达")


def main():
    configure_local_paths()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(
            os.getenv("FOGHARBOR_TEST_URL", "http://127.0.0.1:8501"), wait_until="domcontentloaded"
        )
        page.locator('[data-testid="stExpandSidebarButton"]').click()
        expect(page.locator('[data-testid="stSidebar"]')).to_have_attribute("aria-expanded", "true")
        page.get_by_text("策划试炼场", exact=True).click()
        expect(page.get_by_role("button", name="生成任务", exact=True)).to_be_visible()
        page.screenshot(path=str(ROOT / "artifacts/arena-setup.png"), full_page=True)
        page.get_by_role("button", name="生成任务", exact=True).click()
        expect(page.get_by_text("雾港六枚兽印", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="→ 右", exact=True)).to_be_enabled()

        def map_click(x, y):
            chart = page.locator(".js-plotly-plot").first
            position = chart.evaluate(
                """(el, p) => {
                const rect = el.getBoundingClientRect();
                const xa = el._fullLayout.xaxis, ya = el._fullLayout.yaxis;
                return {x: rect.left + xa._offset + xa.l2p(p[0]),
                        y: rect.top + ya._offset + ya.l2p(p[1])};
            }""",
                [x, y],
            )
            page.mouse.click(position["x"], position["y"])

        def current_position():
            return page.locator(".js-plotly-plot").first.evaluate("""el => {
                const trace = el.data[el.data.length-1];
                return [trace.x[0], trace.y[0]];
            }""")

        # 真正点选 Plotly，而不是绕过页面直接调用引擎。
        map_click(1, 0)
        expect(page.get_by_text("位置 (1,0) · 已清除 0 / 6 只异兽", exact=True)).to_be_visible()
        map_click(4, 4)
        expect(page.get_by_text("只能移动到相邻格", exact=True)).to_be_visible()
        assert current_position() == [1, 0]
        grid = new_game(seed=42)["map"]
        pos = (1, 0)
        grid[0][1] = 0
        targets = [
            (x, y) for y, row in enumerate(grid) for x, value in enumerate(row) if value == 2
        ]
        for index, target in enumerate(targets, 1):
            for nxt in route(grid, pos, target):
                delta = (nxt[0] - pos[0], nxt[1] - pos[1])
                label = {(1, 0): "→ 右", (-1, 0): "← 左", (0, 1): "↓ 下", (0, -1): "↑ 上"}[delta]
                page.get_by_role("button", name=label, exact=True).click()
                expect(
                    page.get_by_text(
                        f"位置 ({nxt[0]},{nxt[1]}) · 已清除 {index - 1} / 6 只异兽",
                        exact=True,
                    )
                ).to_be_visible()
                pos = nxt
            expect(
                page.get_by_text(f"坐标异兽 ({target[0]},{target[1]})", exact=True)
            ).to_be_visible()
            page.locator('[data-testid="stMain"]').evaluate("el => el.scrollTo(0,0)")
            page.screenshot(path=str(ROOT / "artifacts/arena-combat.png"), full_page=True)
            for _ in range(20):
                if page.get_by_role("button", name="技能1 · 破阵重击", exact=False).count() == 0:
                    break
                burst = page.get_by_role("button", name="技能1 · 破阵重击", exact=False)
                flow = page.get_by_role("button", name="技能2 · 潮汐回响", exact=False)
                if burst.is_enabled():
                    burst.click()
                elif flow.is_enabled():
                    flow.click()
                else:
                    page.get_by_role("button", name="等待 / 回蓝 +3", exact=True).click()
                page.wait_for_timeout(300)
            expect(
                page.get_by_text(
                    f"位置 ({pos[0]},{pos[1]}) · 已清除 {index} / 6 只异兽",
                    exact=True,
                )
            ).to_be_visible()
            grid[target[1]][target[0]] = 0
        expect(page.get_by_text("试炼完成 · 任务奖励已发放", exact=True)).to_be_visible()
        expect(page.get_by_text("系统优化建议", exact=True)).to_be_visible()
        expect(page.get_by_text("金币", exact=True).first).to_be_visible()
        expect(page.get_by_text("/ 200 字", exact=False)).to_be_visible(timeout=20000)
        page.screenshot(path=str(ROOT / "artifacts/arena-result.png"), full_page=True)
        page.get_by_role("button", name="生成成就海报", exact=True).click()
        expect(page.get_by_text("占位图 ·", exact=False)).to_be_visible(timeout=150000)
        page.screenshot(path=str(ROOT / "artifacts/arena-poster.png"), full_page=True)
        page.get_by_role("button", name="重置试炼", exact=True).click()
        expect(page.get_by_role("button", name="生成任务", exact=True)).to_be_enabled()
        expect(page.get_by_role("button", name="→ 右", exact=True)).to_be_disabled()
        page.set_viewport_size({"width": 430, "height": 932})
        page.screenshot(path=str(ROOT / "artifacts/arena-mobile.png"), full_page=True)
        assert not errors, errors
        assert page.locator('[data-testid="stException"]').count() == 0
        print(
            "Browser verified: Plotly click, invalid movement, six combats, "
            "victory, review, poster, reset."
        )
        browser.close()


if __name__ == "__main__":
    main()
