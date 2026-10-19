"""MinerU 在线精准解析 API 的最小客户端（批量上传 → 轮询 → 下载）。

用法（token 放环境变量，不写进文件）：
    $env:MINERU_TOKEN = "..."
    python tools/mineru_client.py submit <pdf> [--name 名称] [--model vlm]
    python tools/mineru_client.py poll <batch_id>
    python tools/mineru_client.py fetch <batch_id> <outdir>

本文件只做「取回结构化底稿」，不改站点 OCR 与 index.html（路线 A）。
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import requests

BASE = "https://mineru.net/api/v4"
TOKEN = os.environ.get("MINERU_TOKEN", "").strip()


def headers():
    if not TOKEN:
        raise SystemExit("缺少 MINERU_TOKEN 环境变量")
    return {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}


def submit(pdf: Path, name: str | None = None, model: str = "vlm", pages: str | None = None):
    payload = {
        "files": [{"name": name or pdf.name, "data_id": pdf.stem[:64]}],
        "model_version": model,
        "is_ocr": True,
        "enable_table": True,
        "enable_formula": True,
        "language": "ch",
    }
    if pages:
        payload["page_ranges"] = pages
    r = requests.post(f"{BASE}/file-urls/batch", headers=headers(), json=payload, timeout=60)
    print("apply:", r.status_code, r.text[:500])
    data = r.json()
    if data.get("code") != 0:
        raise SystemExit("申请上传链接失败")
    batch_id = data["data"]["batch_id"]
    urls = data["data"]["file_urls"]
    for url in urls:
        with pdf.open("rb") as fh:
            up = requests.put(url, data=fh, timeout=600)
        print("upload:", up.status_code)
        if up.status_code != 200:
            raise SystemExit("上传失败")
    print(json.dumps({"batch_id": batch_id, "file": str(pdf), "pages": pages}, ensure_ascii=False))
    return batch_id


def submit_many(pdfs: list[Path], model: str = "vlm"):
    """一个批次上传多份 PDF；返回 batch_id。"""
    payload = {
        "files": [{"name": p.name, "data_id": p.stem[:64]} for p in pdfs],
        "model_version": model,
        "is_ocr": True,
        "enable_table": True,
        "enable_formula": True,
        "language": "ch",
    }
    r = requests.post(f"{BASE}/file-urls/batch", headers=headers(), json=payload, timeout=120)
    print("apply:", r.status_code, r.text[:400], flush=True)
    data = r.json()
    if data.get("code") != 0:
        raise SystemExit("申请上传链接失败")
    batch_id = data["data"]["batch_id"]
    urls = data["data"]["file_urls"]
    for pdf, url in zip(pdfs, urls):
        with pdf.open("rb") as fh:
            up = requests.put(url, data=fh, timeout=1800)
        print("upload:", pdf.name, up.status_code, flush=True)
        if up.status_code != 200:
            raise SystemExit("上传失败：" + pdf.name)
    print("BATCH_ID", batch_id, flush=True)
    return batch_id


def poll(batch_id: str, wait: bool = True, interval: int = 15):
    url = f"{BASE}/extract-results/batch/{batch_id}"
    while True:
        r = requests.get(url, headers=headers(), timeout=60)
        print("poll:", r.status_code, r.text[:800], flush=True)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("code") != 0:
            return None
        results = data.get("data", {}).get("extract_result", [])
        states = [x.get("state") for x in results]
        if results and all(s in ("done", "failed") for s in states):
            return results
        if not wait:
            return results
        time.sleep(interval)


def fetch(batch_id: str, outdir: Path, wait: bool = True):
    results = poll(batch_id, wait=wait)
    if not results:
        raise SystemExit("没有取到结果")
    outdir.mkdir(parents=True, exist_ok=True)
    for item in results:
        name = item.get("file_name", "result")
        if item.get("state") != "done":
            print("failed:", name, item.get("err_msg"))
            continue
        zip_url = item.get("full_zip_url")
        if not zip_url:
            print("no zip:", name)
            continue
        r = requests.get(zip_url, timeout=600)
        target = outdir / (Path(name).stem + ".zip")
        target.write_bytes(r.content)
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            zf.extractall(outdir / Path(name).stem)
        print("saved:", target, "->", outdir / Path(name).stem)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("pdf")
    s.add_argument("--name")
    s.add_argument("--model", default="vlm")
    s.add_argument("--pages")
    p = sub.add_parser("poll")
    p.add_argument("batch_id")
    p.add_argument("--no-wait", action="store_true")
    f = sub.add_parser("fetch")
    f.add_argument("batch_id")
    f.add_argument("outdir")
    args = ap.parse_args()

    if args.cmd == "submit":
        pid = submit(Path(args.pdf), args.name, args.model, args.pages)
        print("BATCH_ID", pid)
    elif args.cmd == "poll":
        res = poll(args.batch_id, wait=not args.no_wait)
        print(json.dumps(res, ensure_ascii=False, indent=2) if res else "NO RESULT")
    else:
        fetch(args.batch_id, Path(args.outdir))


if __name__ == "__main__":
    sys.exit(main())
