"""将核实过的官方CC0素材下载到项目，不使用系统临时目录。"""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://kenney.nl/assets/tiny-dungeon"
URL = (
    "https://kenney.nl/media/pages/assets/tiny-dungeon/"
    "f8422efb44-1674742415/kenney_tiny-dungeon.zip"
)
EXPECTED_SHA256 = "c109438ab06f65fd80f9b2686a4cf9c7c11dc64444b47333ec71d602f8bb5fc7"


def main() -> None:
    output = (ROOT / "assets" / "kenney").resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive_file = output / "tiny-dungeon.zip"
    if archive_file.exists():
        data = archive_file.read_bytes()
    else:
        response = httpx.get(URL, follow_redirects=True, timeout=40)
        response.raise_for_status()
        data = response.content
        archive_file.write_bytes(data)
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("素材包校验值与已核实版本不同，停止解压。")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.infolist():
            target = (output / member.filename).resolve()
            if not target.is_relative_to(output):
                raise ValueError("素材压缩包路径超出项目素材目录")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(member))
    metadata = {
        "author": "Kenney",
        "pack": "Tiny Dungeon 1.0",
        "license": "CC0-1.0",
        "source": SOURCE,
        "download": URL,
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    (output / "source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    tiles = sorted((output / "Tiles").glob("*.png"))
    sheet = Image.new("RGB", (13 * 84, ((len(tiles) + 12) // 13) * 94), "#222638")
    draw = ImageDraw.Draw(sheet)
    for i, tile in enumerate(tiles):
        img = Image.open(tile).convert("RGBA").resize((64, 64), Image.Resampling.NEAREST)
        x, y = (i % 13) * 84 + 10, (i // 13) * 94 + 4
        sheet.paste(img, (x, y), img)
        draw.text((x, y + 68), tile.stem.removeprefix("tile_"), fill="white")
    (ROOT / "artifacts").mkdir(exist_ok=True)
    sheet.save(ROOT / "artifacts" / "tiny-dungeon-contact-sheet.png")
    print(f"Downloaded {len(tiles)} CC0 tiles to {output}; sha256={metadata['sha256']}")


if __name__ == "__main__":
    main()
