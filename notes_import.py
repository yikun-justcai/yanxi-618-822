"""把两份“重点笔记”docx 解析成考点清单数据（notes_data.json）。

输入（相对工作区）：
    公共管理/蔡立辉王乐夫重点/蔡立辉王乐夫公共管理学.docx
    公共管理/陈振明重点/陈振明公共管理.docx

每份笔记的体例：章名单独一行；每条考点写成
    「考点名（题型）P纸书页」
红字表示这个考点考过真题。解析时保留题干、题型、纸书页、红字标记，
再用 OCR 全文回查考点名，能查到的记下 OCR 页码（查不到的留空，不编造）。

用法：
    python notes_import.py          # 重新解析并写入 notes_data.json
"""

import json
import re
import sys
from pathlib import Path

import docx

import ocr_index

PROJECT = Path(__file__).resolve().parent
WORKSPACE = PROJECT.parent
OUT = PROJECT / "notes_data.json"

TYPE_WORDS = re.compile(r"^(名词解释|名词|名解|简答|论述|开放性题目|简答与论述|名解与简答为主|"
                        r"名词/可用于开放性题目|简答/论述|名词为主|简答、论述|[\s/、与和]|\+)*$")
PAGE = re.compile(r"[Pp]\s*(\d{1,3})")

# 章名 -> 站点模块。列表第一项是主模块。
SOURCES = [
    {
        "id": "cai-wang-3",
        "label": "蔡王",
        "doc": "公共管理/蔡立辉王乐夫重点/蔡立辉王乐夫公共管理学.docx",
        "chapters": [
            ("导论", ["m1"]),
            ("公共管理的理论发展", ["m2"]),
            ("公共组织", ["m3"]),
            ("公共领导", ["m4"]),
            ("公共政策", ["m5"]),
            ("公共人力资源管理", ["m6"]),
            ("公共预算管理", ["m7"]),
            ("政务信息资源管理", ["m8"]),
            ("公共危机管理", ["m9"]),
            ("公共管理技术与方法", ["m10"]),
            ("公共管理规范", ["m11"]),
            ("公共部门绩效评估", ["m12"]),
            ("公共部门改革", ["m13"]),
        ],
    },
    {
        "id": "chen-2",
        "label": "陈",
        "doc": "公共管理/陈振明重点/陈振明公共管理.docx",
        "chapters": [
            ("导论", ["m1", "m2"]),
            ("公共组织", ["m3"]),
            ("政府改革与治理", ["m13", "m2"]),
            ("政府间关系", ["m13"]),
            ("政府作用", ["m13", "m1"]),
            ("政府工具", ["m10", "m5"]),
            ("公共政策", ["m5"]),
            ("人力资源管理", ["m6"]),
            ("公共预算与财政", ["m7"]),
            ("第三部门管理", ["m3"]),
            ("战略管理", ["m10"]),
            ("绩效管理", ["m12"]),
            ("公共管理伦理", ["m11"]),
        ],
    },
]

POLICY_SOURCES = [
    {"id": "ning-3", "label": "宁骚", "doc": "公共政策/宁骚/宁骚公共政策学.docx",
     "chapters": [(name, [f"p{n}"]) for n, name in enumerate([
         "公共政策学的学科要素", "公共政策的研究视角和路径", "政策研究的资料收集与分析方法",
         "公共政策与政策工具", "政策系统与公共决策体制", "政策过程及其理论模型",
         "第七章 政策问题与议程设定", "第八章 政策方案的规划与抉择", "公共政策执行",
         "公共政策的评估与监控", "第十一章 公共政策的变动、终结与周期", "公共政策学知识的应用"], 1)]},
    {"id": "xie-intro-5", "label": "谢明", "doc": "公共政策/谢明/谢明公共政策.docx",
     "chapters": [("绪论", ["p1"]), ("公共政策的形式、类型、特征与作用", ["p4"]),
                  ("政策主体、政策客体与政策环境", ["p5"]), ("政策模型及相关理论", ["p6"]),
                  ("政策制定", ["p7", "p8"]), ("政策执行", ["p9"]),
                  ("政策评估", ["p10"]), ("政策终结", ["p11"])]},
]


def run_color(run):
    color = run.font.color
    return str(color.rgb) if color and color.rgb else None


def split_item(text):
    """把「考点（题型）P12」拆成（考点, 题型, 纸书页）。"""
    page = None
    m = PAGE.search(text)
    if m:
        page = int(m.group(1))
        text = text[:m.start()] + text[m.end():]
    types = []
    rest = []
    pos = 0
    for m in re.finditer(r"[（(]([^（）()]*)[）)]", text):
        prefix = text[pos:m.start()]
        inner = m.group(1)
        if TYPE_WORDS.match(inner):
            rest.append(prefix)
            types.append(inner)
        else:
            rest.append(prefix + m.group(0))
        pos = m.end()
    rest.append(text[pos:])
    term = "".join(rest)
    term = re.sub(r"\s+", " ", term).strip(" 。；;，,")
    term = re.sub(r"(名词|简答|论述|名解|要点)(为主|为主，)?$", "", term).strip()
    if types:
        joined = "/".join(types)
        if "简答" in joined and "论述" in joined:
            kind = "简答/论述"
        elif "名词" in joined or "名解" in joined:
            kind = "名词解释"
        elif "简答" in joined:
            kind = "简答"
        elif "论述" in joined:
            kind = "论述"
        else:
            kind = "要点"
    else:
        kind = "要点"
    return term, kind, page


