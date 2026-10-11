from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_start_dialogue_shop_and_restarting_game():
    ui = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    ui.radio(key="experience").set_value("剧情冒险").run()
    assert not ui.exception
    ui.button(key="story_start").click().run()
    assert not ui.exception
    game = ui.session_state["adventure"]
    assert game["quest_stage"] == "meet"
    game["player"].update(x=2, y=2)
    ui.run()
    ui.button(key="story_interact_lorn").click().run()
    assert not ui.exception
    assert game["inventory"]["potion"] == 2
    assert game["quest_stage"] == "fragments"
    game["player"].update(x=5, y=2)
    ui.run()
    ui.button(key="story_interact_eve").click().run()
    ui.button(key="story_buy").click().run()
    assert not ui.exception
    assert game["player"]["gold"] == 10 and game["inventory"]["potion"] == 3
    ui.button(key="story_restart").click().run()
    assert not ui.exception
    assert ui.session_state["adventure"]["quest_stage"] == "meet"
    assert ui.session_state["adventure"]["removed"]["ruins"] == []


def test_combat_controls_and_mode_switch_preserve_independent_sessions():
    ui = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    ui.radio(key="experience").set_value("剧情冒险").run()
    ui.button(key="story_start").click().run()
    game = ui.session_state["adventure"]
    game["quest_stage"] = "fragments"
    game["map_id"] = "ruins"
    game["player"].update(x=4, y=1)
    ui.run()
    ui.button(key="story_move_right").click().run()
    assert not ui.exception
    assert game["phase"] == "COMBAT"
    ui.button(key="story_skill_burst").click().run()
    assert not ui.exception
    assert game["dps_samples"][0]["damage"] == 36
    assert ui.button(key="story_skill_burst").disabled
    ui.button(key="story_skill_flow").click().run()
    assert game["phase"] == "EXPLORING" and game["kills"] == 1
    ui.radio(key="experience").set_value("策划试炼场").run()
    assert not ui.exception
    assert ui.session_state["arena"]["phase"] == "SETUP"
    ui.radio(key="experience").set_value("剧情冒险").run()
    assert not ui.exception
    assert ui.session_state["adventure"]["kills"] == 1
