"""独立调试前端时先设置项目缓存，再导入Streamlit CLI。"""

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime_paths import configure_local_paths  # noqa: E402

if __name__ == "__main__":
    configure_local_paths()
    sys.argv = ["streamlit", "run", str(ROOT / "app.py"), *sys.argv[1:]]
    runpy.run_module("streamlit", run_name="__main__")
