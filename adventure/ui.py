"""剧情界面：真实像素场景、鼠标/键盘交互、NPC与战斗共享session_state。"""

import asyncio
import base64
import html
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v2 as components

from adventure import engine
from adventure.art import battle_scene, data_url, portrait, scene, title_art
from adventure.content import ENDING, INTRO, MAPS, QUESTS, REWARD
from adventure.styles import CSS
from adventure.telemetry import review_payload
from frontend import api
from game.charts import dps_figure, dps_frame, heatmap_figure, hit_frame

HERE = Path(__file__).resolve().parent
BOARD_ARGS = dict(
    html='<div class="game-board" tabindex="0" role="application" aria-label="像素地图">'
    '<canvas width="640" height="640" aria-label="可点击的冒险地图"></canvas>'
    '<div class="board-hint"></div></div>',
    css=(HERE / "board.css").read_text(encoding="utf-8"),
    js=(HERE / "board.js").read_text(encoding="utf-8"),
)


def perform(action: str, *args) -> None:
    game = st.session_state.adventure
    try:
        {
            "move": engine.move,
            "act": engine.act,
            "interact": engine.interact,
            "buy": engine.buy_potion,
            "potion": engine.use_potion,
        }[action](game, *args)
        st.session_state.game_notice = ""
    except ValueError as exc:
        st.session_state.game_notice = str(exc)
        # 错误动作不推进游戏回合；版本号仅刷新客户端输入锁。
        game["revision"] += 1


def board_event() -> None:
    state = st.session_state.get("adventure_canvas")
    event = state.get("action") if isinstance(state, dict) else getattr(state, "action", None)
    if not event or event.get("revision") != st.session_state.adventure["revision"]:
        return
    if event["type"] == "move":
        perform("move", int(event["x"]), int(event["y"]))
    elif event["type"] == "interact":
        perform("interact", event["id"])
    elif event["type"] == "act":
        perform("act", event["action"])


def start() -> None:
    st.session_state.adventure = engine.new_game()
    st.session_state.game_started = True
    st.session_state.game_notice = ""


def _post(path: str, payload: dict, message: str, timeout: float = 190) -> dict | None:
    try:
        with st.spinner(message, show_time=True):
            return asyncio.run(api.request("POST", path, payload, request_timeout=timeout))
    except api.APIError as exc:
        st.error(str(exc))
        return None


def render_review(game: dict) -> None:
    with st.expander("策划复盘 · 战斗、路径与AI"):
        st.plotly_chart(dps_figure(game), width="stretch", key="story_dps")
        map_id = st.selectbox(
            "查看关卡受击分布", list(MAPS), format_func=lambda k: MAPS[k]["name"], key="hit_map"
        )
        filtered = {"hit_points": [h for h in game["hit_points"] if h["map_id"] == map_id]}
        st.plotly_chart(heatmap_figure(filtered), width="stretch", key="story_heatmap")
        mode = st.toggle("使用 DeepSeek 复盘", value=False, key="story_ai")
        st.caption("默认规则复盘无需Key。开启后发送本局战斗日志与路径；主线和数值不受AI改写。")
        if st.button("生成系统优化建议", key="story_review", width="stretch"):
            payload = review_payload(game, "deepseek" if mode else "demo")
            if payload["summary"]["sampled"]:
                st.caption("长局日志已均匀取样，并附完整计数；图表与导出仍保留全部记录。")
            result = _post("/api/arena/review", payload, "正在复盘这场冒险…")
            if result:
                game["review"] = result["review"]
        if game["review"]:
            st.write(game["review"])
        st.download_button(
            "导出本局记录",
            json.dumps(game, ensure_ascii=False, indent=2),
            file_name="fogharbor-run.json",
            mime="application/json",
            width="stretch",
        )
        st.download_button(
            "导出DPS数据",
            dps_frame(game).to_csv(index=False).encode("utf-8-sig"),
            file_name="fogharbor-dps.csv",
            mime="text/csv",
            width="stretch",
        )
        st.download_button(
            "导出热力图",
            hit_frame(filtered).to_csv().encode("utf-8-sig"),
            file_name="fogharbor-hits.csv",
            mime="text/csv",
            width="stretch",
        )
    with st.expander("成就海报 · ComfyUI彩蛋"):
        if st.button("生成守灯人成就海报", key="story_poster", width="stretch"):
            result = _post("/api/arena/poster", REWARD, "正在制作海报…")
            if result:
                game["poster"] = result
        if game["poster"]:
            result = game["poster"]
            data = base64.b64decode(result["image_base64"])
            st.image(data, width="stretch")
            st.caption(
                "ComfyUI生成"
                if result["source"] == "comfyui"
                else "本地占位图 · " + result["notice"]
            )
            st.download_button(
                "下载海报",
                data,
                file_name="keeper-poster.png",
                mime=result["mime_type"],
                width="stretch",
            )


