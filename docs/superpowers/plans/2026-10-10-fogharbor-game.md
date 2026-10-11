# 雾港守灯人 Implementation Plan

用户已批准制作，并要求不经过C盘。沿用已读取的计划及验证技能，本轮不再访问C盘技能文件。不再请求玩法确认。

**Goal:** 在现有Python项目中提供使用CC0网络素材、可通关的像素冒险。

**Architecture:** adventure/content.py编写两张地图与剧情；engine.py实现纯Python规则；art.py渲染本地素材；ui.py管理session_state与交互。原沙盘保留为策划模式。默认主页运行离线剧情，不依赖AI。

**Tech Stack:** Python、Streamlit、Pillow、Plotly、Pandas、FastAPI。

## 约束

- 所有新增文件、下载包、素材、浏览器、临时目录、测试输出和缓存位于E:/0。
- 使用E盘Python虚拟环境；设置PYTHONNOUSERSITE，避免用户site-packages。
- 移除项目中C盘字体/浏览器硬编码；海报使用随项目提供的字体或Pillow内置字体。
- 不更改.env密钥；网络素材保留原CC0许可证。

## 顺序

- [x] 下载官方Tiny Dungeon到assets/kenney并安全解压；制作本地图集核实形象和来源。
- [x] 编写关卡/任务规则测试，覆盖主线、NPC、背包、碰撞、商店、切图、首领、防御及结局。
- [x] 实现内容与世界状态机，并完成纯逻辑通关测试。
- [x] 实现像素地图/角色卡/战斗场景，接入三栏界面与原沙盘入口。
- [x] 本地剧情可直接玩；可选DeepSeek复盘、海报保留，记录分地图路径和受击。
- [x] 更新启动器、测试与README；E盘Chromium实际通关并检查小屏布局。
- [x] pytest与Ruff通过，来源审阅，确认临时/下载/缓存路径为E盘。

## 验收记录（2026-10-10）

- pytest：80 passed；Ruff：All checks passed。
- 剧情浏览器通关：105次移动、21个战斗回合、三碎片、四敌人、支线交付与灯塔结局。
- 鼠标Canvas、方向键移动、E对话、1重击快捷键、药剂商店、切图、首领蓄力防御、重开均通过。
- 430px小屏：地图未超出视口，Canvas点击可移动，侧栏初始收起，方向按钮保持同一行。
- 规则复盘及ComfyUI本地占位图实际请求成功；真实DeepSeek/GPU工作流未使用账号或模型联调。
- 原策划模式：真实点击Plotly、非法移动、六场战斗、胜利、复盘、占位海报、重置全部通过。
- 本地缓存测试核实tempfile、pip、Playwright与Streamlit配置路径位于E:/0；移除C盘字体/浏览器路径。
- 官方ZIP SHA256：c109438ab06f65fd80f9b2686a4cf9c7c11dc64444b47333ec71d602f8bb5fc7；132个PNG，原始CC0许可证已保存。
- 运行服务：http://127.0.0.1:8501（游戏）及http://127.0.0.1:8000/docs（接口）。

截图：artifacts/fogharbor-title.png、fogharbor-harbor.png、fogharbor-combat.png、fogharbor-ruins.png、fogharbor-ending.png、fogharbor-mobile.png；原沙盘截图同目录。
