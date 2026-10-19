"""把 MinerU 的 content_list_v2 / content_list 转成书级结构化底稿（路线 A，不动站点）。

输入：MinerU 下载目录（每个任务一个子目录，含 *_content_list_v2.json 与 full.md）
输出：MinerU/structured/<book>/
  book.json       书级元数据、页数、分卷、标题树
  pages.jsonl     每页一条：页码、分卷、blocks（type/level/text/bbox）
  pages/NNNN.txt  每页纯文本（便于检索/比对）
  tables.jsonl    表格（HTML 或文本）
  figures.jsonl   图片（路径、图注）
  book.md         合并后的 Markdown（按卷拼接）
用法：
  python tools/mineru_import.py "D:\\考研备考\\MinerU"
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"D:\考研备考\MinerU")
PARTS = json.loads((ROOT / "parts.json").read_text(encoding="utf-8"))
OUT = ROOT / "structured"


def flatten(node) -> str:
    """递归提取 v2 块里的文字 span。"""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(flatten(x) for x in node)
    if isinstance(node, dict):
        if node.get("type") == "text" and isinstance(node.get("content"), str):
            return node["content"]
        for key in ("content", "title_content", "paragraph_content", "table_content",
                    "image_caption", "image_footnote", "equation_content"):
            if key in node:
                return flatten(node[key])
        return ""
    return ""


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "")


def block_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, dict):
        if content.get("html"):
            return strip_tags(content["html"]).strip()
        return flatten(content).strip()
    if isinstance(content, str):
        return content.strip()
    # v1 兼容
    return str(block.get("text", "")).strip()


def find_task_dirs():
    seen = set()
    for pattern in ("*content_list_v2.json", "*content_list.json"):
        for f in ROOT.rglob(pattern):
            parent = f.parent
            if parent in seen or parent.name in ("_smoke", "_split", "_chunks"):
                continue
            seen.add(parent)
            yield parent


def load_pages(task_dir: Path):
    v2 = sorted(task_dir.glob("*content_list_v2.json"))
    if v2:
        pages = json.loads(v2[0].read_text(encoding="utf-8"))
        out = []
        for page in pages:
            blocks = []
            for b in page:
                blocks.append({
                    "type": b.get("type"),
                    "level": (b.get("content") or {}).get("level") if isinstance(b.get("content"), dict) else None,
                    "text": block_text(b),
                    "bbox": b.get("bbox"),
                    "raw": b,
                })
            out.append(blocks)
        return out
    v1 = sorted(task_dir.glob("*content_list.json"))
    if not v1:
        return []
    blocks = json.loads(v1[0].read_text(encoding="utf-8"))
    by_page = defaultdict(list)
    for b in blocks:
        by_page[int(b.get("page_idx", 0))].append({
            "type": b.get("type"),
            "level": None,
            "text": str(b.get("text", "")).strip(),
            "bbox": b.get("bbox"),
            "raw": b,
        })
    return [by_page.get(i, []) for i in range(max(by_page) + 1)] if by_page else []


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    books = defaultdict(list)
    initialized = set()

    for task_dir in find_task_dirs():
        meta = PARTS.get(task_dir.name)
        if not meta:
            print("跳过（parts.json 没有登记）：", task_dir.name)
            continue
        pages = load_pages(task_dir)
        if not pages:
            print("没有 content_list：", task_dir.name)
            continue
        book = meta["book"]
        part = meta["part"]
        offset = meta["offset"]
        target = OUT / book
        target.mkdir(parents=True, exist_ok=True)
        (target / "pages").mkdir(exist_ok=True)
        if book not in initialized:
            for name in ("pages.jsonl", "tables.jsonl", "figures.jsonl"):
                (target / name).unlink(missing_ok=True)
            initialized.add(book)

        with (target / "pages.jsonl").open("a", encoding="utf-8") as pages_f, \
             (target / "tables.jsonl").open("a", encoding="utf-8") as tables_f, \
             (target / "figures.jsonl").open("a", encoding="utf-8") as figs_f:
            for local_idx, blocks in enumerate(pages):
                page_no = offset + local_idx + 1
                text_parts = []
                for b in blocks:
                    t = b["type"]
                    txt = b["text"]
                    if t in ("page_header", "page_footer"):
                        continue
                    if txt:
                        text_parts.append(txt)
                    if t == "table":
                        raw = b["raw"]
                        html = (raw.get("content") or {}).get("html")
                        tables_f.write(json.dumps({
                            "book": book, "page": page_no, "part": part,
                            "text": txt, "html": html, "raw": raw,
                        }, ensure_ascii=False) + "\n")
                    if t in ("image", "figure"):
                        figs_f.write(json.dumps({
                            "book": book, "page": page_no, "part": part,
                            "caption": txt, "raw": b["raw"],
                        }, ensure_ascii=False) + "\n")
                pages_f.write(json.dumps({
                    "book": book, "page": page_no, "part": part,
                    "blocks": [{k: b[k] for k in ("type", "level", "text", "bbox")} for b in blocks],
                }, ensure_ascii=False) + "\n")
                (target / "pages" / f"{page_no:04d}.txt").write_text(
                    "\n".join(text_parts), encoding="utf-8")

        # 卷级 markdown 汇总
        md = task_dir / "full.md"
        if md.exists():
            with (target / f"part{part}.md").open("w", encoding="utf-8") as fh:
                fh.write(md.read_text(encoding="utf-8", errors="replace"))

        books[book].append({"part": part, "offset": offset, "pages": len(pages), "dir": task_dir.name})

    for book, parts in books.items():
        target = OUT / book
        headings = []
        seen = set()
        pages_file = target / "pages.jsonl"
        if pages_file.exists():
            recs = [json.loads(x) for x in pages_file.read_text(encoding="utf-8").splitlines()]
            recs.sort(key=lambda r: r["page"])
            pages_file.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs),
                                  encoding="utf-8")
            for rec in recs:
                for b in rec["blocks"]:
                    if b["type"] == "title" and b["text"]:
                        key = (rec["page"], b["text"])
                        if key in seen:
                            continue
                        seen.add(key)
                        headings.append({"page": rec["page"], "level": b.get("level") or 1,
                                         "text": b["text"]})
        headings.sort(key=lambda x: x["page"])
        # 过滤：只保留章节号、数字编号或常见前后置标题；跨页重复的页眉标题只留第一次
        num_re = re.compile(r"^\d+(\.\d+)*[\s、.．]")
        ch_re = re.compile(r"^第[一二三四五六七八九十百零〇]+[章节篇]")
        front_re = re.compile(r"^(内容简介|作者简介|目录|前言|序|导论|绪论|结语|参考文献|后记|附录|索引)")
        counts = {}
        for h in headings:
            counts[h["text"]] = counts.get(h["text"], 0) + 1
        filtered = []
        seen_text = set()
        for h in headings:
            text = h["text"]
            keep = num_re.match(text) or ch_re.match(text) or front_re.match(text)
            if not keep:
                continue
            if counts[text] > 5 and text in seen_text:
                continue
            seen_text.add(text)
            filtered.append(h)
        all_headings = headings
        headings = filtered
        merged_md = []
        for part in sorted(parts, key=lambda x: x["part"]):
            md_path = target / f"part{part['part']}.md"
            if md_path.exists():
                merged_md.append(f"\n\n<!-- part {part['part']} (offset {part['offset']}) -->\n\n")
                merged_md.append(md_path.read_text(encoding="utf-8"))
        (target / "book.md").write_text("".join(merged_md), encoding="utf-8")
        meta = {
            "book": book,
            "parts": sorted(parts, key=lambda x: x["part"]),
            "pages": max(p["offset"] + p["pages"] for p in parts),
            "headings": headings,
            "headings_all": all_headings,
        }
        (target / "book.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{book}: {meta['pages']} 页，{len(headings)} 个标题，{len(parts)} 卷")


if __name__ == "__main__":
    sys.exit(main())
