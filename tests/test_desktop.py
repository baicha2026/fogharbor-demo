import sys
from pathlib import Path

from desktop_launcher import free_port, service_command
from runtime_paths import ROOT, resource_root, user_root


def test_source_commands_invoke_python_and_frozen_commands_invoke_exe(monkeypatch):
    command = service_command("backend", 18000)
    assert command[1] == str(ROOT / "desktop_launcher.py")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "E:/0/dist/Fogharbor.exe")
    monkeypatch.setattr(sys, "_MEIPASS", "E:/0/.runtime/bundle/_MEItest", raising=False)
    assert service_command("frontend", 18501) == [
        "E:/0/dist/Fogharbor.exe",
        "--service",
        "frontend",
        "--port",
        "18501",
    ]
    assert user_root() == Path("E:/0/dist")
    assert resource_root() == Path("E:/0/.runtime/bundle/_MEItest")


def test_auto_port_is_a_valid_ephemeral_loopback_port():
    assert 1024 <= free_port() <= 65535
