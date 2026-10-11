# 美术素材与授权记录

游戏使用 **Kenney Tiny Dungeon 1.0** 的16×16像素角色、敌人、地砖、墙、箱子、药剂和装饰图块。

| 项目 | 记录 |
| --- | --- |
| 作者 | Kenney / [kenney.nl](https://kenney.nl) |
| 素材页面 | [Tiny Dungeon](https://kenney.nl/assets/tiny-dungeon) |
| 官方下载 | [kenney_tiny-dungeon.zip](https://kenney.nl/media/pages/assets/tiny-dungeon/f8422efb44-1674742415/kenney_tiny-dungeon.zip) |
| 授权 | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| 原始许可 | [kenney/License.txt](kenney/License.txt) |
| 机器来源清单 | [kenney/source.json](kenney/source.json) |
| ZIP SHA256 | `c109438ab06f65fd80f9b2686a4cf9c7c11dc64444b47333ec71d602f8bb5fc7` |

官方许可写明：“This content is free to use in personal, educational and commercial projects.” 署名不是强制条件，本项目在标题、游戏页底与README中保留作者署名。官方页面标注130素材，实际包内 `Tiles/` 有132个PNG文件。

图块随项目本地保存，运行中无需请求素材网站。下载工具 `scripts/fetch_game_assets.py` 将ZIP保存在此目录，校验解压路径在目标目录内，保存许可证及SHA256并生成本地联系图 `artifacts/tiny-dungeon-contact-sheet.png`。

游戏采用最近邻放大并重新组合场景。具体使用编号定义在 `adventure/content.py` 的 `SPRITES`：莉亚99、洛恩100、艾芙84、三守卫123/108/121、首领110，其余地图物件同表。角色名字、对话、剧情、关卡布局与数值规则为原创内容。

`fonts/poster.ttf` 是可选的自备中文字体位置，目前未附加字体素材。海报默认使用Pillow内置字体，不读取Windows系统字体目录。
