"""雾港守灯人主页；策划模式保留原沙盘。"""

import runpy
from pathlib import Path

from runtime_paths import configure_local_paths

configure_local_paths()

import streamlit as st  # noqa: E402 -- 缓存路径须在导入Streamlit前配置。

st.set_page_config(
    page_title="雾港守灯人", page_icon="🏮", layout="wide", initial_sidebar_state="collapsed"
)
with st.sidebar:
    st.caption("FOGHARBOR / PLAYGROUND")
    mode = st.radio("选择体验", ["大型2D远征", "剧情冒险", "策划试炼场"], key="experience")

if mode == "策划试炼场":
    runpy.run_path(str(Path(__file__).parent / "sandbox_app.py"), run_name="__main__")
elif mode == "大型2D远征":
    from adventure.campaign_ui import render

    render()
else:
    from adventure.ui import render

    render()
