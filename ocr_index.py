"""按页检索本地教材 OCR，供备课与构建时的教材依据校验使用。

OCR 文件每页以 `## 第 N 页` 开头。N 是 PDF 页序，不是纸书页码。
检索时会把整页的空白全部去掉再比对，因为 OCR 会在句中任意换行。

命令行用法（在本目录运行）：

    python ocr_index.py find cai-wang-3 "公共管理的含义"
    python ocr_index.py page cai-wang-3 30
    python ocr_index.py spread cai-wang-3 30 34
    python ocr_index.py chapters cai-wang-3
"""

import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
WORKSPACE = PROJECT.parent
INVENTORY = PROJECT / "source_inventory.json"
PAGE_HEAD = re.compile(r"^## 第 (\d+) 页\s*$", re.M)


def squeeze(text):
    """去掉全部空白，便于跨行比对 OCR 段落。"""
    return re.sub(r"\s+", "", text or "")


# OCR 的顽固混淆：把「入」认成「人」（归结、切入、进入、纳入……）。
# 这些「人」的组合在书里不会作为词出现，所以统一归一成「入」再比对；
# 引文也走同一个归一，页面显示的引文就不会带着「归人」这种错字。
CONFUSIONS = [
    ("归人", "归入"), ("切人", "切入"), ("进人", "进入"), ("加人", "加入"),
    ("纳人", "纳入"), ("深人", "深入"), ("投人", "投入"), ("列人", "列入"),
    ("导人", "导入"), ("融人", "融入"), ("介人", "介入"), ("卷人", "卷入"),
    ("编人", "编入"), ("输人", "输入"), ("侵人", "侵入"), ("潜人", "潜入"),
    ("渗人", "渗入"), ("植人", "植入"), ("嵌人", "嵌入"), ("录人", "录入"),
    ("人门", "入门"), ("人党", "入党"), ("人学", "入学"), ("人伍", "入伍"),
    ("人股", "入股"), ("人库", "入库"), ("人账", "入账"),
    ("儿个", "几个"), ("自前", "目前"),
]


def normalize(text):
    """去空白 + 修正已知的「入／人」混淆，正文与引文用同一套规则。"""
    out = squeeze(text)
    for wrong, right in CONFUSIONS:
        out = out.replace(wrong, right)
    return out


def resolve_path(raw):
    """清单里存相对路径（相对工作区），挪目录或换机器都不会失效。"""
    path = Path(raw)
    if path.is_absolute() and path.exists():
        return path
    for candidate in (WORKSPACE / raw, PROJECT / raw):
        if candidate.exists():
            return candidate
    raise SystemExit(f"找不到 OCR 文件：{raw}（已在 {WORKSPACE} 下按相对路径查找）")


class Book:
    def __init__(self, meta):
        self.id = meta["id"]
        self.title = meta["title"]
        self.short = meta.get("short", self.title)
        self.subject = meta.get("subject")
        self.engine = meta.get("engine", "原 OCR")
        self.path = resolve_path(meta["ocrPath"])
        raw = self.path.read_bytes()
        if meta.get("sha256") and hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            raise ValueError(f"教材文本哈希变化，请先核对修改并刷新 source_inventory.py：{self.path}")
        text = raw.decode("utf-8")
        parts = PAGE_HEAD.split(text)
        self.pages = {}
        for i in range(1, len(parts) - 1, 2):
            self.pages[int(parts[i])] = parts[i + 1]
        markers = [int(parts[i]) for i in range(1, len(parts) - 1, 2)]
        if markers != list(range(1, meta["ocrPages"] + 1)):
            raise ValueError(f"OCR 页码缺失、重复或与清单不符: {self.path}")
        self._flat = {n: normalize(body) for n, body in self.pages.items()}

    def page(self, n):
        return self.pages.get(n, "")

    def find(self, phrase):
        """返回包含该段落的 OCR 页码（已去空白后比对）。"""
        needle = normalize(phrase)
        if not needle:
            return []
        return [n for n in sorted(self._flat) if needle in self._flat[n]]

    def find_all(self, phrases):
        """每个短语各自命中的页码；任一未命中即为 None。"""
        hits = [self.find(p) for p in phrases]
        return None if any(not h for h in hits) else hits

    def quote_on(self, pages, quote):
        """校验 quote 是否出现在给定页码范围内（去空白后比对）。"""
        needle = normalize(quote)
        if not needle:
            return False
        return any(needle in self._flat.get(n, "") for n in pages)

    def chapters(self):
        """按页眉里的“第N章 章名”切分章节，返回 [{no, name, start, end}]。"""
        head = re.compile(r"第(\d{1,2})章([\u4e00-\u9fa5]{2,12})")
        found = []
        for n in sorted(self.pages):
            first_lines = [l.strip() for l in self.pages[n].split("\n")[:4] if l.strip()]
            for line in first_lines:
                m = head.search(line)
                if m and not line.startswith("表") and "目录" not in line:
                    found.append((n, int(m.group(1)), m.group(2)))
                    break
        merged = []
        for page, no, name in found:
            if merged and merged[-1]["no"] == no:
                if len(name) > len(merged[-1]["name"]):
                    merged[-1]["name"] = name
                merged[-1]["end"] = page
            else:
                merged.append({"no": no, "name": name, "start": page, "end": page})
        return merged


_CACHE = {}


def books():
    if not _CACHE:
        for meta in json.loads(INVENTORY.read_text(encoding="utf-8")):
            _CACHE[meta["id"]] = Book(meta)
    return _CACHE


def book(ident):
    all_books = books()
    if ident not in all_books:
        raise SystemExit(f"未知教材: {ident}，可选: {', '.join(all_books)}")
    return all_books[ident]


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, ident = argv[1], argv[2]
    src = book(ident)
    if cmd == "find":
        hits = src.find(" ".join(argv[3:]))
        print(f"{src.title} · 命中 OCR 页: {hits or '无'}")
    elif cmd == "page":
        print(src.page(int(argv[3]))[:4000])
    elif cmd == "spread":
        for n in range(int(argv[3]), int(argv[4]) + 1):
            print(f"\n===== OCR 第 {n} 页 =====")
            print(src.page(n))
    elif cmd == "chapters":
        for c in src.chapters():
            print(f"第{c['no']}章 {c['name']}  OCR 第 {c['start']}–{c['end']} 页")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
