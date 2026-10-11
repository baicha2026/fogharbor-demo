from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from game.engine import HEIGHT, WIDTH


def hit_frame(game: dict) -> pd.DataFrame:
    frame = pd.DataFrame(0, index=range(HEIGHT), columns=range(WIDTH), dtype=int)
    for hit in game.get("hit_points", []):
        frame.loc[int(hit["y"]), int(hit["x"])] += 1
    frame.index.name, frame.columns.name = "y", "x"
    return frame


def dps_frame(game: dict) -> pd.DataFrame:
    rows = game.get("dps_samples", [])
    return pd.DataFrame(
        rows,
        columns=[
            "elapsed",
            "battle_id",
            "battle_elapsed",
            "damage",
            "dps",
            "avg_dps",
            "action",
            "vacuum",
        ],
    )


def map_figure(game: dict) -> go.Figure:
    symbols = {0: "·", 1: "△", 2: "M", 3: "＋"}
    colors = {0: "#d8ddd2", 1: "#df9c63", 2: "#bd5f68", 3: "#68a78f"}
    cells = [
        {"x": x, "y": y, "text": symbols[v], "color": colors[v]}
        for y, row in enumerate(game["map"])
        for x, v in enumerate(row)
    ]
    fig = go.Figure(
        go.Scatter(
            x=[c["x"] for c in cells],
            y=[c["y"] for c in cells],
            mode="markers+text",
            text=[c["text"] for c in cells],
            textfont={"size": 18, "color": "#243d34"},
            marker={
                "size": 28,
                "symbol": "square",
                "color": [c["color"] for c in cells],
                "line": {"width": 1, "color": "white"},
            },
            hovertext=[f"({c['x']},{c['y']})" for c in cells],
            hoverinfo="text",
        )
    )
    path = game.get("path", [])
    if path:
        fig.add_trace(
            go.Scatter(
                x=[p["x"] for p in path],
                y=[p["y"] for p in path],
                mode="lines+markers",
                line={"color": "#253b34", "width": 2},
                marker={"size": 5},
                name="行动轨迹",
            )
        )
    p = game["player"]
    fig.add_trace(
        go.Scatter(
            x=[p["x"]],
            y=[p["y"]],
            mode="markers+text",
            text=["◆"],
            textfont={"size": 16, "color": "white"},
            marker={"size": 26, "symbol": "diamond", "color": "#173f70"},
            name="玩家",
            hovertext=["玩家当前位置"],
            hoverinfo="text",
        )
    )
    fig.update_layout(
        height=490,
        margin={"l": 25, "r": 15, "t": 15, "b": 25},
        showlegend=False,
        clickmode="event+select",
        dragmode=False,
        xaxis={
            "range": [-0.5, WIDTH - 0.5],
            "dtick": 1,
            "showgrid": False,
            "zeroline": False,
            "fixedrange": True,
        },
        yaxis={
            "range": [HEIGHT - 0.5, -0.5],
            "dtick": 1,
            "showgrid": False,
            "zeroline": False,
            "fixedrange": True,
            "scaleanchor": "x",
        },
        plot_bgcolor="#f7f8f2",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def heatmap_figure(game: dict) -> go.Figure:
    frame = hit_frame(game)
    fig = go.Figure(
        go.Heatmap(
            z=frame.values,
            x=frame.columns,
            y=frame.index,
            colorscale="YlOrRd",
            zmin=0,
            zmax=max(1, int(frame.values.max())),
            colorbar={"title": "受击次数"},
            hovertemplate="坐标 (%{x},%{y})<br>受击 %{z} 次<extra></extra>",
        )
    )
    fig.update_layout(
        height=350,
        margin={"l": 5, "r": 5, "t": 25, "b": 5},
        title="受击热力图（挫败区域）",
        yaxis={"autorange": "reversed"},
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def dps_figure(game: dict) -> go.Figure:
    frame = dps_frame(game)
    fig = go.Figure()
    if not frame.empty:
        fig.add_trace(
            go.Scatter(x=frame.elapsed, y=frame.dps, mode="lines+markers", name="瞬时 DPS")
        )
        fig.add_trace(
            go.Scatter(
                x=frame.elapsed,
                y=frame.avg_dps,
                mode="lines",
                name="平均 DPS",
                line={"dash": "dot"},
            )
        )
        peaks = frame[(frame.dps == frame.dps.max()) & (frame.dps > 0)].head(1)
        fig.add_trace(
            go.Scatter(
                x=peaks.elapsed,
                y=peaks.dps,
                mode="markers+text",
                text=["爆发峰值"] * len(peaks),
                textposition="top center",
                name="爆发峰值",
                marker={"size": 11, "color": "#d39048"},
            )
        )
        for row in frame[frame.vacuum].itertuples():
            fig.add_vrect(
                x0=row.elapsed - 2,
                x1=row.elapsed,
                fillcolor="#9aa49d",
                opacity=0.18,
                line_width=0,
                annotation_text="技能真空期",
            )
    fig.update_layout(
        height=300,
        margin={"l": 5, "r": 5, "t": 25, "b": 5},
        title="DPS 实时曲线",
        xaxis_title="全局战斗秒数",
        yaxis_title="伤害 / 秒",
        legend={"orientation": "h", "y": -0.3},
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
