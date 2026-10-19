"""MinerU 迁移回归：页界、脚注、文本完整性、旧文件保留、内容修正。"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ocr_index as ocr
import source_inventory
from course import extra, policy


def main():
    inventory = json.loads(ocr.INVENTORY.read_text(encoding="utf-8"))
    assert source_inventory.inventory() == inventory, "刷新清单不能改变源选择或元数据"
    selected = [m for m in inventory if m.get("engine") == "MinerU"]
    assert len(selected) == 4 and sum(m["ocrPages"] for m in selected) == 1751
    for meta in selected:
        old = ocr.resolve_path(meta["legacyOcrPath"])
        assert hashlib.sha256(old.read_bytes()).hexdigest() == meta["legacySha256"], "旧 OCR 被改动"
    assert ocr.book("cai-wang-3").quote_on([18], "公共管理更加强调管理的、市场化和社会化的手段")
    assert ocr.book("cai-wang-3").quote_on([77], "提供公共物品和公共服务是网络治理的根本任务")
    assert ocr.book("chen-2").quote_on([327], "七是在国际事务中发挥监督、协调作用")
    assert ocr.book("xie-intro-5").quote_on([121], "不要轻易满足于简单的一致")
    # 哈希与重复页必须阻断构建，不能被 dict 覆盖静默吞掉。
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.md"
        path.write_text("## 第 1 页\n正文\n## 第 1 页\n重复", encoding="utf-8")
        meta = {"id": "bad", "title": "bad", "ocrPath": str(path), "ocrPages": 2}
        for hash_value in (None, "bad-hash"):
            if hash_value:
                meta["sha256"] = hash_value
            try:
                ocr.Book(meta)
            except ValueError:
                pass
            else:
                raise AssertionError("没有拒绝损坏的底稿")
    lesson = next(l for l in extra.LESSONS if l["id"] == "l3-6")
    assert "七条" in lesson["write"]["sample"]
    assert "互助" in "".join(lesson["write"]["points"])
    assert "国际" in "".join(lesson["write"]["points"])
    lesson = next(l for l in policy.LESSONS if l["id"] == "p6-4")
    assert len(next(b["items"] for b in lesson["blocks"] if b["t"] == "list")) == 9
    assert lesson["exercises"][-1]["a"] == [0, 2]
    print("PASS：1751 页、四本新源、旧文件哈希、跨页/脚注、损坏阻断、七项作用与九项预防措施")


if __name__ == "__main__":
    main()
