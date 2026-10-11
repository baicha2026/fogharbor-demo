# 雾港守灯人 · AI技术策划试炼场

一个有角色、对话、主线、支线、商店、首领与结局的 **2D像素回合制小游戏**。玩家扮演见习守灯人莉亚，找回三枚灯芯，击败熄灯者，再回港修复灯塔。

使用 **Python + Streamlit + Pillow + Plotly + Pandas**，FastAPI 提供异步 DeepSeek 与 ComfyUI 接口。角色和场景采用官方 **Kenney Tiny Dungeon / CC0** 免费素材，已随项目保存。剧情通关无需 API Key、网络或 GPU。原来的随机网格沙盘保留为“策划试炼场”。

## EXE直接运行

成品：`E:\0\dist\Fogharbor.exe`，**Windows x64 单文件**，已包含Python、依赖、页面与游戏素材，无需安装Python。跨设备使用便携包：`E:\0\AI技术策划试炼场_Windows便携版.zip`。

1. 完整解压便携包到可写入的目录，例如 `D:\Games` 或 `E:\Games`。双击包内的 `StartGame.cmd`，启动窗口自动开启本机服务并在默认浏览器中打开游戏。
2. 浏览器关闭后可在启动窗口点击“打开游戏”重新打开；关闭启动窗口会停止两个服务。
3. 端口自动选择，允许与源码版同时运行。默认剧情及规则复盘不需要API Key。

单文件解包目录使用相对路径 `.runtime\bundle`；`StartGame.cmd` 会先切换到游戏目录，因此解包文件、日志、应用缓存和存档均保存在游戏旁的 `.runtime`。新设备无需有E盘或创建 `E:\0`，选择可写入的非C盘目录即可。首次打开需要解包，通常等待数秒。请完整解压后再启动，不要从压缩软件的预览窗口运行。系统要求为 **Windows 10/11 x64** 和现代浏览器；建议预留500MB空间。macOS、Linux和手机无法直接运行此Windows EXE。

便携包不包含开发环境、个人存档、真实 `.env` 或API Key。默认任务、探索、战斗与结算可离线使用。DeepSeek需要在新设备配置自己的Key及网络；真实海报需要自行安装并启动ComfyUI与模型，未配置时返回本地占位海报。迁移进度时，先在大型远征中保存并关闭游戏，再将EXE旁 `.runtime\campaign` 复制到新设备相同位置。

可选AI配置：在EXE旁新建 `.env`，按下文填写DeepSeek或ComfyUI参数，再重启EXE。成品没有包含开发环境 `.env` 或真实Key。默认ComfyUI工作流已内置；自定义工作流可放在EXE旁的 `workflows` 下。日志位置为EXE旁 `.runtime/logs/backend.log` 与 `frontend.log`。

重新打包（构建过程全部使用E盘项目目录）：

```powershell
$env:PYTHONNOUSERSITE='1'
$env:PYTHONUTF8='1'
$env:TEMP='E:\0\.runtime\tmp'
$env:TMP='E:\0\.runtime\tmp'
$env:PIP_CACHE_DIR='E:\0\.runtime\pip'
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe scripts/build_exe.py
.\.venv\Scripts\python.exe scripts/verify_exe.py
.\.venv\Scripts\python.exe scripts/package_portable.py
.\.venv\Scripts\python.exe scripts/verify_exe.py --archive AI技术策划试炼场_Windows便携版.zip
```

PyInstaller配置位于 `packaging/fogharbor.spec`，构建缓存位于 `.runtime/build` 与 `.runtime/pyinstaller`。验证脚本将EXE或便携ZIP放在没有源码的独立目录、清空PATH，加载真实Tk启动窗口（隐藏显示），通过成品服务实际通关两个模式，然后确认关闭后服务停止。ZIP验证还会检查解包路径位于便携目录、压缩包未携带真实Key或历史运行数据，并通过实际 `StartGame.cmd` 启动。

## 启动（当前 E 盘环境）

在 PowerShell 执行：

```powershell
Set-Location E:\0
$env:PYTHONNOUSERSITE='1'
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe run.py
```

