"""把一个批次的若干 PDF 提交 MinerU，轮询并下载到指定目录。"""

import sys
from pathlib import Path

from mineru_client import fetch, submit_many

out = Path(sys.argv[1])
pdfs = [Path(p) for p in sys.argv[2:]]
bid = submit_many(pdfs, model="vlm")
fetch(bid, out)
print("ALL_DONE", out, flush=True)
