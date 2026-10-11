# PyInstaller单文件构建；明确白名单数据，不把.env、测试浏览器或本局日志打包。
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
datas = collect_data_files("streamlit")
datas += copy_metadata("streamlit", recursive=True)
datas += copy_metadata("plotly")
datas += [
    (str(root / "app.py"), "."),
    (str(root / "sandbox_app.py"), "."),
    (str(root / ".streamlit" / "config.toml"), ".streamlit"),
    (str(root / "assets"), "assets"),
    (str(root / "adventure" / "board.js"), "adventure"),
    (str(root / "adventure" / "board.css"), "adventure"),
    (str(root / "workflows" / "reward_api.json"), "workflows"),
]
a = Analysis(
    [str(root / "desktop_launcher.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=collect_submodules(
        "streamlit",
        filter=lambda name: not name.startswith(("streamlit.testing", "streamlit.hello")),
    ) + [
        "adventure.ui", "adventure.campaign", "adventure.campaign_ui",
        "adventure.styles", "frontend.styles", "frontend.tree",
        "uvicorn.logging", "uvicorn.loops.asyncio", "uvicorn.protocols.http.h11_impl",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "scipy", "sklearn", "torch", "tensorflow", "cv2",
        "IPython", "notebook", "jupyterlab", "pytest", "playwright", "numba",
        "sympy", "geopandas", "bokeh", "dash", "polars", "pydeck",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="Fogharbor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    # 使用相对路径，让压缩包解压到任意盘符后都能运行；
    # 解包目录会落在启动时的便携目录中，不依赖构建机的 E:\0 路径。
    runtime_tmpdir=".runtime\\bundle",
    icon=str(root / "assets" / "fogharbor.ico"),
)
