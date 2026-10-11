"""Start both local services with the same Python interpreter, and clean up on exit."""

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

from runtime_paths import configure_local_paths

ROOT = Path(__file__).resolve().parent


def ensure_port_free(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            raise RuntimeError(f"端口 {port} 已被占用，请修改 .env 或关闭对应服务。") from None


def wait_for_backend(process: subprocess.Popen, url: str) -> None:
    deadline = time.monotonic() + 30
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("FastAPI 启动失败，请查看上方日志。")
        try:
            with opener.open(url + "/health", timeout=1) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.25)
    raise RuntimeError("等待 FastAPI 启动超时，请检查服务日志。")


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main() -> int:
    configure_local_paths()
    # Existing environment variables take precedence. Do not modify the user's environment.
    environment = {
        key: value for key, value in dotenv_values(ROOT / ".env").items() if value is not None
    }
    environment.update(os.environ)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    processes: list[subprocess.Popen] = []
    try:
        backend_port = int(environment.get("BACKEND_PORT", "8000"))
        frontend_port = int(environment.get("FRONTEND_PORT", "8501"))
        if not all(1 <= port <= 65535 for port in (backend_port, frontend_port)):
            raise ValueError("端口需在 1–65535 之间。")
        if backend_port == frontend_port:
            raise ValueError("BACKEND_PORT 和 FRONTEND_PORT 不能相同。")
        backend_url = environment.get("BACKEND_URL", f"http://127.0.0.1:{backend_port}").rstrip("/")
        parsed = urlsplit(backend_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost"}
            or (parsed.port or 80) != backend_port
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("一键启动时 BACKEND_URL 必须与本地 BACKEND_PORT 对应。")
        ensure_port_free(backend_port)
        ensure_port_free(frontend_port)
        backend = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(backend_port),
            ],
            cwd=ROOT,
            env=environment,
        )
        processes.append(backend)
        wait_for_backend(backend, backend_url)
        frontend_environment = {
            key: value for key, value in environment.items() if not key.startswith("DEEPSEEK_")
        }
        frontend_environment["BACKEND_URL"] = backend_url
        frontend = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.address",
                "127.0.0.1",
                "--server.port",
                str(frontend_port),
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
            ],
            cwd=ROOT,
            env=frontend_environment,
        )
        processes.append(frontend)
        print(f"\n雾港守灯人: http://127.0.0.1:{frontend_port}", flush=True)
        print(f"FastAPI docs: {backend_url}/docs\n按 Ctrl+C 关闭两个服务。\n", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        raise RuntimeError("一个服务已退出，正在关闭其它服务。")
    except KeyboardInterrupt:
        print("\n正在关闭 雾港守灯人…", flush=True)
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"启动失败：{exc}", file=sys.stderr)
        return 1
    finally:
        for process in reversed(processes):
            stop(process)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
