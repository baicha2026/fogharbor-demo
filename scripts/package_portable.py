"""白名单打包 Windows 便携包；不复制开发环境、真实密钥或历史存档。"""

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "AI技术策划试炼场_Windows便携版.zip"
PACKAGE = "Fogharbor"

START_SCRIPT = r'''@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1
if not exist "Fogharbor.exe" (
    echo Please extract the entire ZIP before starting the game.
    pause
    exit /b 1
)
start "" /wait "%~dp0Fogharbor.exe" %*
exit /b %errorlevel%
'''

GUIDE = """AI技术策划试炼场 · 雾港守灯人 / Windows 便携版

【开始游戏】
1. 将 ZIP 整体解压到有写入权限的文件夹，例如 D:\\Games\\Fogharbor。
   原设备要求不使用 C 盘：请在新设备上也选择 D、E 或其它非 C 盘。
   不需要创建 E:\\0，也不需要安装 Python。
2. 双击 StartGame.cmd。它自动切换到游戏所在文件夹，再打开图形启动器。
3. 等待启动器显示“已就绪”，游戏会在默认浏览器中打开。
4. 浏览器关闭后，可以在启动器中点击“打开游戏”。关闭启动器会停止游戏。

请先完整解压，不要在压缩软件预览窗口中直接运行。
系统要求：Windows 10/11 64 位（x64），已安装 Edge、Chrome 等现代浏览器。
建议预留至少 500 MB 空间。游戏启动器使用本机服务，无需联网即可游玩。
本包为 Windows EXE，不能在 macOS、Linux、Android、iOS 上直接运行。

【游戏内容】
默认进入大型 2D 远征：11 张地图、3 条路线、3 个主要结局、
11 本技能书和 4 个主动技能槽；侧栏可切换剧情冒险及策划试炼场。
包含角色、怪物、陷阱、补给、技能书与地图素材。

【存档与迁移】
运行目录、日志和存档自动保存在游戏旁边的 .runtime 文件夹。
大型远征可在左侧“存档与统计”中保存或载入，存档位置：
.runtime\\campaign\\slot1.json 至 slot3.json。
如要保留原设备进度：先保存并关闭游戏，再把原设备的
.runtime\\campaign 文件夹复制到新设备同名位置。
本压缩包默认不包含个人存档、个人 API Key 和开发环境。

【可选 AI 功能】
完整游戏不需要配置 DeepSeek 或 ComfyUI。
使用真实 AI 复盘：将 .env.example 复制为 .env，填写自己的 DeepSeek Key，
保持文件在 EXE 旁，重启游戏。需要网络及个人 API 配额。
使用真实 AI 海报：新设备上需自行安装并启动 ComfyUI（默认 8188 端口），
安装兼容模型，在 .env 中配置模型名称。ComfyUI 和大模型未随包附带。
未配置时使用离线规则任务、规则复盘与明确标注的本地占位海报。

【无法启动时】
先确认已完整解压到可写入文件夹，并通过 StartGame.cmd 启动。
启动失败时可查看 .runtime\\logs\\backend.log 与 frontend.log。
日志文件夹尚未出现时，问题发生在 EXE 解包或系统加载阶段。

【素材许可】
像素素材：Kenney Tiny Dungeon，CC0。
来源 https://kenney.nl/assets/tiny-dungeon
原始许可见 Kenney-License.txt，另有技能书程序绘制图标。
"""


def main() -> int:
    executable = ROOT / "dist" / "Fogharbor.exe"
    if not executable.is_file():
        raise FileNotFoundError("请先运行 scripts/build_exe.py。")
    # EXE已经压缩过，ZIP再压缩的收益有限；压缩包不扫描项目目录。
    with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for source, target in (
            (executable, "Fogharbor.exe"),
            (ROOT / ".env.example", ".env.example"),
            (ROOT / "assets" / "kenney" / "License.txt", "Kenney-License.txt"),
        ):
            archive.write(source, f"{PACKAGE}/{target}")
        archive.writestr(f"{PACKAGE}/StartGame.cmd", START_SCRIPT.replace("\n", "\r\n"))
        archive.writestr(f"{PACKAGE}/使用说明.txt", GUIDE.encode("utf-8-sig"))
    with ARCHIVE.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    ARCHIVE.with_suffix(".sha256.txt").write_text(
        f"{digest}  {ARCHIVE.name}\n", encoding="utf-8"
    )
    print(f"便携压缩包：{ARCHIVE} ({ARCHIVE.stat().st_size / 1024**2:.1f} MiB)")
    print(f"SHA256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
