"""生成 MinerU 底稿的质量报告：页级相似度、结构统计、站点引文可匹配率（旧 OCR 与逐页 MinerU 的迁移评估）。"""

from __future__ import annotations

import json
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

PROJECT = Path(r"D:\考研备考\专业课资料\专业课记忆站")
ROOT = Path(r"D:\考研备考\MinerU")
sys.path.insert(0, str(PROJECT))

import build_site as site  # noqa: E402
import ocr_index as ocr  # noqa: E402
from course import policy  # noqa: E402
from mineru_to_ocr import collect  # noqa: E402

BOOKS = {
    "蔡王": "cai-wang-3",
    "陈振明": "chen-2",
    "宁骚": "ning-3",
    "谢明": "xie-intro-5",
}
SRC2BOOK = {v: k for k, v in BOOKS.items()}


def norm(s: str) -> str:
    return "".join(ch for ch in s if ch.isalnum())


def load_mineru(book: str):
    base = ROOT / "structured" / book
    pages = {}
    types = Counter()
    headings = []
    for line in (base / "pages.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        parts = []
        for b in rec["blocks"]:
            types[b["type"]] += 1
            if b["type"] in ("page_header", "page_footer"):
                continue
            if b["text"]:
                parts.append(b["text"])
            if b["type"] == "title" and b["text"]:
                headings.append((rec["page"], b.get("level") or 1, b["text"]))
        pages[rec["page"]] = "\n".join(parts)
    tables = sum(1 for _ in (base / "tables.jsonl").read_text(encoding="utf-8").splitlines())
    figs = sum(1 for _ in (base / "figures.jsonl").read_text(encoding="utf-8").splitlines())
    # 正式回查必须使用未合并页的 layout，不使用 structured 中提前到前页的段落。
    pages = collect(ROOT)[0][BOOKS[book]]
    return pages, types, headings, tables, figs


def evidence_refs():
    refs = []
    for lesson in site.LESSON_POOL.values():
        for e in lesson.get("evidence", []):
            if e.get("src") in SRC2BOOK:
                refs.append((e["src"], e["pages"], e["quote"]))
        dual = lesson.get("dual") or {}
        for e in dual.get("evidence", []) if isinstance(dual, dict) else []:
            if e.get("src") in SRC2BOOK:
                refs.append((e["src"], e["pages"], e["quote"]))
    for refs_for_lesson in site.CHEN_EVIDENCE.values():
        for e in refs_for_lesson:
            if e.get("src") in SRC2BOOK:
                refs.append((e["src"], e["pages"], e["quote"]))
    for lesson in policy.LESSONS:
        for e in lesson.get("evidence", []):
            if e.get("src") in SRC2BOOK:
                refs.append((e["src"], e["pages"], e["quote"]))
    return refs


def main():
    refs = evidence_refs()
    lines = ["# MinerU 结构化底稿质量报告", "",
             "当前站点已使用逐页 MinerU 底稿；比较对象为保留的旧 OCR。相似度不是准确率，结构统计仍来自原始结构化导出。", ""]
    overall = []
    for book, ocr_id in BOOKS.items():
        base = ROOT / "structured" / book
        if not (base / "pages.jsonl").exists():
            continue
        m_pages, types, headings, tables, figs = load_mineru(book)
        meta = json.loads((base / "book.json").read_text(encoding="utf-8"))
        headings = meta.get("headings", headings)
        equations = types.get("equation_interline", 0) + types.get("equation_inline", 0)
        old_meta = next(m for m in json.loads(ocr.INVENTORY.read_text(encoding="utf-8")) if m["id"] == ocr_id)
        old_meta = {**old_meta, "ocrPath": old_meta.get("legacyOcrPath", old_meta["ocrPath"]),
                    "sha256": old_meta.get("legacySha256", old_meta["sha256"])}
        old = ocr.Book(old_meta)
        n = min(max(m_pages), len(old.pages))
        ratios = []
        for page in range(1, n + 1):
            a, b = norm(m_pages.get(page, "")), norm(old.page(page))
            if a or b:
                ratios.append(SequenceMatcher(None, a, b).ratio())
        avg = sum(ratios) / len(ratios) if ratios else 0
        low = [i + 1 for i, r in enumerate(ratios) if r < 0.75]
        book_refs = [r for r in refs if r[0] == ocr_id]
        hit = 0
        misses = []
        for src, pages, quote in book_refs:
            q = ocr.normalize(quote)
            ok = any(q and q in ocr.normalize(m_pages.get(int(p), "")) for p in pages)
            if ok:
                hit += 1
            else:
                misses.append((pages, quote[:30]))
        overall.append((book, n, avg, len(low), len(book_refs), hit))
        lines += [
            f"## {book}",
            "",
            f"- 页数：{n}；页级平均相似度：**{avg:.3f}**；相似度 < 0.75 的页：{len(low)} 页"
            + (f"（最差：{low[:8]}）" if low else ""),
            f"- 结构：标题 {len(headings)} 个；表格 {tables} 个；图片 {figs} 个；公式 {equations} 个；块类型 {dict(types.most_common(8))}",
            f"- 站点引文：{len(book_refs)} 条，MinerU 直接命中 **{hit}** 条"
            + (f"；未命中示例：{misses[:3]}" if misses else ""),
            "",
        ]
    lines += ["## 汇总", "", "| 书 | 页数 | 平均相似度 | 低相似页 | 引文命中 |", "|---|---|---|---|---|"]
    for book, n, avg, low, total, hit in overall:
        lines.append(f"| {book} | {n} | {avg:.3f} | {low} | {hit}/{total} |")
    total_refs = sum(x[4] for x in overall)
    total_hits = sum(x[5] for x in overall)
    lines += ["", f"引文总计：**{total_hits}/{total_refs}** 直接命中"
              f"（{total_hits / total_refs * 100:.1f}%）；严格在声明页码回查，不借用相邻页。", "",
              "低相似页多因页眉/脚注/图内文字与旧 OCR 的切分不同，不代表正文质量差；"
              "抽查样例见 `structured/宁骚/pages/0159.txt`、`structured/陈振明/pages/0179.txt`、"
              "`structured/蔡王/pages/0088.txt`。"]
    (ROOT / "quality-report.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", ROOT / "quality-report.md")


if __name__ == "__main__":
    main()
