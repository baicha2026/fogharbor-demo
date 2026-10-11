from html import escape

import plotly.graph_objects as go

from backend.models import ACTION_LABELS


def build_tree(session: dict | None, selected_id: str | None = None) -> go.Figure:
    if session is None:
        nodes = [
            {
                "id": "start",
                "depth": 0,
                "quest": {
                    "name": "故事的起点",
                    "branches": [
                        {"action": action, "title": "等待生成"} for action in ACTION_LABELS
                    ],
                },
                "player_state": {"gold": 250, "hp": 70, "reputation": 15},
            }
        ]
        root_id = "start"
        selected_id = "start"
    else:
        nodes, root_id = session["nodes"], session["root_id"]
    children = {(node.get("parent_id"), node.get("parent_action")): node for node in nodes}
    vertices, adjacency, edge_labels = {}, {}, {}
    for node in nodes:
        node_id = node["id"]
        state = node["player_state"]
        vertices[node_id] = {
            "kind": "quest",
            "depth": node["depth"],
            "label": node["quest"]["name"],
            "hover": escape(node["quest"]["name"])
            + "<br>"
            + f"金币 {state['gold']} · 血量 {state['hp']} · 声望 {state['reputation']}",
        }
        adjacency[node_id] = []
        for branch in node["quest"]["branches"]:
            action = branch["action"]
            child = children.get((node_id, action))
            child_id = child["id"] if child else f"{node_id}:{action}"
            adjacency[node_id].append(child_id)
            edge_labels[(node_id, child_id)] = ACTION_LABELS[action]
            if not child:
                label = ACTION_LABELS[action]
                vertices[child_id] = {
                    "kind": "preview",
                    "depth": node["depth"] + 1,
                    "label": label,
                    "hover": f"{label} · {escape(branch['title'])}<br>尚未探索，点击任务选项后延展",
                }
    positions = {}
    leaf = 0

    def place(node_id: str) -> float:
        nonlocal leaf
        descendants = adjacency.get(node_id, [])
        if descendants:
            ys = [place(child) for child in descendants]
            y = sum(ys) / len(ys)
        else:
            y = float(-leaf)
            leaf += 1
        positions[node_id] = (vertices[node_id]["depth"], y)
        return y

    place(root_id)
    fig = go.Figure()
    for parent_id, child_ids in adjacency.items():
        for child_id in child_ids:
            x0, y0 = positions[parent_id]
            x1, y1 = positions[child_id]
            midpoint = x0 + 0.48
            preview = vertices[child_id]["kind"] == "preview"
            fig.add_trace(
                go.Scatter(
                    x=[x0, midpoint, midpoint, x1],
                    y=[y0, y0, y1, y1],
                    mode="lines",
                    line={
                        "color": "#d5dacc" if preview else "#8ca68a",
                        "width": 1.5,
                        "dash": "dot" if preview else "solid",
                    },
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            if not preview:
                fig.add_annotation(
                    x=midpoint + 0.13,
                    y=y1 + 0.17,
                    text=edge_labels[(parent_id, child_id)],
                    showarrow=False,
                    font={"size": 10, "color": "#84947e"},
                )
    ids = list(vertices)
    fig.add_trace(
        go.Scatter(
            x=[positions[key][0] for key in ids],
            y=[positions[key][1] for key in ids],
            mode="markers+text",
            text=[
                escape(vertices[key]["label"][:10])
                + ("…" if len(vertices[key]["label"]) > 10 else "")
                for key in ids
            ],
            textposition="bottom center",
            textfont={"size": 11, "color": "#536650"},
            customdata=[[key, vertices[key]["kind"]] for key in ids],
            hovertext=[vertices[key]["hover"] for key in ids],
            hoverinfo="text",
            marker={
                "size": [
                    17 if key == selected_id else 10 if vertices[key]["kind"] == "quest" else 8
                    for key in ids
                ],
                "color": [
                    "#216052"
                    if key == selected_id
                    else "#9bad88"
                    if vertices[key]["kind"] == "quest"
                    else "#f5f4ef"
                    for key in ids
                ],
                "line": {"width": 1.5, "color": "#9baa8a"},
            },
            showlegend=False,
        )
    )
    max_depth = max(value["depth"] for value in vertices.values())
    selected_depth = vertices.get(selected_id, {}).get("depth", 0)
    view_range = [-0.45, max_depth + 0.5]
    if max_depth > 3:
        view_range = [max(-0.45, selected_depth - 1.5), selected_depth + 1.8]
    fig.update_layout(
        height=min(720, max(350, leaf * 44)),
        margin={"l": 35, "r": 35, "t": 28, "b": 25},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Microsoft YaHei, sans-serif"},
        dragmode="pan",
        xaxis={"range": view_range, "showgrid": False, "zeroline": False, "visible": False},
        yaxis={"range": [-leaf + 0.1, 0.7], "showgrid": False, "zeroline": False, "visible": False},
        uirevision=session["id"] if session else "empty",
        hoverlabel={"bgcolor": "#fafbf6"},
    )
    return fig
