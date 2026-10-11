import pytest

from runtime_paths import configure_local_paths

configure_local_paths()


@pytest.fixture
def quest_data():
    return {
        "name": "雾港的最后一封信",
        "description": "渡口即将关闭，一位信使希望你送出最后一封信。",
        "location": "雾港",
        "difficulty": "低",
        "preconditions": {
            "min_level": 1,
            "min_gold": 0,
            "min_hp": 0,
            "min_reputation": -100,
            "description": "能够抵达渡口。",
        },
        "rewards": {
            "gold": 80,
            "hp": 0,
            "reputation": 5,
            "item_name": "雾港信使徽章",
            "item_prompt": "A silver courier badge with a lighthouse motif, game item concept art",
        },
        "branches": [
            {
                "action": "accept",
                "title": "护送信件",
                "description": "穿过废弃渡口。",
                "outcome": "信件抵达，但旅程让你受了轻伤。",
                "effects": {"gold": 80, "hp": -5, "reputation": 5},
            },
            {
                "action": "refuse",
                "title": "留在城内",
                "description": "把线索交还信使。",
                "outcome": "你决定在城内休整。",
                "effects": {"gold": 0, "hp": 5, "reputation": 0},
            },
            {
                "action": "befriend",
                "title": "与信使结盟",
                "description": "交换情报。",
                "outcome": "你赢得了信使的信任。",
                "effects": {"gold": 0, "hp": 0, "reputation": 12},
            },
        ],
    }
