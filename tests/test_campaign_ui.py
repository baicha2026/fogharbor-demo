from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_large_campaign_is_default_experience() -> None:
    ui = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()

    assert not ui.exception
    assert ui.session_state["campaign_game"]["phase"] == "EXPLORING"


def test_large_campaign_mode_renders_2d_grid_and_expedition_controls() -> None:
    ui = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not ui.exception

    ui.radio(key="experience").set_value("大型2D远征").run()

    assert not ui.exception
    assert ui.session_state["campaign_game"]["phase"] == "EXPLORING"
    grid_buttons = [
        button for button in ui.button if button.key and button.key.startswith("campaign_cell_")
    ]
    assert len(grid_buttons) == 100
    assert any(button.key == "campaign_save" for button in ui.button)
    assert any(button.key == "campaign_restart" for button in ui.button)
