"""刷新当前教材清单的页数和哈希；保留源选择、版本与迁移记录。"""
import hashlib
import json
from ocr_index import INVENTORY, PAGE_HEAD, resolve_path


def inventory():
    sources = json.loads(INVENTORY.read_text(encoding="utf-8"))
    for source in sources:
        path = resolve_path(source["ocrPath"])
        data = path.read_bytes()
        pages = [int(n) for n in PAGE_HEAD.findall(data.decode("utf-8"))]
        if not pages or pages != list(range(1, len(pages) + 1)):
            raise ValueError(f"页码缺失、重复或乱序：{path}")
        source.update(ocrPages=len(pages), sha256=hashlib.sha256(data).hexdigest())
    return sources


if __name__ == "__main__":
    sources = inventory()
    INVENTORY.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("已刷新当前来源：" + ", ".join(f"{s['id']} {s.get('engine', '原 OCR')} {s['ocrPages']} 页" for s in sources))