打开 [http://127.0.0.1:8501](http://127.0.0.1:8501)。启动器同时开启 Streamlit 与 FastAPI；按 Ctrl+C 关闭两个服务。默认监听本机，不自动打开系统浏览器。

首次在新环境安装，需要 **Python 3.11+**，并把 Python 安装到 E 盘。例如：

```powershell
Set-Location E:\0
New-Item -ItemType Directory -Force .runtime\tmp,.runtime\pip | Out-Null
$env:PYTHONNOUSERSITE='1'
$env:PYTHONUTF8='1'
$env:TEMP='E:\0\.runtime\tmp'
$env:TMP='E:\0\.runtime\tmp'
$env:PIP_CACHE_DIR='E:\0\.runtime\pip'
E:\py\Python313\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe run.py
```

已有 `.venv` 或 `.env` 时保留原配置。默认剧情不需要创建 `.env`。

`runtime_paths.py` 将临时文件、pip 缓存、浏览器、应用缓存和 Windows 下的进程用户配置放在 `E:\0\.runtime`；只改变应用进程及子进程的环境，不修改系统环境变量。字体使用项目内可选字体或 Pillow 内置字体。浏览器验证使用 E 盘 Chromium。游戏素材不从远程链接加载。

独立调试前端可执行 `python scripts/start_frontend.py`，它先配置本地运行目录，再导入 Streamlit。只有结算复盘和海报需要 FastAPI，独立后端命令为 `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`。

## 大型 2D 远征

侧栏切换到“**大型2D远征**”可进入升级后的长线模式。当前版本保持 2D 网格和 Streamlit 实现，不依赖 Godot 或 3D 资源：

- **11 张地图**：避风站、灯塔遗迹作为共享开场，随后从守灯、逐潮、破誓三条路线中选择一条，每条路线包含 3 张专属地图，并对应独立结局。
- **路线选择有实际后果**：后续地图、敌人组合、技能书、奖励和结局均由路线决定，结算时可查看路线成就。
- **技能书成长**：地图中放置 11 本唯一技能书，获得后可在左侧装备到 4 个主动技能槽。技能具有伤害、MP 消耗、冷却、护盾、控制、治疗或爆发等差异，每次释放会记录短时演出事件。
- **策划复盘数据**：移动轨迹、受击坐标、战斗日志和 DPS 样本贯穿整局；结算页绘制受击热力图与带爆发峰值、技能真空期标记的 DPS 曲线。
- **离线优先**：不配置 DeepSeek 或 ComfyUI 也能完整探索、战斗、存档和结算。AI 复盘失败时使用规则建议，海报服务不可用时自动生成可下载的本地占位海报。

大型远征的存档位保存在 `E:\0\.runtime\campaign\slot1.json` 至 `slot3.json`，采用临时文件替换写入；损坏存档会重命名为 `.broken` 备份。地图只能点击玩家四方向相邻格，战斗或路线选择期间会锁定移动。重新开始远征只清空当前会话，不影响原有“剧情冒险”和“策划试炼场”模式。

## 玩一局

1. 点击“开始冒险”，走到洛恩旁边接取主线，获得两瓶药剂。
2. 与药师艾芙交谈可接月露草支线，也可花20金币购买药剂。
3. 从避风站东南入口进入灯塔遗迹。开宝箱，击败三名守卫，再拾取对应的灯芯碎片。封印未解除时不能拾取碎片。
4. 集齐三枚碎片后，挑战东南角的熄灯者。看到“蓄力中”提示时使用防御。
5. 首领战后返回洛恩旁边交谈，点亮灯塔、获得守灯人徽章与80金币。

月露草支线不影响主线：交给艾芙可获得两瓶药剂与最多25HP治疗。港口的避风泉可免费恢复生命和魔力。切换地图保留已打开宝箱、已收集物品和已击败敌人。

| 操作 | 方法 |
| --- | --- |
| 移动 | 点击四方向相邻格、地图下方方向按钮；点击地图后也可使用 WASD / 方向键 |
| 互动 | 走到角色或泉水旁边，点击右侧按钮；地图获得焦点时按 E |
| 战斗 | 点击动作按钮；地图获得焦点时按1重击、2回响、3防御、4药剂、5等待 |
| 重开 | “重新开始”清空本次剧情进度与行囊 |
| 策划模式 | 展开左上角侧栏，选择“策划试炼场” |

墙不可穿越，不能对角移动，战斗中不能移动。HP耗尽后失败结算。每个浏览器会话独立，状态保存在 `st.session_state.adventure`；刷新导致会话重建时会丢失本局，结算区可导出 JSON。

## 战斗与关卡数值

| 内容 | 数值与设计目的 |
| --- | --- |
| 莉亚 | HP100、MP40、ATK20、金币30；资源随整局继承 |
| 破阵重击 | round(ATK×1.8)=36；消耗12MP，冷却3个完整后续回合 |
| 潮汐回响 | round(ATK×0.7)=14；恢复8MP，冷却1个完整后续回合 |
| 防御 / 等待 | 防御回4MP并将本回合反击降至1/3（向上取整）；等待回3MP |
| 药剂 | 恢复最多35HP / 6MP；战斗中消耗一回合并推进冷却 |
| 三名守卫 | HP44/52/60，ATK5/6/7；击败后解除各自的碎片封印，每只掉12金币 |
| 熄灯者 | HP112、ATK9；普通攻击9与预告重击18交替，防御重击只受6伤害；掉25金币 |
| 机关 / 宝箱 | 三处机关各8伤害，只触发一次；两个宝箱各有一瓶药剂，另有30/25金币 |
| 主线奖励 | 一次性80金币与最多20HP，解锁徽章 |

合法动作才推进冷却；玩家先出手，敌人存活才反击，击杀回合无反击。伤害取实际扣血量，排除过量伤害。详细策划注释见 `adventure/engine.py`、`adventure/content.py` 和 `game/engine.py`。

结算可展开“策划复盘”：DPS曲线按每回合2秒模拟时间计算，标出爆发峰值与技能真空期；受击热力图按地图分别聚合受击次数，包含陷阱和敌人反击。完整日志附地图ID，可导出整局 JSON、DPS CSV、热力图 CSV。长局复盘按接口限额均匀取样并附准确汇总，图表与导出保留完整记录。

## 可选 DeepSeek 与 ComfyUI

编辑 `.env` 并重启：

```dotenv
DEEPSEEK_API_KEY=你的Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
DEEPSEEK_TIMEOUT=60
```

模型名按账号可用模型设置。结算区开启“使用 DeepSeek 复盘”后再点击生成，将本局战斗日志、路径、受击点与DPS发送给AI，返回200字以内的系统优化建议。默认规则复盘不调用外网。策划模式还支持按玩家血量与金币生成动态任务 JSON。

后端通过 `httpx.AsyncClient` 异步调用，使用 JSON 输出与 Pydantic 校验，无效输出纠正重试一次；真实模式失败显示原因。前端请求期间有加载动画。Key只在后端读取，`.env` 已被忽略，不会发给浏览器。

`backend/poster.py` 预留异步 `generate_achievement_poster()`，默认连接本地8188：

```dotenv
COMFYUI_BASE_URL=http://127.0.0.1:8188
COMFYUI_WORKFLOW=workflows/reward_api.json
COMFYUI_CHECKPOINT=v1-5-pruned-emaonly.safetensors
COMFYUI_TIMEOUT=120
```

自行启动 ComfyUI、安装兼容模型后，结算点击“生成守灯人成就海报”，将徽章物品名与英文提示词注入 API 工作流。客户端提交 `/prompt`、轮询 `/history/{prompt_id}`、通过 `/view` 读取图片。服务或模型不可用时返回明确标注的本地占位图，不影响通关。本项目不下载模型。自定义工作流须为 ComfyUI **API格式**，提示词保留 `{{prompt}}`，模型名可使用 `{{checkpoint}}`。

## 文件与素材

```text
app.py                       默认剧情 / 策划模式入口
adventure/content.py         原创角色、任务、两张地图、实体与精灵编号
adventure/engine.py          探索、互动、背包、商店、战斗、结局规则
adventure/art.py             本地像素素材渲染
adventure/ui.py              三栏界面与 session_state
adventure/board.js + .css     Canvas鼠标/键盘组件
adventure/telemetry.py        长局复盘取样与汇总
assets/kenney/               官方图块、原始ZIP、许可证、来源与校验值
sandbox_app.py              保留的AI网格策略沙盘
game/                       沙盘状态机、合同、Pandas/Plotly图表
backend/                    FastAPI、异步DeepSeek、ComfyUI、海报占位
runtime_paths.py            项目内临时/缓存路径配置
run.py                      一键启动两个服务与退出清理
tests/                      数值、接口、Streamlit与实际浏览器验证
```

素材来源：[Kenney Tiny Dungeon](https://kenney.nl/assets/tiny-dungeon)，作者 Kenney，授权 [CC0](https://creativecommons.org/publicdomain/zero/1.0/)。原始许可保留于 `assets/kenney/License.txt`；详细清单见 [素材记录](assets/README.md)。角色命名、剧情、地图和战斗规则为本项目创作。

策划模式的动态任务、随机地图、三种战术建议及完整沙盘说明见 [策划模式指南](docs/arena-guide.md)。API文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)。

## 验证

```powershell
New-Item -ItemType Directory -Force .runtime\tmp | Out-Null
$env:PYTHONNOUSERSITE='1'
$env:TEMP='E:\0\.runtime\tmp'
$env:TMP='E:\0\.runtime\tmp'
$env:PIP_CACHE_DIR='E:\0\.runtime\pip'
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.runtime/pytest
.\.venv\Scripts\python.exe -m ruff check . --no-cache
```

可选实际浏览器验证，先启动 `run.py`；浏览器与安装临时文件均放在项目目录：

```powershell
.\.venv\Scripts\python.exe -m pip install playwright --cache-dir .runtime/pip
.\.venv\Scripts\python.exe scripts/setup_browser.py
.\.venv\Scripts\python.exe -m tests.browser_adventure
.\.venv\Scripts\python.exe -m tests.browser_smoke
```

测试覆盖完整剧情通关、碎片封印、跨地图持久化、NPC一次性奖励、支线交付、商店、合法移动、技能冷却、首领预告与防御、死亡/重开、图表、JSON校验、AI错误和ComfyUI占位。浏览器脚本实际点击地图与按钮、使用键盘操作，并把截图保存在 `artifacts/`。外部AI自动化使用HTTP模拟；真实DeepSeek与GPU工作流需要实际Key和本地模型联调。
