"""AI技术策划试炼场：session_state 驱动的一局完整策略试验。"""

import asyncio
import base64
import json

import pandas as pd
import streamlit as st

from frontend import api
from frontend.styles import CSS, section
from game.charts import dps_figure, dps_frame, heatmap_figure, hit_frame, map_figure
from game.engine import MAX_HP, MAX_MP, SKILLS, act, finish, move, new_game

st.set_page_config(page_title="AI技术策划试炼场", page_icon="🧭", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    """
<style>
.hero-title {font-size:30px;}
.arena-strip {display:flex; gap:10px; margin:20px 0 26px;}
.arena-strip span {padding:7px 15px; border:1px solid #d8ddd0; border-radius:7px;
  font-size:11px; color:#6d7e6b;}
.arena-strip .active {background:#216052; color:white; border-color:#216052;}
[data-testid="stMetricValue"] {font-size:1.5rem;}
[data-testid="stPlotlyChart"] {border-radius:12px; overflow:hidden;}
.block-container {padding-top:2rem;}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=10, show_spinner=False)
def connection_status(base_url: str) -> dict | None:
    try:
        return asyncio.run(api.request("GET", "/health", request_timeout=3))
    except api.APIError:
        return None


def initialize() -> None:
    if "arena" not in st.session_state:
        st.session_state.arena = new_game()
        st.session_state.run_id = 0
    defaults = {"start_hp": 100, "start_gold": 250, "map_seed": 42, "flash": ""}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def do_move(x: int, y: int) -> None:
    try:
        arena = st.session_state.arena
        move(arena, x, y)
        event = arena["path"][-1]["event"]
        st.session_state.flash = {
            "supply": "补给已使用：恢复 25 HP / 12 MP，上限内生效。",
            "trap": "触发陷阱：受到 8 点伤害，上限为剩余 HP。",
            "monster": "遭遇异兽！在右侧下方选择技能。",
            "move": f"抵达 ({x},{y})。",
        }[event]
    except ValueError as exc:
        st.session_state.flash = str(exc)


def select_map(chart_key: str) -> None:
    event = st.session_state[chart_key]
    points = event.selection.points
    if points and st.session_state.arena["phase"] == "EXPLORING":
        do_move(round(points[-1]["x"]), round(points[-1]["y"]))


def do_act(action: str) -> None:
    try:
        arena = st.session_state.arena
        kills = arena["kills"]
        act(arena, action)
        st.session_state.flash = (
            "异兽已击败，探索继续。击杀积分 +12 金币。"
            if arena["kills"] > kills
            else "本回合已结算。"
        )
    except ValueError as exc:
        st.session_state.flash = str(exc)


def reset_game() -> None:
    st.session_state.arena = new_game(
        hp_ratio=st.session_state.start_hp,
        gold=st.session_state.start_gold,
        seed=int(st.session_state.map_seed),
    )
    st.session_state.run_id += 1
    st.session_state.flash = ""


def post(path: str, payload: dict, message: str, timeout: float) -> dict | None:
    try:
        with st.spinner(message, show_time=True):
            return asyncio.run(api.request("POST", path, payload, request_timeout=timeout))
    except api.APIError as exc:
        st.error(str(exc))
        return None


def request_review(arena: dict, timeout: float) -> None:
    payload = {
        key: arena[key] for key in ("battle_log", "path", "hit_points", "dps_samples", "result")
    }
    payload["mode"] = arena["mode"]
    arena["review_attempted"] = True
    result = post("/api/arena/review", payload, "正在分析战斗与路线…", timeout)
    if result:
        arena["review"] = result["review"]


initialize()
health = connection_status(api.BACKEND_URL)
arena = st.session_state.arena
player = arena["player"]
phase = arena["phase"]
phase_labels = {"SETUP": "准备", "EXPLORING": "探索", "COMBAT": "战斗", "RESULT": "结算"}
strip = "".join(
    f'<span class="{"active" if key == phase else ""}">{index:02d} · {label}</span>'
    for index, (key, label) in enumerate(phase_labels.items(), 1)
)
st.markdown(
    '<div class="masthead"><div class="wordmark">design arena'
    "<span>TECHNICAL DESIGN LAB</span></div>"
    '<div class="mastnote">10 × 10 &nbsp; / &nbsp; STRATEGY SANDBOX</div></div>'
    '<div class="eyebrow">AI × SYSTEMS DESIGN</div>'
    '<div class="hero-title">AI技术策划试炼场</div>'
    '<div class="hero-subtitle">从一个动态任务出发，让战斗数值与关卡路线接受同一次实战检验。</div>'
    f'<div class="arena-strip">{strip}</div>',
    unsafe_allow_html=True,
)
if st.session_state.flash:
    # 页面内提示在重绘后仍可读，避免瞬时 toast 丢失或与主内容重复。
    st.caption(st.session_state.flash)
    st.session_state.flash = ""

left, middle, right = st.columns([0.92, 1.5, 1.2], gap="large")
timeout = (health or {}).get("deepseek_timeout", 60) + 15
active = phase in {"EXPLORING", "COMBAT"}

with left:
    st.markdown(
        section("01 / PLAYER & QUEST", "角色与任务", "设置起点，给这一局一个目标。"),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        a, b = st.columns(2)
        a.metric("HP", f"{player['hp']} / {MAX_HP}")
        b.metric("MP", f"{player['mp']} / {MAX_MP}")
        st.progress(player["hp"] / MAX_HP, text="生命状态")
        a, b = st.columns(2)
        a.metric("ATK", player["atk"])
        b.metric("金币", player["gold"])
        st.caption(f"位置 ({player['x']},{player['y']}) · 已清除 {arena['kills']} / 6 只异兽")
    with st.expander("开局状态", expanded=phase == "SETUP"):
        st.slider("开局血量比例", 0, 100, key="start_hp", format="%d%%", disabled=active)
        st.number_input(
            "开局金币", min_value=0, max_value=1_000_000, step=50, key="start_gold", disabled=active
        )
        st.number_input(
            "地图随机种子", min_value=0, max_value=999999, step=1, key="map_seed", disabled=active
        )
        st.caption("HP上限100 · MP40 · ATK20。相同种子生成相同布局。")
    offline = st.toggle(
        "离线演示",
        value=not bool(health and health.get("deepseek_configured")),
        key="offline_mode",
        disabled=active,
    )
    st.caption("本地任务与规则复盘" if offline else "DeepSeek 动态任务与系统复盘")
    if not health:
        st.warning("后端未连接。请运行 python run.py。")
        if st.button("重新连接", key="reconnect", width="stretch"):
            connection_status.clear()
            st.rerun()
    if st.button(
        "生成任务", type="primary", width="stretch", key="generate_quest", disabled=active
    ):
        result = post(
            "/api/arena/task",
            {
                "hp_ratio": st.session_state.start_hp,
                "gold": st.session_state.start_gold,
                "mode": "demo" if offline else "deepseek",
            },
            "正在根据玩家状态生成任务…",
            timeout,
        )
        if result:
            arena = new_game(
                result,
                hp_ratio=st.session_state.start_hp,
                gold=st.session_state.start_gold,
                seed=int(st.session_state.map_seed),
            )
            arena["mode"] = "demo" if offline else "deepseek"
            st.session_state.arena = arena
            st.session_state.run_id += 1
            st.rerun()
    if arena["task"]:
        task = arena["task"]
        with st.container(border=True):
            st.caption(
                "DYNAMIC QUEST / " + ("离线规则" if arena.get("mode") == "demo" else "DeepSeek")
            )
            st.subheader(task["name"])
            st.write(task["description"])
            st.progress(
                min(1.0, arena["kills"] / 6), text=f"目标 · 清除全部异兽 {arena['kills']} / 6"
            )
            reward = task["rewards"]
            st.caption(f"胜利奖励 · 金币 +{reward['gold']} / HP +{reward['hp']}")
            st.write("成就物品：", reward["item_name"])
            conditions = task["preconditions"]
            st.caption(f"前置 · HP ≥ {conditions['min_hp']}% / 金币 ≥ {conditions['min_gold']}")
            with st.expander("三条战术建议"):
                for branch in task["branches"]:
                    st.write(f"**{branch['title']}**")
                    st.caption(branch["description"])
                st.caption("建议供路线决策参考；奖励仅在胜利结算时发放。")
            with st.expander("任务 JSON"):
                st.json(task)
    else:
        st.info("生成任务后开启试炼。可先调整血量，比较低血量与满血的任务建议。")
    if active:
        st.button(
            "结束试验并结算",
            key="end_run",
            width="stretch",
            on_click=finish,
            args=(arena, "retreat"),
        )
    st.button("重置试炼", key="reset", width="stretch", on_click=reset_game)

with middle:
    st.markdown(
        section("02 / LEVEL", "网格关卡", "看清地形，规划你的下一步。"), unsafe_allow_html=True
    )
    st.caption("◆ 玩家  ·  △ 陷阱 1  ·  M 怪物 2  ·  ＋ 补给 3  ·  · 空地 0")
    chart_key = f"arena_map_{st.session_state.run_id}_{len(arena['path'])}_{phase}"
    st.plotly_chart(
        map_figure(arena),
        width="stretch",
        key=chart_key,
        on_select=lambda: select_map(chart_key),
        selection_mode="points",
        config={"displayModeBar": False},
    )
    st.caption("点击四方向相邻格移动，或使用下方方向按钮。线条记录已走路线。")
    controls = st.columns(4)
    for column, (name, dx, dy, key) in zip(
        controls,
        [
            ("↑ 上", 0, -1, "up"),
            ("← 左", -1, 0, "left"),
            ("↓ 下", 0, 1, "down"),
            ("→ 右", 1, 0, "right"),
        ],
        strict=True,
    ):
        x, y = player["x"] + dx, player["y"] + dy
        column.button(
            name,
            key=f"move_{key}",
            width="stretch",
            disabled=phase != "EXPLORING" or not (0 <= x < 10 and 0 <= y < 10),
            on_click=do_move,
            args=(x, y),
        )
    if phase == "COMBAT":
        st.warning("当前正处于战斗，击败异兽后恢复移动。")
    elif phase == "SETUP":
        st.caption("地图预览 · 尚未开始记录。出生点两侧保留补给，帮助低血量玩家起步。")
    stats = st.columns(3)
    stats[0].metric("移动步数", len(arena["path"]) - 1)
    stats[1].metric("受击次数", len(arena["hit_points"]))
    stats[2].metric("伤害总量", sum(hit["damage"] for hit in arena["hit_points"]))
    if phase == "RESULT":
        labels = {
            "victory": "试炼完成 · 任务奖励已发放",
            "defeat": "试炼失败 · HP 耗尽",
            "retreat": "试验结束 · 本局已保留",
        }
        st.subheader(labels[arena["result"]])
        st.plotly_chart(heatmap_figure(arena), width="stretch", key="hits")
        if not arena["hit_points"]:
            st.caption("本局没有受击，热力图为零；未走区域不代表没有风险。")
        else:
            st.caption("色阶表示受击次数；数值与战斗日志一起用于定位挫败来源。")
        st.download_button(
            "导出试炼 JSON",
            json.dumps(arena, ensure_ascii=False, indent=2),
            file_name="arena-run.json",
            mime="application/json",
            width="stretch",
        )
        st.download_button(
            "导出受击热力图 CSV",
            hit_frame(arena).to_csv().encode("utf-8-sig"),
            file_name="hit-heatmap.csv",
            mime="text/csv",
            width="stretch",
        )
    with st.expander("路线与地图数据"):
        st.dataframe(pd.DataFrame(arena["path"]), hide_index=True, width="stretch")
        st.dataframe(pd.DataFrame(arena["map"]), width="stretch")
    with st.expander("本局数值规则"):
        st.write("陷阱：8 HP；补给：25 HP / 12 MP。事件只触发一次。异兽 HP42–54 / ATK4–6。")
        st.write(
            "技能1：ATK×1.8，消耗12MP，冷却3个完整回合。技能2：ATK×0.7，免费，恢复8MP，冷却1回合。"
        )
        st.write("等待恢复3MP。每回合模拟2秒；敌人存活才反击。清除6个怪物后胜利。")
        st.caption("每局最多400步/200个战斗回合，达到后自动结束试验并保留数据。")

with right:
    st.markdown(
        section("03 / COMBAT & ANALYSIS", "战斗与复盘", "验证爆发、循环与关卡挫败感。"),
        unsafe_allow_html=True,
    )
    if phase == "COMBAT":
        combat = arena["combat"]
        with st.container(border=True):
            st.caption(f"ENCOUNTER {combat['battle_id']:02d}")
            st.subheader(combat["enemy_name"])
            st.progress(
                combat["hp"] / combat["max_hp"],
                text=f"敌人 HP {combat['hp']} / {combat['max_hp']} · ATK {combat['atk']}",
            )
            for action, skill in SKILLS.items():
                cooldown = combat["cooldowns"][action]
                reason = (
                    f"CD {cooldown} 回合"
                    if cooldown
                    else ("MP不足" if player["mp"] < skill["mana"] else "可施放")
                )
                st.button(
                    f"{skill['name']} · {reason}",
                    key=f"skill_{action}",
                    width="stretch",
                    type="primary" if action == "burst" else "secondary",
                    disabled=cooldown > 0 or player["mp"] < skill["mana"],
                    on_click=do_act,
                    args=(action,),
                )
                st.caption("36伤害 · 12MP · CD3" if action == "burst" else "14伤害 · 回8MP · CD1")
            st.button(
                "等待 / 回蓝 +3", key="skill_wait", width="stretch", on_click=do_act, args=("wait",)
            )
            st.caption("敌人会在存活的每个回合反击，包括等待回合。")
    elif phase != "RESULT":
        with st.container(border=True):
            st.subheader("等待下一场遭遇")
            st.caption("走进 M 怪物格，将在这里打开回合战斗面板。")
            st.write("破阵重击 · 高伤 / 长CD")
            st.write("潮汐回响 · 低伤 / 短CD / 回蓝")
    st.plotly_chart(dps_figure(arena), width="stretch", key="dps", config={"displayModeBar": False})
    if arena["dps_samples"]:
        frame = dps_frame(arena)
        metrics = st.columns(2)
        metrics[0].metric("爆发峰值", f"{frame.dps.max():.1f} DPS")
        metrics[1].metric("累计平均", f"{frame.damage.sum() / (len(frame) * 2):.1f} DPS")
        st.caption("实线为当前回合 DPS；虚线为本场平均，换敌人时重算。灰区为技能都不可用的回合。")
    else:
        st.caption("进入战斗后记录伤害曲线。每回合2秒，操作停顿不计入 DPS。")
    with st.expander("战斗日志", expanded=phase == "COMBAT"):
        if arena["battle_log"]:
            st.dataframe(
                pd.DataFrame(arena["battle_log"]).tail(12), hide_index=True, width="stretch"
            )
        else:
            st.caption("还没有战斗记录。")
    if phase == "RESULT":
        st.divider()
        st.subheader("系统优化建议")
        st.caption("离线规则复盘" if arena.get("mode") == "demo" else "DeepSeek 复盘")
        if not arena["review_attempted"]:
            request_review(arena, timeout)
        if arena["review"]:
            st.write(arena["review"])
            st.caption(f"{len(arena['review'])} / 200 字")
        elif st.button("重试 AI 复盘", key="retry_review", width="stretch"):
            request_review(arena, timeout)
            st.rerun()
        st.subheader("成就海报")
        st.caption("结算纪念图 · 物品奖励在任务胜利时解锁。")
        if st.button("生成成就海报", key="poster", width="stretch"):
            result = post(
                "/api/arena/poster",
                arena["task"]["rewards"],
                "正在制作成就海报…",
                (health or {}).get("comfyui_timeout", 120) + 15,
            )
            if result:
                arena["poster"] = result
        if arena["poster"]:
            poster = arena["poster"]
            st.image(base64.b64decode(poster["image_base64"]), width="stretch")
            if poster["source"] == "placeholder":
                st.caption("占位图 · " + poster["notice"])
            else:
                st.caption("ComfyUI 生成 · " + poster["item_name"])
            st.download_button(
                "下载海报",
                base64.b64decode(poster["image_base64"]),
                file_name="achievement.png",
                mime=poster["mime_type"],
                width="stretch",
            )
        st.download_button(
            "导出 DPS CSV",
            dps_frame(arena).to_csv(index=False).encode("utf-8-sig"),
            file_name="dps.csv",
            mime="text/csv",
            width="stretch",
        )

st.markdown(
    '<div class="footer">AI TECHNICAL DESIGN ARENA &nbsp; / &nbsp; '
    "任务 → 路线 → 战斗 → 数据 → 复盘</div>",
    unsafe_allow_html=True,
)
