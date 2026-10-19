"""按固定页数切分 PDF（默认 200 页/卷，绕过 MinerU 单文件页数限制）。"""

import sys
from pathlib import Path

import pymupdf

src = Path(sys.argv[1])
outdir = Path(sys.argv[2])
chunk = int(sys.argv[3]) if len(sys.argv) > 3 else 200
outdir.mkdir(parents=True, exist_ok=True)

doc = pymupdf.open(src)
total = len(doc)
for i, start in enumerate(range(0, total, chunk), 1):
    end = min(total, start + chunk)
    out = pymupdf.open()
    out.insert_pdf(doc, from_page=start, to_page=end - 1)
    dst = outdir / f"{src.stem}_p{i}.pdf"
    out.save(dst, garbage=4, deflate=True)
    print(dst.name, "pages", end - start, "offset", start, "MB", round(dst.stat().st_size / 1048576, 1))
