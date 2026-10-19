"""生成 MinerU 与现有 OCR 的抽样对照（供人工快速验收）。"""

import sys
from pathlib import Path

PROJECT = Path(r"D:\考研备考\专业课资料\专业课记忆站")
sys.path.insert(0, str(PROJECT))
import ocr_index as ocr  # noqa: E402

ROOT = Path(r"D:\考研备考\MinerU\structured")
CASES = [
    ("宁骚", "ning-3", 159, "政策工具定义与分类"),
    ("陈振明", "chen-2", 179, "内部性与政府扩张"),
    ("蔡王", "cai-wang-3", 88, "公共组织六特征"),
    ("谢明", "xie-intro-5", 31, "公地悲剧"),
]

lines = ["# MinerU 抽样对照", "",
         "每页左为 MinerU 结构化文本（已去页眉页脚），右为现有 RapidOCR 文本（截断）。", ""]
for book, ocr_id, page, title in CASES:
    m = (ROOT / book / "pages" / f"{page:04d}.txt").read_text(encoding="utf-8").strip()
    old = " ".join(ocr.book(ocr_id).page(page).split())
    lines += [f"## {book} p{page}：{title}", "",
              "**MinerU**", "", m[:900], "",
              "**现有 OCR**", "", old[:900], "", "---", ""]
(Path(r"D:\考研备考\MinerU\samples.md")).write_text("\n".join(lines), encoding="utf-8")
print("wrote samples.md")
