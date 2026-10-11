from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pyinstaller_includes_large_campaign_modules() -> None:
    spec = (ROOT / "packaging" / "fogharbor.spec").read_text(encoding="utf-8")

    assert '"adventure.campaign"' in spec
    assert '"adventure.campaign_ui"' in spec