def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="game-mast"><span class="game-brand">FOGHARBOR</span>'
        '<span class="game-tag">A SMALL PIXEL ADVENTURE / 雾港守灯人</span></div>',
        unsafe_allow_html=True,
    )
    if "adventure" not in st.session_state:
        st.session_state.adventure = engine.new_game()
        st.session_state.game_started = False
        st.session_state.game_notice = ""
    if not st.session_state.game_started:
        a, b = st.columns([1.1, 1], gap="large")
        with a:
            st.caption("一盏灯，一座港，一条回家的路。")
            st.title("雾港守灯人")
            st.write(INTRO)
            st.image(portrait("hero", 120), caption="莉亚 · 见习守灯人", width=120)
            st.write(
                "探索两张地图，与守灯人和药师交谈。找回三枚灯芯，击败熄灯者，让归航的船再次看见灯光。"
            )
            st.button(
                "开始冒险", key="story_start", type="primary", width="stretch", on_click=start
            )
            st.caption("回合制像素冒险 · 约5–10分钟 · 无需API Key即可通关")
            with st.expander("操作说明"):
                st.write("点击相邻格，或点击地图后使用方向键/WASD。E与身边角色互动。")
                st.write("战斗中可用1重击、2回响、3防御、4药剂、5等待，也可点击动作按钮。")
        with b:
            st.image(title_art(), width="stretch")
        st.markdown(
            '<div class="game-footer">像素素材：Kenney · Tiny Dungeon · CC0。'
            "剧情、地图与角色设定为本项目创作。</div>",
            unsafe_allow_html=True,
        )
        return

    game = st.session_state.adventure
    p = game["player"]
    world = MAPS[game["map_id"]]
    left, middle, right = st.columns([0.82, 1.65, 1.03], gap="large")
    with left:
        st.markdown('<div class="game-section">01 / THE KEEPER</div>', unsafe_allow_html=True)
        with st.container(border=True):
            a, b = st.columns([1, 1.6])
            a.image(portrait("hero"), width=72)
            b.subheader("莉亚")
            b.caption("见习守灯人")
            st.progress(p["hp"] / 100, text=f"生命 {p['hp']} / 100")
            st.progress(p["mp"] / 40, text=f"魔力 {p['mp']} / 40")
            a, b = st.columns(2)
            a.metric("金币", p["gold"])
            b.metric("攻击", p["atk"])
        title, objective = QUESTS[game["quest_stage"]]
        st.markdown(
            f'<div class="quest-card"><strong>{html.escape(title)}</strong>'
            f"<p>{html.escape(objective)}</p></div>",
            unsafe_allow_html=True,
        )
        st.progress(
            game["inventory"]["fragment"] / 3, text=f"灯芯碎片 {game['inventory']['fragment']} / 3"
        )
        if game["side_quest"] != "none":
            st.caption(
                "支线 · 月露草："
                + ("已完成" if game["side_quest"] == "complete" else "交给艾芙可得2瓶药剂")
            )
        with st.container(border=True):
            st.write("**行囊**")
            st.write(f"药剂 × {game['inventory']['potion']} · 月露草 × {game['inventory']['herb']}")
            st.caption("药剂恢复35HP / 6MP，战斗中使用消耗一回合。")
            st.button(
                "使用药剂",
                key="story_use_potion",
                width="stretch",
                disabled=game["phase"] == "RESULT" or game["inventory"]["potion"] == 0,
                on_click=perform,
                args=("potion",),
            )
        with st.expander("旅途手记"):
            for text in reversed(game["journal"][-8:]):
                st.caption(text)
        st.button("重新开始", key="story_restart", width="stretch", on_click=start)

    with middle:
        st.markdown('<div class="game-section">02 / THE JOURNEY</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="game-title">{world["name"]}</div>'
            f'<div class="game-intro">{world["subtitle"]}</div>',
            unsafe_allow_html=True,
        )
        nearby = engine.interactions(game)
        neighbors = []
        for dx, dy in ((0, -1), (-1, 0), (0, 1), (1, 0)):
            x, y = p["x"] + dx, p["y"] + dy
            if 0 <= x < 10 and 0 <= y < 10 and world["tiles"][y][x] != "#":
                e = engine.entity_at(game, x, y)
                if not e or e["kind"] != "npc":
                    neighbors.append([x, y])
        # 每个Streamlit运行时注册同一份声明，独立测试/服务重启不会引用旧registry。
        board = components.component("fogharbor_board", **BOARD_ARGS)
        board(
            key="adventure_canvas",
            data={
                "image": data_url(scene(game)),
                "phase": game["phase"],
                "x": p["x"],
                "y": p["y"],
                "revision": game["revision"],
                "neighbors": neighbors,
                "interaction": nearby[0]["id"] if nearby else "",
            },
            on_action_change=board_event,
        )
        with st.container(key="story_direction_buttons"):
            controls = st.columns(4)
            for col, (label, dx, dy, key) in zip(
                controls,
                [
                    ("↑ 上", 0, -1, "up"),
                    ("← 左", -1, 0, "left"),
                    ("↓ 下", 0, 1, "down"),
                    ("→ 右", 1, 0, "right"),
                ],
                strict=True,
            ):
                target = [p["x"] + dx, p["y"] + dy]
                col.button(
                    label,
                    key="story_move_" + key,
                    width="stretch",
                    disabled=game["phase"] != "EXPLORING" or target not in neighbors,
                    on_click=perform,
                    args=("move", *target),
                )
        st.caption(
            f"莉亚位置 ({p['x']},{p['y']}) · 移动 "
            f"{sum(row['event'] != 'arrival' for row in game['path']) - 1} 步"
            f" · 击败 {game['kills']} 个敌人"
        )
        if st.session_state.game_notice:
            st.warning(st.session_state.game_notice)
        if game["phase"] == "RESULT":
            if game["result"] == "victory":
                st.success("灯塔已点亮 · 雾港重明")
                st.subheader("所有人都有回家的方向")
                st.write(ENDING)
                st.caption("获得守灯人徽章与80金币。")
            else:
                st.error("冒险结束 · 莉亚倒在了迷雾中")
                st.write("带足药剂，遇到蓄力就防御。避风泉可以免费恢复生命与魔力。")
            render_review(game)

    with right:
        st.markdown(
            '<div class="game-section">03 / VOICES IN THE FOG</div>', unsafe_allow_html=True
        )
        dialogue = game["dialogue"]
        with st.container(border=True):
            st.image(portrait(dialogue["portrait"], 72), width=72)
            st.markdown(
                f'<div class="speaker">{html.escape(dialogue["speaker"])}</div>',
                unsafe_allow_html=True,
            )
            st.write(dialogue["text"])
        if game["phase"] == "COMBAT":
            c = game["combat"]
            st.subheader(c["name"])
            st.image(battle_scene(game), width="stretch")
            st.progress(c["hp"] / c["max_hp"], text=f"敌人生命 {c['hp']} / {c['max_hp']}")
            if c["charged"]:
                st.warning("首领蓄力中：下回合重击18伤害。防御可降至6。")
            for key, label, caption in [
                ("burst", "破阵重击", "36伤害 · 消耗12MP · 冷却3回合"),
                ("flow", "潮汐回响", "14伤害 · 回8MP · 冷却1回合"),
            ]:
                cd = c["cooldowns"][key]
                st.button(
                    label + (f" · CD{cd}" if cd else ""),
                    key="story_skill_" + key,
                    type="primary" if key == "burst" else "secondary",
                    width="stretch",
                    disabled=cd > 0 or (key == "burst" and p["mp"] < 12),
                    on_click=perform,
                    args=("act", key),
                )
                st.caption(caption)
            st.button(
                "防御 · 减伤 / 回4MP",
                key="story_guard",
                width="stretch",
                on_click=perform,
                args=("act", "guard"),
            )
            st.button(
                "等待 · 回3MP",
                key="story_wait",
                width="stretch",
                on_click=perform,
                args=("act", "wait"),
            )
            st.caption("敌人存活才反击。战斗中无法移动，击杀回合无反击。")
        elif game["phase"] == "EXPLORING":
            for e in nearby:
                label = (
                    "在避风泉休息"
                    if e["kind"] == "rest"
                    else ("查看灯芯" if e["kind"] == "beacon" else "与" + e["name"] + "交谈")
                )
                st.button(
                    label,
                    key="story_interact_" + e["id"],
                    width="stretch",
                    on_click=perform,
                    args=("interact", e["id"]),
                )
                if e["id"] == "eve":
                    st.button(
                        "购买药剂 · 20金币",
                        key="story_buy",
                        width="stretch",
                        disabled=p["gold"] < 20,
                        on_click=perform,
                        args=("buy",),
                    )
            if not nearby:
                st.caption("走到洛恩或艾芙旁边交谈。踩上箱子或物品即可拾取。石墙不可穿越。")
            with st.expander("地点与角色"):
                for e in engine.entities(game):
                    if e["kind"] in {"npc", "exit", "fragment", "boss"}:
                        st.caption(f"{e['name']} · ({e['x']},{e['y']})")
        if game["battle_log"]:
            with st.expander("最近的战斗记录"):
                st.dataframe(pd.DataFrame(game["battle_log"]).tail(5), hide_index=True)

    st.markdown(
        '<div class="game-footer">美术素材 Kenney · Tiny Dungeon · CC0'
        " &nbsp; / &nbsp; 原创剧情与关卡 · Python × Streamlit</div>",
        unsafe_allow_html=True,
    )
