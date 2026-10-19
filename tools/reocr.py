"""用 RapidOCR 重新识别教材 PDF，输出与旧 OCR 同样格式的分页 Markdown。

旧 OCR 的毛病是字级误识（入→人、古→占、鼎→灿、了→r、非→卜 等），
一句引文里错两三个字就没法直接当依据给学生看。这个脚本按页渲染（200 dpi）
重做识别，每页写 `## 第 N 页`，N 用 PDF 页码，方便和书本对页。

可断点续跑：每 20 页的识别结果落一个 JSON，重跑会跳过已完成的块。

用法：
    python tools/reocr.py chen  --pdf "公共管理/公共管理学陈振明.pdf" --out "OCR全文/陈振明-公共管理学-第二版.md"
    python tools/reocr.py cai   --pdf "公共管理/公共管理学蔡王第三版.pdf" --out "OCR全文/蔡立辉王乐夫-公共管理学-第3版.md"
"""

import argparse
import json
import multiprocessing as mp
import re
import sys
import time
from pathlib import Path

import pymupdf

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT.parent
CACHE = WORKSPACE / "OCR全文" / "_reocr-cache"


_ENGINE = None
_DOC = None
_DPI = 200
_TAG = ""


def init_worker(pdf, dpi, tag, threads=4):
    global _ENGINE, _DOC, _DPI, _TAG
    # onnxruntime 默认按物理核数开线程；多进程并行时会互相抢占，
    # 先把每个会话的线程数压下来，再开 4 个进程才是净收益。
    import onnxruntime as ort

    class LimitedSessionOptions(ort.SessionOptions):
        def __init__(self):
            super().__init__()
            self.intra_op_num_threads = threads
            self.inter_op_num_threads = 1

    ort.SessionOptions = LimitedSessionOptions
    from rapidocr_onnxruntime import RapidOCR
    _ENGINE = RapidOCR()
    _DOC = pymupdf.open(pdf)
    _DPI = dpi
    _TAG = tag


def worker(args):
    start, end, chunk_file = args
    out = {}
    for i in range(start, end):
        pix = _DOC[i].get_pixmap(dpi=_DPI)
        img = WORKSPACE / "OCR全文" / f"_reocr-tmp-{_TAG}-{i}.png"
        pix.save(img)
        try:
            result, _ = _ENGINE(str(img))
            lines = [item[1] for item in result] if result else []
        finally:
            img.unlink(missing_ok=True)
        out[i + 1] = lines
    Path(chunk_file).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return (start, end)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=10)
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()

    pdf = (PROJECT.parent / args.pdf).resolve()
    if not pdf.exists():
        raise SystemExit(f"找不到 PDF：{pdf}")
    doc = pymupdf.open(pdf)
    total = len(doc)
    CACHE.mkdir(parents=True, exist_ok=True)

    jobs = []
    for start in range(0, total, args.chunk):
        end = min(total, start + args.chunk)
        chunk_file = CACHE / f"{args.tag}-{start:04d}-{end:04d}.json"
        if chunk_file.exists():
            continue
        jobs.append((start, end, str(chunk_file)))

    print(f"{args.tag}: {total} 页，待识别 {len(jobs)} 块（每块 {args.chunk} 页，{args.workers} 进程）")
    if jobs:
        started = time.time()
        with mp.Pool(processes=args.workers, initializer=init_worker,
                     initargs=(str(pdf), args.dpi, args.tag, args.threads)) as pool:
            for done, _ in enumerate(pool.imap_unordered(worker, jobs), 1):
                print(f"  完成 {done}/{len(jobs)} 块，用时 {round(time.time() - started)}s", flush=True)

    pages = {}
    for chunk_file in sorted(CACHE.glob(f"{args.tag}-*.json")):
        pages.update({int(k): v for k, v in json.loads(chunk_file.read_text(encoding="utf-8")).items()})

    missing = [n for n in range(1, total + 1) if n not in pages]
    if missing:
        raise SystemExit(f"还缺 {len(missing)} 页（例：{missing[:5]}），重跑本命令续做")

    out_path = PROJECT.parent / args.out
    with out_path.open("w", encoding="utf-8") as fh:
        for n in range(1, total + 1):
            fh.write(f"\n## 第 {n} 页\n\n")
            text = "\n".join(pages[n]).strip()
            fh.write(text + "\n")
    chars = sum(len("".join(v)) for v in pages.values())
    print(f"已写入 {out_path.name}：{total} 页，{chars} 字")
    return 0


if __name__ == "__main__":
    sys.exit(main())
