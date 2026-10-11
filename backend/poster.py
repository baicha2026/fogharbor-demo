"""成就海报：调用 ComfyUI，配置不可用时显式生成占位 PNG。"""

import asyncio
import base64
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from backend.comfyui import ComfyUIClient
from backend.errors import ServiceError
from backend.models import Reward
from game.contracts import ArenaReward, PosterResult


def placeholder_poster(item_name: str, notice: str) -> PosterResult:
    image = Image.new("RGB", (900, 540), "#192c32")
    draw = ImageDraw.Draw(image)
    font_file = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "poster.ttf"
    if font_file.is_file():
        title_font = ImageFont.truetype(str(font_file), 30)
        body_font = ImageFont.truetype(str(font_file), 19)
        title = item_name[:20]
        subtitle = "本地占位海报 · 连接 ComfyUI 后可生成概念图"
    else:
        title_font = ImageFont.load_default(size=30)
        body_font = ImageFont.load_default(size=19)
        title, subtitle = "TRIAL ACHIEVEMENT", "PLACEHOLDER / Connect ComfyUI for AI artwork"
    for x in range(30, 900, 60):
        draw.line((x, 0, x, 540), fill="#22363b")
    for y in range(30, 540, 60):
        draw.line((0, y, 900, y), fill="#22363b")
    draw.rectangle((35, 35, 865, 505), outline="#d7b56d", width=2)
    draw.polygon(
        [(450, 80), (535, 130), (535, 220), (450, 270), (365, 220), (365, 130)],
        fill="#304e52",
        outline="#d7b56d",
        width=3,
    )
    draw.polygon(
        [
            (450, 114),
            (470, 160),
            (515, 166),
            (480, 195),
            (492, 239),
            (450, 215),
            (408, 239),
            (420, 195),
            (385, 166),
            (430, 160),
        ],
        fill="#d7b56d",
    )
    draw.text((450, 320), title, font=title_font, fill="#f3eee1", anchor="mm")
    draw.text((450, 385), subtitle, font=body_font, fill="#acc0b7", anchor="mm")
    draw.text((450, 460), "AI TECHNICAL DESIGN ARENA", font=body_font, fill="#d7b56d", anchor="mm")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return PosterResult(
        image_base64=base64.b64encode(buffer.getvalue()).decode("ascii"),
        mime_type="image/png",
        item_name=item_name,
        source="placeholder",
        notice=notice,
    )


async def generate_achievement_poster(client: ComfyUIClient, reward: ArenaReward) -> PosterResult:
    """默认8188；配置/超时错误不影响结算，原因随占位图返回。"""
    try:
        image = await client.generate(Reward(**reward.model_dump(), reputation=0))
        return PosterResult(
            image_base64=image.image_base64,
            mime_type=image.mime_type,
            item_name=image.item_name,
            source="comfyui",
        )
    except ServiceError as exc:
        return await asyncio.to_thread(placeholder_poster, reward.item_name, str(exc))
