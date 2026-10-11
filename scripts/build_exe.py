"""所有构建缓存与输出保存在E盘项目目录；打包不读取或复制真实.env。"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime_paths import configure_local_paths  # noqa: E402


def main() -> int:
    configure_local_paths()
    os.environ["PYINSTALLER_CONFIG_DIR"] = str(ROOT / ".runtime" / "pyinstaller")
    (ROOT / ".runtime" / "bundle").mkdir(parents=True, exist_ok=True)
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (64, 64), "#131c23")
    ImageDraw.Draw(image).rounded_rectangle((1, 1, 62, 62), radius=9, outline="#d7b56d", width=3)
    with Image.open(ROOT / "assets" / "kenney" / "Tiles" / "tile_0099.png") as hero:
        hero = hero.convert("RGBA").resize((48, 48), Image.Resampling.NEAREST)
        image.alpha_composite(hero, (8, 8))
    image.resize((256, 256), Image.Resampling.NEAREST).save(
        ROOT / "assets" / "fogharbor.ico",
        sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--distpath",
            str(ROOT / "dist"),
            "--workpath",
            str(ROOT / ".runtime" / "build"),
            str(ROOT / "packaging" / "fogharbor.spec"),
        ],
        cwd=ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
