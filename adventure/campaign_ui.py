# ruff: noqa: E501

"""大型 2D 远征的 Streamlit 界面。

规则完全由 :mod:`adventure.campaign` 驱动；本文件只负责输入、可视化和可选
AI 服务调用。这样技能伤害、路线锁定、存档和结局不会因为重绘页面而分叉。
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from adventure import campaign, campaign_art
from adventure.styles import CSS
from backend.poster import placeholder_poster
from frontend import api

EXTRA_CSS = """
<style>
.campaign-hero {display:flex; justify-content:space-between; align-items:end;
 border-bottom:1px solid #35414a; padding-bottom:16px; margin-bottom:20px;}
.campaign-brand {font-family:Georgia,serif; color:#f0d39a; font-size:27px;}
.campaign-kicker {font-size:10px; letter-spacing:2px; color:#7e9ba0;}
.campaign-title {font-size:30px; color:#f1dfb9; margin-top:5px; font-weight:650;}
.campaign-subtitle {color:#abb9b7; font-size:13px; margin-top:5px;}
.campaign-phase {color:#e0bb70; font-size:11px; letter-spacing:1px; text-transform:uppercase;}
.campaign-message {border-left:3px solid #d4af67; padding:9px 12px; background:#202f34;
 color:#e9dfca; border-radius:4px; margin:10px 0 14px;}
.campaign-grid button {min-height:2.15rem!important; padding:0!important; font-size:1.15rem!important;
 line-height:1!important; border-radius:4px!important;}
.campaign-grid [data-testid="stHorizontalBlock"] {gap:3px!important;}
.campaign-map-frame, .st-key-campaign_map_frame {border:1px solid #465961; border-radius:8px; padding:7px;
 background:#101a22; box-shadow:0 8px 24px rgba(0,0,0,.2);}
.campaign-legend {display:flex; flex-wrap:wrap; gap:8px 14px; margin:8px 0 10px;
 color:#abb9b7; font-size:11px;}
.campaign-legend span {white-space:nowrap;}
.campaign-legend i {display:inline-block; width:9px; height:9px; margin-right:4px;
 border-radius:2px; vertical-align:-1px;}
.campaign-art-caption {font-size:11px; color:#8ea6a7; margin:4px 0 8px;}
.campaign-empty-chart {border:1px solid #35414a; border-radius:7px; padding:24px 12px;
 text-align:center; color:#8ea6a7; background:#18242b; margin:4px 0 12px;}
.fx-banner {padding:14px; border:1px solid #dfb65d; color:#f8dc99; background:#2f3540;
 animation:fxPulse .9s ease-out; border-radius:7px; text-align:center; margin-bottom:12px;}
@keyframes fxPulse {0% {transform:scale(.96); box-shadow:0 0 0 #dfb65d; opacity:.35;}
 45% {transform:scale(1.02); box-shadow:0 0 24px #dfb65d; opacity:1;} 100% {transform:scale(1);}}
.route-card {padding:8px 10px; border-left:3px solid #d4af67; background:#202f34; margin:6px 0;}
.campaign-footer {border-top:1px solid #35414a; padding-top:14px; margin-top:22px; color:#8aa0a4; font-size:11px;}
</style>
"""


PHASE_LABELS = {
    "EXPLORING": "探索",
    "COMBAT": "战斗",
    "ROUTE_CHOICE": "路线选择",
    "RESULT": "结算",
}


def _initialize() -> None:
    if "campaign_game" not in st.session_state:
        st.session_state.campaign_game = campaign.new_game()
    st.session_state.setdefault("campaign_notice", "")
    st.session_state.setdefault("campaign_slot", 1)
    st.session_state.setdefault("campaign_review", "")
    st.session_state.setdefault("campaign_poster", None)


def _notice(message: str) -> None:
    st.session_state.campaign_notice = message


def _move(x: int, y: int) -> None:
    game = st.session_state.campaign_game
    try:
        campaign.move(game, x, y)
        _notice(game["last_message"])
    except ValueError as exc:
        _notice(str(exc))


def _act(skill_id: str) -> None:
    game = st.session_state.campaign_game
    try:
        campaign.act(game, skill_id)
        _notice(game["last_message"])
    except ValueError as exc:
        _notice(str(exc))


def _choose_route(route_id: str) -> None:
    game = st.session_state.campaign_game
    try:
        campaign.choose_route(game, route_id)
        _notice(game["last_message"])
    except ValueError as exc:
        _notice(str(exc))


def _equip(skill_id: str, slot: int) -> None:
    game = st.session_state.campaign_game
    try:
        campaign.equip_skill(game, skill_id, slot)
        _notice(game["last_message"])
    except ValueError as exc:
        _notice(str(exc))


def _restart() -> None:
    st.session_state.campaign_game = campaign.new_game()
    st.session_state.campaign_review = ""
    st.session_state.campaign_poster = None
    _notice("新的远征已经开始。")


def _save() -> None:
    try:
        path = campaign.save_game(
            st.session_state.campaign_game, int(st.session_state.campaign_slot)
        )
        _notice(f"已保存到存档位 {st.session_state.campaign_slot}：{path.name}。")
    except (OSError, ValueError) as exc:
        _notice(str(exc))


def _load() -> None:
    try:
        st.session_state.campaign_game = campaign.load_game(int(st.session_state.campaign_slot))
        st.session_state.campaign_review = ""
        st.session_state.campaign_poster = st.session_state.campaign_game.get("poster")
        _notice(f"已载入存档位 {st.session_state.campaign_slot}。")
    except (OSError, ValueError, FileNotFoundError) as exc:
        _notice(str(exc))


def _post(path: str, payload: dict[str, Any], timeout: float = 190) -> dict[str, Any] | None:
    try:
        return asyncio.run(api.request("POST", path, payload, request_timeout=timeout))
    except api.APIError as exc:
        _notice(str(exc))
        return None


def _dps_frame(game: dict[str, Any]) -> pd.DataFrame:
    rows = game.get("dps_samples", [])
    if not rows:
        return pd.DataFrame(columns=["elapsed", "dps", "damage", "action", "vacuum", "avg_dps"])
    frame = pd.DataFrame(rows)
    frame["avg_dps"] = frame["dps"].expanding().mean()
    return frame


def _dps_figure(game: dict[str, Any]) -> go.Figure:
    frame = _dps_frame(game)
    fig = go.Figure()
    if not frame.empty:
        fig.add_trace(
            go.Scatter(x=frame["elapsed"], y=frame["dps"], mode="lines+markers", name="瞬时 DPS")
        )
        fig.add_trace(
            go.Scatter(
                x=frame["elapsed"],
                y=frame["avg_dps"],
                mode="lines",
                name="平均 DPS",
                line={"dash": "dot"},
            )
        )
        peak = frame.loc[frame["dps"].idxmax()]
        fig.add_trace(
            go.Scatter(
                x=[peak["elapsed"]],
                y=[peak["dps"]],
                mode="markers+text",
                text=["爆发峰值"],
                textposition="top center",
                name="峰值",
                marker={"color": "#e1b765", "size": 11},
            )
        )
        for row in frame[frame["vacuum"]].itertuples():
            fig.add_vrect(
                x0=float(row.elapsed) - 1.5,
                x1=float(row.elapsed),
                fillcolor="#879699",
                opacity=0.18,
                line_width=0,
            )
    fig.update_layout(
        height=265,
        margin={"l": 5, "r": 5, "t": 28, "b": 5},
        title="DPS 实时曲线",
        xaxis_title="战斗秒数",
        yaxis_title="伤害 / 秒",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#18242b",
        legend={"orientation": "h", "y": -0.25},
    )
    if frame.empty:
        fig.add_annotation(
            text="等待第一次战斗数据",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"color": "#8ea6a7", "size": 13},
        )
    return fig


def _heatmap_figure(game: dict[str, Any]) -> go.Figure:
    frame = pd.DataFrame(0, index=range(campaign.HEIGHT), columns=range(campaign.WIDTH), dtype=int)
    for hit in game.get("hit_points", []):
        frame.loc[int(hit["y"]), int(hit["x"])] += 1
    fig = go.Figure(
        go.Heatmap(
            z=frame.values,
            x=frame.columns,
            y=frame.index,
            colorscale="YlOrRd",
            zmin=0,
            zmax=max(1, int(frame.values.max())),
            colorbar={"title": "受击"},
            hovertemplate="(%{x},%{y})<br>受击 %{z} 次<extra></extra>",
        )
    )
    fig.update_layout(
        height=280,
        margin={"l": 5, "r": 5, "t": 28, "b": 5},
        title="受击热力图",
        yaxis={"autorange": "reversed"},
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _tile(game: dict[str, Any], x: int, y: int) -> tuple[str, str, bool]:
    level = game["level"]
    if level["tiles"][y][x] == "#":
        return "■", "墙体", True
    player = game["player"]
    if (x, y) == (player["x"], player["y"]):
        return "◆", "莉亚", False
    enemy = next(
        (e for e in level["enemies"] if not e.get("defeated") and (e["x"], e["y"]) == (x, y)), None
    )
    if enemy:
        return "M", enemy["name"], False
    if any((item["x"], item["y"]) == (x, y) for item in level["traps"]):
        return "△", "陷阱", False
    if any((item["x"], item["y"]) == (x, y) for item in level["supplies"]):
        return "＋", "潮光补给", False
    book = level["book"]
    if not book["claimed"] and (x, y) == (book["x"], book["y"]):
        return "✦", SKILL_BOOKS_NAME(book["id"]), False
    exit_cell = level["exit"]
    if (x, y) == (exit_cell["x"], exit_cell["y"]):
        return "◎", "出口", False
    return "·", "可行走", False


def SKILL_BOOKS_NAME(skill_id: str) -> str:
    return campaign.SKILL_BOOKS[skill_id]["name"]


def _render_grid(game: dict[str, Any]) -> None:
    player = game["player"]
    with st.container(key="campaign_grid"):
        for y in range(campaign.HEIGHT):
            columns = st.columns(campaign.WIDTH, gap="small")
            for x, column in enumerate(columns):
                label, help_text, blocked = _tile(game, x, y)
                adjacent = abs(x - player["x"]) + abs(y - player["y"]) == 1
                column.button(
                    label,
                    key=f"campaign_cell_{game['revision']}_{x}_{y}",
                    width="stretch",
                    help=f"{help_text} · ({x},{y})",
                    disabled=blocked or game["phase"] != "EXPLORING" or not adjacent,
                    on_click=_move,
                    args=(x, y),
                )


def _reward_payload(game: dict[str, Any]) -> dict[str, Any]:
    route = game.get("route") or "keeper"
    name = campaign.ROUTES.get(route, campaign.ROUTES["keeper"])["name"]
    return {
        "gold": 80,
        "hp": 0,
        "item_name": f"{name}远征徽章",
        "item_prompt": f"fantasy game achievement badge for the {name} route, lighthouse fog harbor, polished 2D concept art",
    }


def _render_result(game: dict[str, Any]) -> None:
    if game["result"] in campaign.ROUTES:
        route = campaign.ROUTES[game["result"]]
        st.success(f"{route['name']}结局 · {route['ending']}")
    else:
        st.error("远征失败 · 莉亚倒在了迷雾中")
    st.plotly_chart(_heatmap_figure(game), width="stretch", key="campaign_heatmap")
    if game.get("hit_points"):
        st.caption(f"本局共记录 {len(game['hit_points'])} 次受击，热点用于校验陷阱与敌人布置。")
    else:
        st.caption("本局没有受击，热力图保持为零。")
    with st.expander("AI系统复盘", expanded=True):
        if st.button("生成200字内优化建议", key="campaign_review", width="stretch"):
            payload = {
                key: game.get(key, [])
                for key in ("battle_log", "path", "hit_points", "dps_samples")
            }
            payload["result"] = (
                game["result"]
                if game["result"] in {"defeat", "keeper", "tide", "oath"}
                else "defeat"
            )
            payload["mode"] = "deepseek"
            with st.spinner("正在复盘战斗日志与路线…"):
                result = _post("/api/arena/review", payload, timeout=80)
            if result:
                st.session_state.campaign_review = result.get("review", "")
            else:
                st.session_state.campaign_review = "建议把补给点作为路线锚点，减少敌人与出口的连续压力；高伤技能保留给精英，短CD技能用于填补真空期，并根据受击热区调整陷阱间距。"
        if st.session_state.campaign_review:
            st.write(st.session_state.campaign_review)
            st.caption(f"{len(st.session_state.campaign_review)} / 200 字")
    with st.expander("ComfyUI 成就海报"):
        st.caption("本地 8188 服务不可用时自动回退到可下载的占位海报。")
        if st.button("生成远征成就海报", key="campaign_poster_button", width="stretch"):
            reward = _reward_payload(game)
            with st.spinner("正在生成成就海报…"):
                result = _post("/api/arena/poster", reward, timeout=140)
            if result is None:
                fallback = placeholder_poster(
                    reward["item_name"], "FastAPI或ComfyUI不可用，已使用本地占位图。"
                )
                result = fallback.model_dump()
            st.session_state.campaign_poster = result
            game["poster"] = result
        poster = st.session_state.campaign_poster or game.get("poster")
        if poster:
            data = base64.b64decode(poster["image_base64"])
            st.image(data, width="stretch")
            st.caption(
                "ComfyUI生成"
                if poster.get("source") == "comfyui"
                else "本地占位图 · " + poster.get("notice", "")
            )
            st.download_button(
                "下载海报",
                data,
                file_name="fogharbor-expedition-poster.png",
                mime=poster.get("mime_type", "image/png"),
                width="stretch",
            )
    st.download_button(
        "导出远征存档 JSON",
        json.dumps(game, ensure_ascii=False, indent=2),
        file_name="fogharbor-expedition.json",
        mime="application/json",
        width="stretch",
    )


def _render_left(game: dict[str, Any]) -> None:
    player = game["player"]
    st.markdown('<div class="game-section">01 / EXPEDITION CONTROL</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.image(campaign_art.portrait("hero", scale=6), width=96)
        st.subheader(player["name"])
        st.caption("雾港远征者 · 2D路线试炼")
        st.progress(
            max(0, player["hp"]) / player["max_hp"], text=f"HP {player['hp']} / {player['max_hp']}"
        )
        st.progress(player["mp"] / player["max_mp"], text=f"MP {player['mp']} / {player['max_mp']}")
        metrics = st.columns(2)
        metrics[0].metric("攻击", player["atk"])
        metrics[1].metric("金币", player["gold"])
        st.caption(
            f"位置 ({player['x']},{player['y']}) · 已完成 {len(game['completed_levels'])} / 11 关"
        )
    definition = game["level"]["definition"]
    st.markdown(
        f'<div class="route-card"><b>{definition["name"]}</b><br><small>{definition["objective"]}</small></div>',
        unsafe_allow_html=True,
    )
    if game["phase"] == "ROUTE_CHOICE":
        st.subheader("选择一条命运路线")
        for route_id, route in campaign.ROUTES.items():
            st.markdown(
                f'<div class="route-card" style="border-color:{route["color"]}"><b>{route["name"]}</b><br><small>{route["ending"]}</small></div>',
                unsafe_allow_html=True,
            )
            st.button(
                f"进入{route['name']}",
                key=f"route_{route_id}",
                type="primary" if route_id == "keeper" else "secondary",
                width="stretch",
                on_click=_choose_route,
                args=(route_id,),
            )
    st.subheader("主动技能栏 · 4 槽")
    for index, skill_id in enumerate(game["equipped"], 1):
        data = campaign._skill_data(skill_id)
        st.caption(f"{index}. {data['name']} · {data['description']}")
    with st.expander("技能书与装备"):
        learned = game.get("learned_books", [])
        if not learned:
            st.caption("探索地图中的 ✦ 技能书格，获得后可学习。")
        else:
            for skill_id in learned:
                data = campaign.SKILL_BOOKS[skill_id]
                cols = st.columns([0.42, 1.45, 0.85, 0.55])
                cols[0].image(campaign_art.book_icon(skill_id), width=42)
                cols[1].caption(f"{data['name']} · {data['damage']}伤害 / CD{data['cooldown']}")
                slot = cols[2].selectbox(
                    "槽位", range(1, 5), key=f"equip_slot_{skill_id}", label_visibility="collapsed"
                )
                cols[3].button(
                    "装备",
                    key=f"equip_{skill_id}",
                    on_click=_equip,
                    args=(skill_id, slot - 1),
                    width="stretch",
                )
    with st.expander("存档与统计"):
        st.selectbox("存档位", [1, 2, 3], key="campaign_slot")
        a, b = st.columns(2)
        a.button("保存", key="campaign_save", width="stretch", on_click=_save)
        b.button("载入", key="campaign_load", width="stretch", on_click=_load)
        st.caption(
            f"击杀 {game['stats']['kills']} · 技能 {game['stats']['skill_casts']} · 最高 DPS {game['stats']['highest_dps']:.1f}"
        )
        if game["achievements"]:
            st.caption("成就：" + "、".join(game["achievements"]))
    st.button("重新开始远征", key="campaign_restart", width="stretch", on_click=_restart)


def _render_middle(game: dict[str, Any]) -> None:
    level = game["level"]
    st.markdown('<div class="game-section">02 / 2D WORLD MAP</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="campaign-title">{level["definition"]["name"]}</div><div class="campaign-subtitle">{level["definition"]["objective"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="campaign-legend">'
        '<span><i style="background:#f2c96d"></i>玩家</span>'
        '<span><i style="background:#e35c54"></i>怪物</span>'
        '<span><i style="background:#e58c5e"></i>陷阱</span>'
        '<span><i style="background:#63d2c6"></i>补给</span>'
        '<span><i style="background:#d8b768"></i>技能书</span>'
        '<span><i style="background:#d8b768"></i>出口</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="campaign_map_frame"):
        st.image(campaign_art.map_image(game), width="stretch")
        st.markdown(
            '<div class="campaign-art-caption">Kenney Tiny Dungeon CC0 像素素材 · 图块预览与下方格子交互同步</div>',
            unsafe_allow_html=True,
        )
    _render_grid(game)
    st.caption("只能点击四方向相邻格；墙体、战斗和路线选择会锁定地图输入。")
    if game.get("last_message"):
        st.markdown(
            f'<div class="campaign-message">{game["last_message"]}</div>', unsafe_allow_html=True
        )
    stats = st.columns(3)
    stats[0].metric("行动轨迹", len(game["path"]))
    stats[1].metric("受击次数", len(game["hit_points"]))
    stats[2].metric("已学技能", len(game["learned_books"]))
    if game["phase"] == "RESULT":
        _render_result(game)


def _render_right(game: dict[str, Any]) -> None:
    st.markdown('<div class="game-section">03 / COMBAT & TELEMETRY</div>', unsafe_allow_html=True)
    if game["phase"] == "COMBAT" and game["combat"]:
        combat = game["combat"]
        enemy_cols = st.columns([0.42, 1.58])
        enemy_cols[0].image(campaign_art.enemy_portrait(combat, scale=6), width=96)
        enemy_cols[1].subheader(combat["name"])
        enemy_cols[1].caption(f"行为：{combat['behavior']} · 像素战斗素材")
        st.progress(
            max(0, combat["hp"]) / combat["max_hp"],
            text=f"敌人 HP {combat['hp']} / {combat['max_hp']} · ATK {combat['atk']}",
        )
        if combat.get("telegraph"):
            st.warning("敌人正在蓄力：下一次反击会增强，使用防御或控制技能。")
        effect = game.get("effects", [])[-1:]
        if effect and time.time() - effect[0]["started_at"] < effect[0]["duration_ms"] / 1000:
            st.markdown(
                f'<div class="fx-banner">✦ {effect[0]["label"]} · 技能演出 {effect[0]["duration_ms"]}ms</div>',
                unsafe_allow_html=True,
            )
        st.caption("技能先播放短时表现，再结算伤害与敌方反击；冷却按完整动作回合推进。")
        for slot, skill_id in enumerate(game["equipped"], 1):
            data = campaign._skill_data(skill_id)
            cd = combat["cooldowns"].get(skill_id, 0)
            label = f"{slot}. {data['name']} · {data['damage']}伤害"
            if cd:
                label += f" · CD{cd}"
            st.button(
                label,
                key=f"campaign_act_{skill_id}_{slot}",
                type="primary" if slot == 1 else "secondary",
                width="stretch",
                disabled=bool(cd or game["player"]["mp"] < data["cost"]),
                on_click=_act,
                args=(skill_id,),
            )
            st.caption(f"消耗 {data['cost']} MP · {data['description']}")
        st.button(
            "等待 · 回 3 MP", key="campaign_wait", width="stretch", on_click=_act, args=("wait",)
        )
    elif game["phase"] == "ROUTE_CHOICE":
        with st.container(border=True):
            st.subheader("地图分支已展开")
            st.write("路线选择会改变接下来的三张地图、敌人组合、技能书和最终结局。")
    elif game["phase"] == "RESULT":
        st.subheader("远征结算")
        st.write("本局的战斗日志、技能真空和受击热区已记录在左侧存档与中间复盘图表中。")
    else:
        with st.container(border=True):
            st.subheader("等待遭遇")
            st.caption("移动到 M 怪物格后，右侧会出现短回合战斗面板。")
            st.write("技能书会扩展技能栏；四个槽位支持在探索中随时重新配置。")
    st.plotly_chart(_dps_figure(game), width="stretch", key="campaign_dps")
    frame = _dps_frame(game)
    if not frame.empty:
        metrics = st.columns(2)
        metrics[0].metric("爆发峰值", f"{frame['dps'].max():.1f}")
        metrics[1].metric("累计平均", f"{frame['dps'].mean():.1f}")
    with st.expander("最近战斗日志", expanded=game["phase"] == "COMBAT"):
        if game["battle_log"]:
            st.dataframe(
                pd.DataFrame(game["battle_log"]).tail(10), hide_index=True, width="stretch"
            )
        else:
            st.caption("尚未发生战斗。")


def render() -> None:
    _initialize()
    st.markdown(CSS + EXTRA_CSS, unsafe_allow_html=True)
    game = st.session_state.campaign_game
    phase = PHASE_LABELS.get(game["phase"], game["phase"])
    st.markdown(
        f'<div class="campaign-hero"><div><div class="campaign-kicker">FOGHARBOR / 2D EXPEDITION</div><div class="campaign-brand">AI技术策划试炼场 · 大型远征</div><div class="campaign-subtitle">11关 · 3路线 · 3结局 · 11本技能书 · 4技能槽</div></div><div class="campaign-phase">{phase}</div></div>',
        unsafe_allow_html=True,
    )
    if st.session_state.campaign_notice:
        st.info(st.session_state.campaign_notice)
    left, middle, right = st.columns([0.88, 1.55, 1.12], gap="large")
    with left:
        _render_left(game)
    with middle:
        _render_middle(game)
    with right:
        _render_right(game)
    st.markdown(
        '<div class="campaign-footer">2D离线规则可完整运行 · Kenney Tiny Dungeon CC0素材 · DeepSeek / ComfyUI 为可选增强服务 · 所有运行数据写入 E:\\0</div>',
        unsafe_allow_html=True,
    )
