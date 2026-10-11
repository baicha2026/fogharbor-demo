"""项目内缓存和临时文件路径；不访问用户目录或系统字体目录。"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def resource_root() -> Path:
    """源码资源位于项目根目录；EXE资源位于便携目录下的PyInstaller解包目录。"""
    return Path(getattr(sys, "_MEIPASS", ROOT))


def user_root() -> Path:
    """EXE旁保存可选.env与运行数据，避免向临时解包目录写用户配置。"""
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else ROOT


def configure_local_paths() -> None:
    runtime = user_root() / ".runtime"
    paths = {
        "TEMP": runtime / "tmp",
        "TMP": runtime / "tmp",
        "TMPDIR": runtime / "tmp",
        "XDG_CACHE_HOME": runtime / "cache",
        "STREAMLIT_HOME": runtime / "streamlit",
        "PLAYWRIGHT_BROWSERS_PATH": runtime / "browsers",
        "PIP_CACHE_DIR": runtime / "pip",
    }
    if os.name == "nt":
        # Streamlit用Path.home()，不识别STREAMLIT_HOME。
        # 仅隔离当前进程及子进程的用户配置，不更改Windows系统环境或真实用户目录。
        paths["USERPROFILE"] = runtime / "profile"
    for key, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)
    # pytest/第三方库可能已经缓存过gettempdir；一并迁回项目临时目录。
    tempfile.tempdir = str(paths["TEMP"])
    os.environ["PYTHONNOUSERSITE"] = "1"
    os.environ["PYTHONUTF8"] = "1"
