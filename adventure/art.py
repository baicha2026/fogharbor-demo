"""用本地CC0图块组合像素画面。缩放使用最近邻，避免像素边缘模糊。"""

import base64
import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

from adventure.content import MAPS, SPRITES
from adventure.engine import entities

ROOT = Path(__file__).resolve().parents[1]
TILES = ROOT / "assets" / "kenney" / "Tiles"


@lru_cache(maxsize=160)
def tile(name: str) -> Image.Image:
    return Image.open(TILES / f"tile_{SPRITES[name]:04d}.png").convert("RGBA")


def png_bytes(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def data_url(image: Image.Image) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes(image)).decode("ascii")


def portrait(name: str, size: int = 96) -> bytes:
    canvas = Image.new("RGBA", (24, 24), "#1b2530")
    canvas.alpha_composite(tile(name), (4, 4))
    return png_bytes(canvas.resize((size, size), Image.Resampling.NEAREST))


def scene(game: dict, *, scale: int = 4) -> Image.Image:
    world = MAPS[game["map_id"]]
    canvas = Image.new("RGBA", (160, 160), "#151923")
    for y, row in enumerate(world["tiles"]):
        for x, kind in enumerate(row):
            floor = "floor" if game["map_id"] == "harbor" else "dungeon_floor"
            if game["map_id"] == "harbor" and (x * 7 + y * 11) % 9 == 0:
                floor = "floor_alt"
            canvas.alpha_composite(tile(floor), (x * 16, y * 16))
            if kind == "#":
                canvas.alpha_composite(tile("wall"), (x * 16, y * 16))
    for x, y, name in world["decor"]:
        canvas.alpha_composite(tile(name), (x * 16, y * 16))
    for entity in world["entities"]:
        if entity["id"] in game["removed"][game["map_id"]]:
            if entity["kind"] == "chest":
                canvas.alpha_composite(tile("chest_open"), (entity["x"] * 16, entity["y"] * 16))
            continue
        sprite = entity["sprite"]
        if entity["kind"] == "beacon" and game["result"] == "victory":
            sprite = "beacon_lit"
        canvas.alpha_composite(tile(sprite), (entity["x"] * 16, entity["y"] * 16))
    draw = ImageDraw.Draw(canvas)
    for entity in entities(game):
        if entity["kind"] in {"npc", "fragment", "boss", "exit"}:
            x, y = entity["x"] * 16 + 7, entity["y"] * 16 + 1
            color = "#f3c86d" if entity["kind"] in {"npc", "exit"} else "#6cdee8"
            draw.rectangle((x, y, x + 1, y + 1), fill=color)
    p = game["player"]
    canvas.alpha_composite(tile("hero"), (p["x"] * 16, p["y"] * 16))
    draw.line(
        (p["x"] * 16 + 3, p["y"] * 16 + 15, p["x"] * 16 + 12, p["y"] * 16 + 15),
        fill="#ffeeac",
        width=1,
    )
    return canvas.resize((160 * scale, 160 * scale), Image.Resampling.NEAREST)


def battle_scene(game: dict) -> bytes:
    image = Image.new("RGBA", (192, 88), "#171c27")
    draw = ImageDraw.Draw(image)
    for x in range(12):
        for y in range(4, 6):
            image.alpha_composite(tile("dungeon_floor"), (x * 16, y * 16))
    for x in (1, 10):
        image.alpha_composite(tile("torch"), (x * 16, 18))
    image.alpha_composite(tile("hero").resize((48, 48), Image.Resampling.NEAREST), (25, 29))
    enemy = tile(game["combat"]["sprite"])
    image.alpha_composite(enemy.resize((48, 48), Image.Resampling.NEAREST), (122, 29))
    draw.line((28, 78, 70, 78), fill="#f3c86d", width=2)
    draw.line((126, 78, 168, 78), fill="#be6261", width=2)
    return png_bytes(image.resize((768, 352), Image.Resampling.NEAREST))


def title_art() -> bytes:
    # 标题场景同样使用真实地图和角色图块，保持美术一致性。
    from adventure.engine import new_game

    game = new_game()
    game["map_id"] = "ruins"
    game["player"].update(x=5, y=5)
    return png_bytes(scene(game, scale=4))
