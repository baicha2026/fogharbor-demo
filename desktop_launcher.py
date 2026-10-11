"""单文件EXE入口：图形启动器及两种隐藏服务进程，不依赖外部Python。"""

import argparse
import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from dotenv import dotenv_values

from runtime_paths import configure_local_paths, resource_root, user_root


def service_command(role: str, port: int) -> list[str]:
    """冻结后sys.executable是本EXE，不能使用python -m，否则会递归打开启动器。"""
    args = ["--service", role, "--port", str(port)]
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, str(resource_root() / "desktop_launcher.py"), *args]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class GameServices:
    def __init__(self):
        self.processes: list[subprocess.Popen] = []
        self.logs = []
        self.cancel = threading.Event()
        self.backend_url = ""
        self.game_url = ""
        self.log_dir = user_root() / ".runtime" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _spawn(self, role: str, port: int, environment: dict) -> subprocess.Popen:
        log = (self.log_dir / f"{role}.log").open("w", encoding="utf-8")
        self.logs.append(log)
        process = subprocess.Popen(
            service_command(role, port),
            cwd=resource_root(),
            env=environment,
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.processes.append(process)
        return process

    def _wait(self, process: subprocess.Popen, url: str, role: str) -> None:
        deadline = time.monotonic() + 75
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while time.monotonic() < deadline:
            if self.cancel.is_set():
                raise RuntimeError("启动已取消。")
            if process.poll() is not None:
                raise RuntimeError(f"{role}启动失败，请查看{self.log_dir}中的日志。")
            try:
                with opener.open(url, timeout=1) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            self.cancel.wait(0.15)
        raise RuntimeError(f"{role}启动超时，请查看{self.log_dir}中的日志。")

    def start(self) -> None:
        environment = {
            key: value
            for key, value in dotenv_values(user_root() / ".env").items()
            if value is not None
        }
        environment.update(os.environ)
        backend_port, frontend_port = free_port(), free_port()
        while frontend_port == backend_port:
            frontend_port = free_port()
        self.backend_url = f"http://127.0.0.1:{backend_port}"
        self.game_url = f"http://127.0.0.1:{frontend_port}"
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        backend = self._spawn("backend", backend_port, environment)
        self._wait(backend, self.backend_url + "/health", "逻辑服务")
        if self.cancel.is_set():
            raise RuntimeError("启动已取消。")
        frontend_environment = {
            key: value for key, value in environment.items() if not key.startswith("DEEPSEEK_")
        }
        frontend_environment["BACKEND_URL"] = self.backend_url
        frontend = self._spawn("frontend", frontend_port, frontend_environment)
        self._wait(frontend, self.game_url + "/_stcore/health", "游戏页面")

    def stop(self) -> None:
        self.cancel.set()
        for process in reversed(self.processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        for log in self.logs:
            log.close()


def serve(role: str, port: int) -> None:
    configure_local_paths()
    os.chdir(resource_root())
    # --windowed构建的stdout/stderr为None，框架日志需要有效输出流。
    log_dir = user_root() / ".runtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    if sys.stdout is None or sys.stderr is None:
        output = (log_dir / f"{role}.log").open("a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = output
    if role == "backend":
        import uvicorn

        from backend.main import app

        uvicorn.run(app, host="127.0.0.1", port=port, loop="asyncio", http="h11", ws="none")
    else:
        from streamlit.web import bootstrap

        flags = {
            "server.address": "127.0.0.1",
            "server.port": port,
            "server.headless": True,
            "server.fileWatcherType": "none",
            "browser.gatherUsageStats": False,
            "global.developmentMode": False,
        }
        bootstrap.load_config_options(flags)
        bootstrap.run(str(resource_root() / "app.py"), False, [], flags)


def publish_state(services: GameServices, path: Path, window_verified: bool = False) -> None:
    path.write_text(
        json.dumps(
            {
                "game_url": services.game_url,
                "backend_url": services.backend_url,
                "pids": [p.pid for p in services.processes],
                "resource_root": str(resource_root()),
                "user_root": str(user_root()),
                "window_verified": window_verified,
            }
        ),
        encoding="utf-8",
    )


def launch_window(auto_browser: bool = True, verification: tuple[Path, Path] | None = None) -> None:
    import tkinter as tk
    from tkinter import messagebox

    services = GameServices()
    messages = queue.Queue()
    window = tk.Tk()
    if verification:
        window.withdraw()  # 真实Tk窗口/图标加载验证，不弹出窗口或浏览器干扰用户。
    window.title("AI技术策划试炼场 · 大型2D远征")
    window.geometry("520x355")
    window.resizable(False, False)
    window.configure(bg="#131c23")
    icon = resource_root() / "assets" / "fogharbor.ico"
    if icon.is_file():
        window.iconbitmap(str(icon))
    tk.Label(
        window,
        text="FOGHARBOR / 2D EXPEDITION",
        font=("Arial", 18, "bold"),
        fg="#e9cd94",
        bg="#131c23",
    ).pack(
        pady=(25, 4)
    )
    tk.Label(
        window,
        text="AI技术策划试炼场 · 大型2D远征",
        font=("Arial", 14),
        fg="#ece2ce",
        bg="#131c23",
    ).pack()
    status = tk.StringVar(value="正在启动大型2D远征…")
    tk.Label(
        window, textvariable=status, wraplength=460, fg="#abb5b7", bg="#131c23", font=("Arial", 11)
    ).pack(pady=22)
    button = tk.Button(
        window,
        text="打开游戏",
        state="disabled",
        width=24,
        relief="flat",
        bg="#b18a48",
        fg="#131c23",
        font=("Arial", 12),
        command=lambda: webbrowser.open(services.game_url),
    )
    button.pack(ipady=7)
    tk.Label(
        window,
        text="关闭此窗口将停止游戏服务。\n无需Python；剧情无需API Key。",
        fg="#abb5b7",
        bg="#131c23",
        font=("Arial", 10),
    ).pack(pady=18)

    def worker():
        try:
            services.start()
            messages.put(None)
        except Exception as exc:
            services.stop()
            messages.put(str(exc))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    def poll():
        try:
            result = messages.get_nowait()
        except queue.Empty:
            window.after(150, poll)
            return
        if result:
            status.set("启动失败")
            if verification:
                verification[0].write_text(json.dumps({"error": result}), encoding="utf-8")
                window.after(0, close)
            else:
                messagebox.showerror("AI技术策划试炼场", result)
        else:
            status.set("大型2D远征已就绪 · " + services.game_url)
            button.configure(state="normal")
            if verification:
                publish_state(services, verification[0], window_verified=True)
            if auto_browser:
                webbrowser.open(services.game_url)

    def close():
        services.cancel.set()
        thread.join(timeout=2)
        services.stop()
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", close)
    window.after(150, poll)
    if verification:

        def check_stop():
            if verification[1].exists():
                close()
            else:
                window.after(200, check_stop)

        window.after(200, check_stop)
    try:
        window.mainloop()
    finally:
        services.cancel.set()
        thread.join(timeout=2)
        services.stop()


def main() -> int:
    configure_local_paths()
    parser = argparse.ArgumentParser(description="雾港守灯人桌面启动器")
    parser.add_argument("--service", choices=["backend", "frontend"])
    parser.add_argument("--port", type=int)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--headless", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--verify-window", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--state-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--stop-file", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.service:
        if args.port is None or not 1 <= args.port <= 65535:
            parser.error("服务需要有效端口。")
        serve(args.service, args.port)
    elif args.headless or args.verify_window:
        if not args.state_file or not args.stop_file:
            parser.error("验证模式需要state-file和stop-file。")
        if args.verify_window:
            launch_window(False, (args.state_file, args.stop_file))
            return 0
        services = GameServices()
        try:
            services.start()
            publish_state(services, args.state_file)
            while not args.stop_file.exists():
                if any(p.poll() is not None for p in services.processes):
                    return 1
                time.sleep(0.2)
        finally:
            services.stop()
    else:
        launch_window(not args.no_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
