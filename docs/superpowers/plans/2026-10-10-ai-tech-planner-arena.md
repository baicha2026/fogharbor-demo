# AI技术策划试炼场 Implementation Plan

> Inline execution is authorized by the user's “开始编码”.

**Goal:** 实现任务驱动的网格探索、回合战斗与 AI 复盘游戏循环。

**Architecture:** session_state.arena 管理游戏状态；game 包提供纯逻辑与 Pandas/Plotly 图表；backend.arena_ai 封装异步生成与校验，复用 ComfyUI。

**Tech Stack:** Python 3.11+、Streamlit、FastAPI、httpx、Pydantic、Plotly、Pandas、Pillow。

## 执行步骤

- [x] 新增 tests/test_arena.py，验证地图可复现、相邻移动、事件一次触发、技能冷却与 MP、击杀无反击、失败/胜利与奖励幂等、实际 DPS 与受击次数。
- [x] 实现 game/engine.py：new_game(task=None, hp_ratio=100, gold=250, seed=42)、move(game,x,y)、act(game,skill)、finish(game,reason)。拒绝非法操作且不修改状态。
- [x] 实现 game/charts.py：map_figure(game)、dps_figure(game)、hit_frame(game)、heatmap_figure(game)。实际回合秒数作为横轴，避免用户点击速度污染数值。
- [x] 新增 game/contracts.py、backend/arena_ai.py、backend/poster.py 与 API。HTTP 模拟验证 JSON 重试、真实模式失败、复盘长度和 ComfyUI 占位。
- [x] 改 app.py，实现三栏、选择事件移动、方向按钮、技能/等待、结算自动复盘、重试与海报、导出。迁移 tests/test_frontend.py 到新首页行为。
- [x] 更新 requirements.txt 与 README.md，记录准确数值、启动/配置、状态生命周期和外部服务边界。
- [x] 执行 `.venv/Scripts/python.exe -m pytest -q` 和 `-m ruff check .`；运行服务器并以 Playwright 验证地图点击、战斗、结算、重开，保存截图。

当前目录没有 Git 仓库，不执行 commit。不写入或读取 API Key 内容。

验证结果：64项pytest通过；Ruff通过；实际Edge浏览器验证地图点击与六场战斗，胜利、复盘、海报及重置均通过。未调用真实DeepSeek或GPU出图，相关网络协议使用模拟验证。
