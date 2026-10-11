"""安装用于验证的浏览器；下载、临时目录与浏览器全部位于E盘项目目录。"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime_paths import configure_local_paths  # noqa: E402

if __name__ == "__main__":
    configure_local_paths()
    raise SystemExit(
        subprocess.call([sys.executable, "-m", "playwright", "install", "chromium", "--only-shell"])
    )