def search_key(term):
    """从考点名里挑一个用于 OCR 回查的短语，越长越不易误命中。"""
    plain = re.sub(r"[（(][^（）()]*[）)]", "", term)
    chunks = [c.strip() for c in re.split(r"[、／/，,]|及|和|与", plain) if len(c.strip()) >= 3]
    if not chunks:
        chunks = [plain.strip()]
    chunks.sort(key=len, reverse=True)
    return chunks[0] if chunks else ""


def parse(doc_path):
    document = docx.Document(str(doc_path))
    chapters = []
    current = None
    for para in document.paragraphs:
        raw = para.text.strip()
        if not raw:
            continue
        red = any(run_color(r) == "FF0000" for r in para.runs)
        if current is None:
            # 第一行是“△1.红色的字体……”这类体例说明，等到章名出现才开始
            if raw in [name for name, _ in chapter_plan]:
                current = {"name": raw, "items": [], "notes": []}
                chapters.append(current)
            continue
        if raw in [name for name, _ in chapter_plan]:
            # 同名的重复章名（笔记里“公共领导”出现两次，第二处其实是公共政策）
            if chapters and chapters[-1]["name"] == raw:
                raw = "公共政策"
            current = {"name": raw, "items": [], "notes": []}
            chapters.append(current)
            continue
        if raw.startswith("△"):
            current["notes"].append(raw.lstrip("△").strip())
            continue
        term, kind, page = split_item(raw)
        if not term:
            continue
        current["items"].append({"term": term, "kind": kind, "page": page, "red": red})
    return chapters


def bigrams(text):
    clean = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", text)
    return {clean[i:i + 2] for i in range(len(clean) - 1)}


def similar(a, b):
    ga, gb = bigrams(a), bigrams(b)
    if not ga or not gb:
        return 0
    return len(ga & gb) / len(ga | gb)


def main(subject='618'):
    global chapter_plan
    books = []
    all_items = []
    for src in (POLICY_SOURCES if subject == '822' else SOURCES):
        chapter_plan = src["chapters"]
        doc_path = WORKSPACE / src["doc"]
        if not doc_path.exists():
            raise SystemExit(f"找不到笔记文件：{doc_path}")
        parsed = parse(doc_path)
        if not parsed:
            raise SystemExit(f"{doc_path.name} 里没有认出任何章节")
        ocr = ocr_index.book(src["id"])
        chapters = []
        for idx, chapter in enumerate(parsed):
            plan = next((mods for name, mods in src["chapters"] if name == chapter["name"]), None)
            if plan is None:
                raise SystemExit(f"{src['label']} 出现计划外的章名：{chapter['name']}")
            items = []
            for n, item in enumerate(chapter["items"]):
                if subject == '822':
                    item['term'] = re.sub(r'^\d+[.、．]\s*', '', item['term'])
                key = search_key(item["term"])
                hits = ocr.find(key) if key else []
                # 只在“查得到、又不像到处都有的套话”时才挂原文页码：
                # 命中超过 6 页说明这个词太泛，指过去反而误导。
                if len(hits) > 6:
                    hits = []
                ident = f"{src['id']}:{idx + 1}:{n + 1}"
                record = {
                    "id": ident,
                    "term": item["term"],
                    "kind": item["kind"],
                    "page": item["page"],
                    "red": item["red"],
                    "ocr": hits[:4],
                }
                items.append(record)
                all_items.append((src["id"], record))
            chapters.append({
                "name": chapter["name"],
                "modules": plan,
                "notes": chapter["notes"],
                "items": items,
            })
        if subject == '822' and src['id'] == 'xie-intro-5':
            chapters[0]['notes'].insert(0, '本笔记未注明版本，所标页码与本地《导论》第5版不一致；笔记页码原样保留，OCR 页另在第5版中按关键词定位，不能直接互换。')
        books.append({"id": src["id"], "label": src["label"], "chapters": chapters, "source": src['doc']})

    # 两本书都列了的考点：只是提示“这个知识点两边都有”，不做逐条对照
    for book_id, item in all_items:
        best, best_score = None, 0.0
        for other_id, other in all_items:
            if other_id == book_id:
                continue
            score = similar(item["term"], other["term"])
            if score > best_score:
                best, best_score = other["id"], score
        if best and best_score >= 0.5:
            item["also"] = best

    stats = {
        "items": len(all_items),
        "verified": sum(1 for _, i in all_items if i["ocr"]),
        "red": sum(1 for _, i in all_items if i["red"]),
        "both": sum(1 for _, i in all_items if i.get("also")),
    }
    data = {"books": books, "stats": stats, 'description': '红点沿用重点笔记的标红；纸书 P 是笔记页码，原文 p 是 MinerU 底稿中的 PDF 页序。关键词命中只帮助定位，不代表整条考点已逐句核验。'}
    if subject == '822':
        data['description'] = '红点沿用笔记标红，未逐题核验原卷；笔记页码保留原标注，MinerU 原文页仅表示关键词定位，并非整条考点的逐句核验。谢明笔记版本未注明，与第5版页码不可互换。'
        data['pageLabel'] = '笔记 P'
    output = PROJECT / 'policy_notes_data.json' if subject == '822' else OUT
    output.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写入 {output.name}：{stats['items']} 条考点（红字 {stats['red']}、两书都有 {stats['both']}、"
          f"OCR 回查成功 {stats['verified']}）")
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', choices=['618', '822'], default='618')
    sys.exit(main(parser.parse_args().subject))
