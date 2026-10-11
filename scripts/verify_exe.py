"""从独立目录启动EXE或实际解压的便携包，清空PATH验证成品。"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime_paths import configure_local_paths  # noqa: E402


def main() -> int:
    configure_local_paths()
    parser = argparse.ArgumentParser(description="验证脱离源码目录的 Windows 成品")
    parser.add_argument("--archive", type=Path, help="解压并通过便携包的启动脚本验证")
    args = parser.parse_args()
    check_dir = ROOT / ".runtime" / "exe-check" / ("便携 验证-" + uuid.uuid4().hex[:8])
    check_dir.mkdir(parents=True)
    game_dir = check_dir
    if args.archive:
        with zipfile.ZipFile(args.archive) as archive:
            assert archive.testzip() is None, "ZIP校验失败"
            for entry in archive.namelist():
                destination = (check_dir / entry).resolve()
                if not destination.is_relative_to(check_dir.resolve()):
                    raise ValueError("ZIP条目超出解压目录")
            archive.extractall(check_dir)
        game_dir = check_dir / "Fogharbor"
        assert (game_dir / "StartGame.cmd").is_file()
        assert not (game_dir / ".env").exists(), "成品不应携带开发环境的Key"
        assert not (game_dir / ".runtime").exists(), "便携包应不包含历史运行数据"
    else:
        shutil.copy2(ROOT / "dist" / "Fogharbor.exe", game_dir / "Fogharbor.exe")
    executable = game_dir / "Fogharbor.exe"
    state_file, stop_file = check_dir / "state.json", check_dir / "stop"
    environment = dict(os.environ)
    environment["PATH"] = ""  # EXE服务不能偷偷依赖开发机Python或外部命令。
    environment.pop("PYTHONPATH", None)
    command = [str(executable)]
    if args.archive:
        command = [
            os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe"),
            "/d", "/c", "call", str(game_dir / "StartGame.cmd"),
        ]
    process = subprocess.Popen(
        [
            *command,
            "--verify-window",
            "--state-file",
            str(state_file),
            "--stop-file",
            str(stop_file),
        ],
        cwd=check_dir,
        env=environment,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    state = None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        deadline = time.monotonic() + 100
        while not state_file.is_file():
            if process.poll() is not None:
                raise RuntimeError(f"EXE启动失败，退出码{process.returncode}")
            if time.monotonic() > deadline:
                raise TimeoutError("EXE启动超时")
            time.sleep(0.25)
        state = json.loads(state_file.read_text(encoding="utf-8"))
        if "error" in state:
            raise RuntimeError(state["error"])
        assert state["window_verified"]
        assert Path(state["resource_root"]).is_relative_to(game_dir / ".runtime" / "bundle")
        assert Path(state["user_root"]) == game_dir
        print("Packaged services ready:", state, flush=True)
        with opener.open(state["backend_url"] + "/health", timeout=5) as response:
            health = json.load(response)
        assert health["comfyui_workflow_configured"]
        assert not health["deepseek_configured"], "成品不应携带开发环境的Key"
        test_env = dict(os.environ)
        test_env["FOGHARBOR_TEST_URL"] = state["game_url"]
        for module in ("tests.browser_adventure", "tests.browser_smoke"):
            result = subprocess.run([sys.executable, "-m", module], cwd=ROOT, env=test_env)
            if result.returncode:
                raise RuntimeError(f"EXE浏览器验证失败：{module}")
    finally:
        stop_file.touch()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)
        if process.returncode != 0:
            for log in (game_dir / ".runtime" / "logs").glob("*.log"):
                print(log.name + "\n" + log.read_text(encoding="utf-8", errors="replace")[-4500:])
    assert process.returncode == 0
    for url in (state["backend_url"] + "/health", state["game_url"] + "/_stcore/health"):
        try:
            opener.open(url, timeout=2)
        except (urllib.error.URLError, OSError):
            continue
        raise AssertionError("关闭EXE后服务未停止：" + url)
    (ROOT / "artifacts" / "exe-verification.json").write_text(
        json.dumps(
            {
                "directory": str(check_dir),
                "archive": str(args.archive.resolve()) if args.archive else None,
                "exe_only": not bool(args.archive),
                "game_directory": str(game_dir),
                "portable_paths": True,
                "empty_path": True,
                "services_stopped": True,
                "state": state,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "EXE verified: standalone copy, empty PATH, both games, "
        "offline AI, poster, service cleanup."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
