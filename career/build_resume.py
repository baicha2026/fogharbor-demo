"""把已确认信息的 Markdown 草稿转为 HTML 和可编辑 DOCX，无第三方依赖。"""

from __future__ import annotations

import html
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "技术策划简历.md"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ET.register_namespace("w", W)


def blocks(text: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "---":
            result.append(("rule", ""))
        elif line.startswith("## "):
            result.append(("section", line[3:]))
        elif line.startswith("# "):
            result.append(("title", line[2:]))
        elif line.startswith("- "):
            result.append(("bullet", line[2:]))
        else:
            result.append(("paragraph", line))
    return result


def inline_html(value: str) -> str:
    parts = re.split(r"(\*\*.*?\*\*)", value)
    return "".join(
        "<strong>" + html.escape(p[2:-2]) + "</strong>"
        if p.startswith("**") and p.endswith("**")
        else html.escape(p)
        for p in parts
    )


def make_html(items: list[tuple[str, str]]) -> str:
    rendered = []
    in_list = False
    after_rule = False
    for kind, value in items:
        if kind != "bullet" and in_list:
            rendered.append("</ul>")
            in_list = False
        if kind == "bullet":
            if not in_list:
                rendered.append("<ul>")
                in_list = True
            rendered.append(f"<li>{inline_html(value)}</li>")
        elif kind == "rule":
            rendered.append("<hr>")
            after_rule = True
        else:
            tag = {"title": "h1", "section": "h2"}.get(kind, "p")
            attr = ' class="footnote"' if after_rule else ""
            rendered.append(f"<{tag}{attr}>{inline_html(value)}</{tag}>")
    if in_list:
        rendered.append("</ul>")
    content = "\n".join(rendered)
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>技术策划 / 战斗 / 关卡 / 任务策划简历</title>
<style>
:root{color-scheme:light;--ink:#232c36;--muted:#667180;--line:#dce1e6;--accent:#aa773b}
*{box-sizing:border-box}body{margin:0;background:#edf0f3;color:var(--ink);font-family:sans-serif;font-size:13px;line-height:1.72}
.sheet{max-width:794px;margin:28px auto;padding:38px 48px 32px;background:white;border-top:5px solid var(--accent);box-shadow:0 5px 24px #25324412}
.draft{font-size:10px;letter-spacing:1.6px;color:var(--muted);margin:0 0 6px}
h1{font-size:29px;line-height:1.3;letter-spacing:1px;margin:0 0 12px}
h2{font-size:15px;margin:22px 0 9px;padding-bottom:5px;border-bottom:1px solid var(--line);page-break-after:avoid}
p{margin:5px 0}ul{padding-left:18px;margin:8px 0}li{padding-left:3px;margin:7px 0;break-inside:avoid}
strong{font-weight:700}hr{border:0;border-top:1px solid var(--line);margin-top:24px}.footnote{font-size:10px;line-height:1.5;color:var(--muted)}
@page{size:A4;margin:12mm} @media print{body{background:white;font-size:11px;line-height:1.6}.sheet{margin:0;padding:8px 6px 0;max-width:none;box-shadow:none}h1{font-size:25px}h2{margin-top:17px}li{margin:5px 0}}
@media(max-width:600px){.sheet{margin:0;padding:26px 22px}.draft{letter-spacing:.5px}h1{font-size:26px}}
</style></head><body><main class="sheet"><p class="draft">RESUME DRAFT · 游戏策划</p>
""" + content + "\n</main></body></html>\n"


def child(parent: ET.Element, tag: str, **attrs: str) -> ET.Element:
    return ET.SubElement(parent, f"{{{W}}}{tag}", {f"{{{W}}}{k}": v for k, v in attrs.items()})


def xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def make_docx(items: list[tuple[str, str]], target: Path) -> None:
    document = ET.Element(f"{{{W}}}document")
    body = child(document, "body")
    after_rule = False
    for kind, value in items:
        if kind == "rule":
            after_rule = True
            continue
        paragraph = child(body, "p")
        props = child(paragraph, "pPr")
        style = {"title": "Title", "section": "Heading1"}.get(kind, "Normal")
        child(props, "pStyle", val="Footnote" if after_rule else style)
        if kind == "section":
            child(props, "keepNext")
        if kind == "bullet":
            child(props, "ind", left="200", hanging="180")
            value = "• " + value
        for part in re.split(r"(\*\*.*?\*\*)", value):
            if not part:
                continue
            run = child(paragraph, "r")
            if part.startswith("**") and part.endswith("**"):
                child(child(run, "rPr"), "b")
                part = part[2:-2]
            text_node = child(run, "t")
            text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            text_node.text = part
    section = child(body, "sectPr")
    child(section, "pgSz", w="11906", h="16838")
    child(section, "pgMar", top="780", right="900", bottom="780", left="900", header="360", footer="360", gutter="0")

    styles = ET.Element(f"{{{W}}}styles")
    defaults = child(styles, "docDefaults")
    rp = child(child(defaults, "rPrDefault"), "rPr")
    child(rp, "rFonts", ascii="Calibri", hAnsi="Calibri", eastAsia="Microsoft YaHei")
    child(rp, "sz", val="20")
    child(rp, "lang", val="zh-CN", eastAsia="zh-CN")
    pp = child(child(defaults, "pPrDefault"), "pPr")
    child(pp, "spacing", after="100", line="280", lineRule="auto")
    for style_id, size, color, before in [
        ("Normal", "20", "232C36", "0"),
        ("Title", "44", "232C36", "0"),
        ("Heading1", "24", "76502B", "230"),
        ("Footnote", "16", "667180", "120"),
    ]:
        style = child(styles, "style", type="paragraph", styleId=style_id)
        if style_id == "Normal":
            style.set(f"{{{W}}}default", "1")
        child(style, "name", val=style_id)
        if style_id != "Normal":
            child(style, "basedOn", val="Normal")
        child(child(style, "pPr"), "spacing", before=before, after="100")
        run_props = child(style, "rPr")
        child(run_props, "sz", val=size)
        child(run_props, "color", val=color)
        if style_id in {"Title", "Heading1"}:
            child(run_props, "b")

    content_types = b'''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''
    package_rels = b'''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    doc_rels = b'''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("word/document.xml", xml_bytes(document))
        archive.writestr("word/styles.xml", xml_bytes(styles))
        archive.writestr("word/_rels/document.xml.rels", doc_rels)


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    items = blocks(text)
    page = make_html(items)
    (HERE / "技术策划简历.html").write_text(page, encoding="utf-8")
    target = HERE / "技术策划简历.docx"
    make_docx(items, target)
    with ZipFile(target) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            ET.fromstring(archive.read(name))
        root = ET.fromstring(archive.read("word/document.xml"))
        actual = "".join(n.text or "" for n in root.iter(f"{{{W}}}t"))
    for required in ["3000+", "Python（基础）", "FastAPI", "Vibe Coding", "ComfyUI", "具体职责待确认"]:
        assert required in actual and required in page, required
    print("已生成并核对文字与DOCX文件结构：")
    for path in [target, HERE / "技术策划简历.html", SOURCE, HERE / "岗位匹配说明.md"]:
        print(path, path.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
