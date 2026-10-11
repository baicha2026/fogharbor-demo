import os
import tempfile
from pathlib import Path

from runtime_paths import ROOT, configure_local_paths


def test_cache_temp_browser_and_streamlit_config_stay_in_project():
    configure_local_paths()
    for key in (
        "TEMP",
        "TMP",
        "TMPDIR",
        "XDG_CACHE_HOME",
        "PLAYWRIGHT_BROWSERS_PATH",
        "PIP_CACHE_DIR",
    ):
        assert Path(os.environ[key]).is_relative_to(ROOT / ".runtime")
    assert Path(tempfile.gettempdir()).is_relative_to(ROOT / ".runtime")
    if os.name == "nt":
        from streamlit.config import get_config_files

        assert Path.home().is_relative_to(ROOT / ".runtime")
        assert all(Path(p).is_relative_to(ROOT) for p in get_config_files("config.toml"))
