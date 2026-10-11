"""大型远征的本地像素素材合成。

大型远征的规则地图使用按钮交互；本模块负责把同一份状态合成一张可读的
像素地图，确保角色、敌人、陷阱、补给、技能书和出口都有真实素材可见。
"""

from __future__ import annotations

import io
from functools import lru_cache
from typing import Any

from PIL import Image, ImageDraw

from adventure import campaign
from adventure.art import tile

TILE_SIZE = 16
MAP_SIZE = campaign.WIDTH * TILE_SIZE

# 行为与 Kenney Tiny Dungeon 中的敌人图块对应，颜色和轮廓在缩放后仍然可辨。
ENEMY_SPRITES = {
    # Tiny Dungeon 图集没有独立的 knight/wizard 文件名；使用已有角色图块
    # 做行为区分，并用光环颜色告诉玩家该敌人的战斗特性。
    "armor": ("boss", "#d9ae66"),
    "burn": ("slime", "#ea745f"),
    "stun": ("skeleton", "#d5d9df"),
    "pull": ("rat", "#c18160"),
    "slow": ("lorn", "#86d6d5"),
    "copy": ("eve", "#e35c54"),
}


@lru_cache(maxsize=1)
def _book_base() -> Image.Image:
    """绘制一个独立的16px技能书图标，避免把碎片图块误当成技能书。"""
    image = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((2, 2, 13, 14), fill="#2d3148", outline="#d8b768")
    draw.rectangle((4, 3, 7, 13), fill="#604e86", outline="#f1d897")
    draw.rectangle((8, 4, 12, 13), fill="#f0dfb0", outline="#be9653")
    draw.line((9, 7, 11, 7), fill="#6e5c8d")
    draw.line((9, 9, 11, 9), fill="#6e5c8d")
    return image


def _book_sprite(skill_id: str) -> Image.Image:
    image = _book_base().copy()
    color = campaign.SKILL_BOOKS[skill_id].get("color", "#d8b768")
    draw = ImageDraw.Draw(image)
    draw.point((1, 8), fill=color)
    draw.point((14, 8), fill=color)
    return image


def _enemy_sprite(enemy: dict[str, Any]) -> tuple[Image.Image, str]:
    sprite_name, color = ENEMY_SPRITES.get(enemy.get("behavior"), ("rat", "#e3a870"))
    return tile(sprite_name).copy(), color


def _glow(canvas: Image.Image, x: int, y: int, color: str) -> None:
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse(
        (x * TILE_SIZE + 1, y * TILE_SIZE + 1, x * TILE_SIZE + 14, y * TILE_SIZE + 14),
        fill=color + "55",
        outline=color + "cc",
        width=1,
    )
    canvas.alpha_composite(overlay)


def map_image(game: dict[str, Any], scale: int = 3) -> bytes:
    """返回带真实图块的10×10远征地图PNG。"""
    level = game["level"]
    canvas = Image.new("RGBA", (MAP_SIZE, MAP_SIZE), "#101a22")
    draw = ImageDraw.Draw(canvas)
    for y, row in enumerate(level["tiles"]):
        for x, kind in enumerate(row):
            base = "wall" if kind == "#" else "dungeon_floor"
            canvas.alpha_composite(tile(base), (x * TILE_SIZE, y * TILE_SIZE))
            draw.rectangle(
                (x * TILE_SIZE, y * TILE_SIZE, (x + 1) * TILE_SIZE - 1, (y + 1) * TILE_SIZE - 1),
                outline="#33434b",
                width=1,
            )

    for item in level.get("traps", []):
        _glow(canvas, item["x"], item["y"], "#e58c5e")
        canvas.alpha_composite(tile("trap"), (item["x"] * TILE_SIZE, item["y"] * TILE_SIZE))
    for item in level.get("supplies", []):
        _glow(canvas, item["x"], item["y"], "#63d2c6")
        canvas.alpha_composite(tile("potion"), (item["x"] * TILE_SIZE, item["y"] * TILE_SIZE))
    book = level.get("book")
    if book and not book.get("claimed"):
        _glow(canvas, book["x"], book["y"], campaign.SKILL_BOOKS[book["id"]]["color"])
        canvas.alpha_composite(
            _book_sprite(book["id"]), (book["x"] * TILE_SIZE, book["y"] * TILE_SIZE)
        )

    exit_cell = level["exit"]
    _glow(canvas, exit_cell["x"], exit_cell["y"], "#d8b768")
    canvas.alpha_composite(tile("stairs"), (exit_cell["x"] * TILE_SIZE, exit_cell["y"] * TILE_SIZE))

    for enemy in level.get("enemies", []):
        if enemy.get("defeated"):
            continue
        sprite, color = _enemy_sprite(enemy)
        _glow(canvas, enemy["x"], enemy["y"], color)
        canvas.alpha_composite(sprite, (enemy["x"] * TILE_SIZE, enemy["y"] * TILE_SIZE))

    player = game["player"]
    _glow(canvas, player["x"], player["y"], "#f2c96d")
    canvas.alpha_composite(tile("hero"), (player["x"] * TILE_SIZE, player["y"] * TILE_SIZE))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        (
            player["x"] * TILE_SIZE,
            player["y"] * TILE_SIZE,
            (player["x"] + 1) * TILE_SIZE - 1,
            (player["y"] + 1) * TILE_SIZE - 1,
        ),
        outline="#ffe6a1",
        width=1,
    )

    enlarged = canvas.resize((MAP_SIZE * scale, MAP_SIZE * scale), Image.Resampling.NEAREST)
    output = io.BytesIO()
    enlarged.save(output, format="PNG", optimize=True)
    return output.getvalue()


def portrait(sprite_name: str, scale: int = 5) -> bytes:
    """将16px角色图块放大为面板立绘。"""
    canvas = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), "#101a22")
    canvas.alpha_composite(tile(sprite_name), (0, 0))
    output = io.BytesIO()
    canvas.resize((TILE_SIZE * scale, TILE_SIZE * scale), Image.Resampling.NEAREST).save(
        output, format="PNG", optimize=True
    )
    return output.getvalue()


def enemy_portrait(enemy: dict[str, Any], scale: int = 5) -> bytes:
    """战斗面板中显示当前敌人的对应素材。"""
    sprite, _ = _enemy_sprite(enemy)
    canvas = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), "#101a22")
    canvas.alpha_composite(sprite, (0, 0))
    output = io.BytesIO()
    canvas.resize((TILE_SIZE * scale, TILE_SIZE * scale), Image.Resampling.NEAREST).save(
        output, format="PNG", optimize=True
    )
    return output.getvalue()


def book_icon(skill_id: str, scale: int = 3) -> bytes:
    """返回技能书列表中使用的像素图标。"""
    output = io.BytesIO()
    _book_sprite(skill_id).resize(
        (TILE_SIZE * scale, TILE_SIZE * scale), Image.Resampling.NEAREST
    ).save(output, format="PNG", optimize=True)
    return output.getvalue()
