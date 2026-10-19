"""从 MinerU layout 未跨页合并块生成逐页底稿，不覆盖旧 OCR。

content_list / para_blocks 会把跨页段落提前，不能用于 PDF 页码回查。
"""
import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
import ocr_index

BOOKS = {"蔡王": "cai-wang-3", "陈振明": "chen-2", "宁骚": "ning-3", "谢明": "xie-intro-5"}


def block_text(block):
    chunks = []
    for line in block.get("lines", []):
        spans = []
        for span in line.get("spans", []):
            text = span.get("content") or span.get("html") or ""
            if span.get("html"):
                text = html.unescape(re.sub(r"<[^>]+>", " ", text))
            spans.append(text)
        chunks.append("".join(spans))
    chunks.extend(block_text(child) for child in block.get("blocks", []))
    return "\n".join(s for s in chunks if s.strip())


def collect(root):
    parts = json.loads((root / "parts.json").read_text(encoding="utf-8"))
    pages = {ident: {} for ident in BOOKS.values()}
    origins = {ident: [] for ident in BOOKS.values()}
    for task, part in parts.items():
        ident = BOOKS[part["book"]]
        path = root / part["book"] / task / "layout.json"
        raw = path.read_bytes()
        data = json.loads(raw)
        origins[ident].append({"file": str(path.relative_to(root)), "sha256": hashlib.sha256(raw).hexdigest(),
                               "offset": part["offset"], "pages": len(data["pdf_info"]), "pdf": part["source"]})
        for page in data["pdf_info"]:
            number = part["offset"] + page["page_idx"] + 1
            if number in pages[ident]:
                raise ValueError(f"重复页：{ident} {number}")
            blocks = page["preproc_blocks"] + [b for b in page.get("discarded_blocks", [])
                                                   if b["type"] == "page_footnote"]
            blocks.sort(key=lambda b: b.get("index", 0))
            pages[ident][number] = "\n\n".join(filter(None, (block_text(b) for b in blocks)))
    for ident, book_pages in pages.items():
        if sorted(book_pages) != list(range(1, len(book_pages) + 1)) or not book_pages:
            raise ValueError(f"页码不连续：{ident}")
    return pages, origins


def main(root):
    pages, origins = collect(root)
    inventory = json.loads(ocr_index.INVENTORY.read_text(encoding="utf-8"))
    output = PROJECT / "sources" / "mineru"
    for meta in inventory:
        if meta["id"] in pages and len(pages[meta["id"]]) != meta["ocrPages"]:
            raise ValueError(f"{meta['id']} 页数变化，请核对 PDF 版本后再迁移")
    output.mkdir(parents=True, exist_ok=True)
    for meta in inventory:
        ident = meta["id"]
        if ident not in pages:
            continue
        path = output / f"{ident}.md"
        content = f"# {meta['title']} · MinerU 逐页文本\n\n" + "\n\n".join(
            f"## 第 {n} 页\n\n{pages[ident][n]}" for n in sorted(pages[ident])) + "\n"
        path.write_text(content, encoding="utf-8")
        meta.setdefault("legacyOcrPath", meta["ocrPath"])
        meta.setdefault("legacySha256", meta["sha256"])
        meta.update(ocrPath=path.relative_to(PROJECT.parent).as_posix(),
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    engine="MinerU", extraction="layout.preproc_blocks + page_footnote",
                    pageMarker="PDF 第 N 页（从封面起算；不是纸书页码）",
                    reviewStatus="quote-checked")
        meta.pop("paperPageRule", None)
        print(f"{ident}: {len(pages[ident])} 页 → {path.relative_to(PROJECT)}")
    (output / "provenance.json").write_text(json.dumps(origins, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ocr_index.INVENTORY.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=PROJECT.parents[1] / "MinerU")
    main(parser.parse_args().root)
