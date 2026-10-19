"""618 / 822 学习站的数据组装与教材依据校验。

运行：python build_site.py
产出：重写 index.html 里的四个 JSON 数据块（618 课程、618 真题、618 考点、822 全部数据）。
任一科的教材依据校验失败都会中止，不覆盖 index.html。
"""

import hashlib
import json
import re
import sys
from pathlib import Path

from course.curriculum import MODULES, MODULE_LESSONS, PLANNED_LESSONS, SUBJECT
from course import m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, extra
from course.dual import CHEN_EVIDENCE
from course import policy, framework

import ocr_index
from exam_content import EXAM_CARDS
from reference_answers import REFERENCE_ANSWERS

PROJECT = Path(__file__).resolve().parent
OUTPUT = PROJECT / "index.html"
EXAM_DIR = PROJECT.parent / "真题"
POINTS_FILE = PROJECT / "notes_data.json"
TARGET_SUBJECT = "公共管理学"  # 618；822 由 policy.SUBJECT 单独传参

LESSON_POOL = {lesson["id"]: lesson for module in (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, extra) for lesson in module.LESSONS}
EXERCISE_TYPES = {"choice", "multi", "judge", "order"}
BLOCK_TYPES = {"lead", "p", "cmp", "ask", "quote", "tip", "list"}
REVIEW_STATES = {"quote-checked", "reviewed"}


# ---------------------------------------------------------------- 校验

def fail(message):
    raise SystemExit("构建中止：" + message)


def check_lessons(lesson_pool=LESSON_POOL, module_lessons=MODULE_LESSONS, modules=MODULES):
    if len(lesson_pool) != sum(len(v) for v in module_lessons.values()):
        fail("课时定义与 curriculum.MODULE_LESSONS 数量不一致")

    for module_id, ids in module_lessons.items():
        for lesson_id in ids:
            if lesson_id not in lesson_pool:
                fail(f"{module_id} 引用了不存在的课时 {lesson_id}")

    for lesson in lesson_pool.values():
        ident = lesson["id"]
        for key in ("title", "goal", "minutes", "blocks", "exercises"):
            if key not in lesson:
                fail(f"{ident} 缺少字段 {key}")
        if not lesson["blocks"]:
            fail(f"{ident} 没有讲解内容")
        for block in lesson["blocks"]:
            if block["t"] not in BLOCK_TYPES:
                fail(f"{ident} 出现未知内容块 {block['t']}")
        sources = {ref["src"] for ref in lesson["evidence"]}
        chen_modules = {m["id"] for m in modules if (m.get("dual") or {}).get("chen")}
        module_id = next((mid for mid, ids in module_lessons.items() if ident in ids), None)
        if module_id in chen_modules and "chen-2" not in sources:
            fail(f"{ident} 所在模块有陈振明对照章节，却没有一条陈书依据")
        for index, item in enumerate(lesson["exercises"]):
            if item["t"] not in EXERCISE_TYPES:
                fail(f"{ident} 练习 {index} 类型未知：{item['t']}")
            if not item.get("why"):
                fail(f"{ident} 练习 {index} 缺少解析")
            if item["t"] in ("choice", "multi"):
                n = len(item["opts"])
                picked = item["a"] if item["t"] == "multi" else [item["a"]]
                if any(not 0 <= p < n for p in picked):
                    fail(f"{ident} 练习 {index} 答案越界")
            if item["t"] == "order":
                if sorted(item["a"]) != list(range(len(item["items"]))):
                    fail(f"{ident} 练习 {index} 排序答案不是全排列")
        write = lesson.get("write")
        if write:
            for key in ("type", "prompt", "minutes", "points", "sample"):
                if key not in write:
                    fail(f"{ident} 写作任务缺少 {key}")
            if len(write["points"]) < 3:
                fail(f"{ident} 写作得分点少于 3 条")
        if not lesson.get("evidence"):
            fail(f"{ident} 没有教材依据")


def claim_texts():
    """把真题 PDF 抽成纯文本，供真题类依据校验使用。"""
    import pymupdf
    cache = {}
    for path in EXAM_DIR.glob("*.pdf"):
        doc = pymupdf.open(path)
        cache[path.name] = re.sub(r"\s+", "", "\n".join(p.get_text() for p in doc))
    return cache


def check_evidence(exam_texts, lesson_pool=LESSON_POOL):
    checked = 0
    for lesson in lesson_pool.values():
        for ref in lesson["evidence"]:
            src = ref["src"]
            quote = re.sub(r"\s+", "", ref["quote"])
            if src.startswith("exam:"):
                name = src.split(":", 1)[1]
                if name not in exam_texts:
                    fail(f"{lesson['id']} 引用了不存在的真题文件 {name}")
                if quote not in exam_texts[name]:
                    fail(f"{lesson['id']} 的真题依据找不到：{ref['quote']}")
            else:
                src_book = ocr_index.book(src)
                pages = ref["pages"]
                if not src_book.quote_on(pages, ref["quote"]):
                    fail(f"{lesson['id']} 的教材依据在 OCR 第 {pages} 页找不到：{ref['quote']}")
            checked += 1
    return checked


def merge_dual_evidence():
    """把 course/dual.py 里按课时归拢的陈书依据并进 lesson["evidence"]。"""
    for lesson_id, refs in CHEN_EVIDENCE.items():
        lesson = LESSON_POOL.get(lesson_id)
        if lesson is None:
            fail(f"dual.py 引用了不存在的课时 {lesson_id}")
        lesson["evidence"] = list(lesson["evidence"]) + list(refs)


def check_dual():
    """每个正课模块都要交代「这一块在陈书里对应哪一章、两书差在哪」。"""
    for module in MODULES:
        if module["id"] == "m0":
            continue
        dual = module.get("dual")
        if not dual:
            fail(f"{module['id']} 缺少两书对照信息 dual")
        if not dual.get("cai"):
            fail(f"{module['id']} 的 dual 没有写蔡书章节")
        if not dual.get("diff"):
            fail(f"{module['id']} 的 dual 没有写两书差异")


def load_points(points_file=POINTS_FILE, modules=MODULES, subject=SUBJECT):
    """读重点笔记解析结果，并检查模块引用与 OCR 页码是否成立。"""
    if not points_file.exists():
        fail("缺少 notes_data.json，请先运行 python notes_import.py")
    data = json.loads(points_file.read_text(encoding="utf-8"))
    module_ids = {m["id"] for m in modules}
    total = verified = red = both = 0
    for book in data["books"]:
        meta = ocr_index.book(book["id"])
        if book["id"] not in subject["books"]:
            fail(f"考点清单里的教材 {book['id']} 不在 {subject['code']} 教材列表里")
        for chapter in book["chapters"]:
            for module_id in chapter["modules"]:
                if module_id not in module_ids:
                    fail(f"{book['label']}·{chapter['name']} 引用了不存在的模块 {module_id}")
            for item in chapter["items"]:
                total += 1
                for page in item["ocr"]:
                    if page not in meta.pages:
                        fail(f"考点「{item['term']}」引用了不存在的 OCR 页 {page}")
                if item["ocr"]:
                    verified += 1
                if item["red"]:
                    red += 1
                if item.get("also"):
                    both += 1
    if not total:
        fail("考点清单是空的")
    data["stats"] = {"items": total, "verified": verified, "red": red, "both": both}
    return data


def check_exam_data(target_subject=TARGET_SUBJECT):
    if len(EXAM_CARDS) != len(REFERENCE_ANSWERS):
        fail("真题与参考答案数量不一致")
    pairs = []
    for (year, course, qtype, topic, question, outline, source), (basis, answer) in zip(
            EXAM_CARDS, REFERENCE_ANSWERS):
        if course != target_subject:
            continue
        ident = "exam-" + hashlib.sha1(f"{year}|{course}|{question}".encode()).hexdigest()[:12]
        pairs.append({
            "id": ident, "year": year, "type": qtype, "topic": topic,
            "question": question, "outline": outline, "answer": answer,
            "basis": basis, "source": source,
        })
    if not pairs:
        fail(f"没有可用的 {target_subject} 真题")
    return pairs


def clean_text(text):
    return re.sub(r"[\s，。、；：？！“”‘’（）()《》【】·—\-…,.]", "", text or "")


def exam_source_text(source):
    """按 source 里的文件名找到真题原件并抽出纯文本；认不出就返回 None。"""
    stem = source.split("·")[0].strip()
    target = clean_text(Path(stem).stem)
    files = [p for p in EXAM_DIR.iterdir() if p.suffix.lower() in (".pdf", ".docx")]
    hit = None
    for path in files:
        name = clean_text(path.stem)
        if name == target or name.startswith(target) or target.startswith(name):
            hit = path
            break
    if hit is None:
        m = re.match(r"(20\d\d)", stem)
        code = "822" if "822" in stem else "618"
        for path in files:
            if m and m.group(1) in path.name and code in path.name:
                hit = path
                break
    if hit is None:
        return None
    if hit.suffix.lower() == ".pdf":
        import pymupdf
        doc = pymupdf.open(hit)
        return clean_text("".join(page.get_text() for page in doc))
    import docx
    doc = docx.Document(str(hit))
    return clean_text("".join(p.text for p in doc.paragraphs))


def check_exam_provenance(pairs):
    """逐题回查真题原件：题干必须真的出现在 source 指向的那份文件里。

    答案类文档（文件名含「答案」）往往不印题干，只能退一步核主题词；
    返回 (逐字命中数, 主题命中数)。
    """
    strict = loose = 0
    for exam in pairs:
        text = exam_source_text(exam["source"])
        if text is None:
            continue
        question = clean_text(exam["question"])
        if question and question in text:
            strict += 1
            continue
        if question[:8] and question[:8] in text:
            loose += 1
            continue
        topic = clean_text(exam["topic"])
        if "答案" in exam["source"] and topic and topic in text:
            loose += 1
            continue
        fail(f"真题题干在原件里找不到：{exam['year']}「{exam['question'][:24]}」（{exam['source']}）")
    return strict, loose


# ---------------------------------------------------------------- 组装
def build_framework(subject, modules, lessons):
    code = str(subject["code"])
    config = framework.FRAMEWORKS[code]
    by_id = {m["id"]: m for m in modules}
    covered = [mid for group in config["groups"] for mid in group["modules"]]
    expected = set(by_id) - {"m0", "p0"}
    if set(covered) != expected or len(covered) != len(set(covered)):
        fail(f"{code} 全科框架章节缺失或重复")
    guides = {}
    for mid, guide in framework.GUIDES[code].items():
        if mid not in by_id:
            fail(f"框架章节不存在：{mid}")
        own = {l["id"] for l in by_id[mid]["lessons"]}
        branches = {lid for b in guide["branches"] for lid in b["lessons"]}
        if branches != own:
            fail(f"{mid} 章节主线未覆盖本章全部课时")
        ids = guide["prerequisites"] + guide["evidenceLessons"]
        ids += [lid for r in guide["relations"] for lid in r["lessons"]]
        if any(lid not in lessons for lid in ids):
            fail(f"{mid} 框架引用了不存在的课时")
        tasks = guide["tasks"]
        if [t["id"] for t in tasks] != ["structure", "relation", "application"]:
            fail(f"{mid} 重建任务不完整")
        if any(not t.get(k, "").strip() for t in tasks for k in ("label", "prompt", "reference", "check")):
            fail(f"{mid} 重建任务缺少提示或参考")
        bridge = guide["bridge"]
        if bridge["module"] not in framework.GUIDES.get(bridge["subject"], {}):
            fail(f"{mid} 跨科入口不存在")
        evidence = []
        for lid in dict.fromkeys(ids + sorted(branches)):
            for ref in lessons[lid]["evidence"]:
                if not ref["src"].startswith("exam:"):
                    evidence.append({**ref, "lessonId": lid})
                    break
        guides[mid] = {**guide, "evidence": evidence}
    return {**config, "guides": guides, "case": framework.CASE}


def build_course(exams, lesson_pool=LESSON_POOL, module_defs=MODULES,
                 module_lessons=MODULE_LESSONS, planned=PLANNED_LESSONS, subject=SUBJECT):
    lessons_public = {}
    for lesson in lesson_pool.values():
        # 审核状态：quote-checked 表示教材引文已由构建脚本逐条回查、讲解为归纳改写；
        # reviewed 沿用已有文本抽核记录，不代表全书逐页或纸书核验。
        status = lesson.get("reviewStatus", "quote-checked")
        if status not in REVIEW_STATES:
            fail(f"{lesson['id']} 的审核状态未知：{status}")
        lessons_public[lesson["id"]] = {**lesson, "moduleId": None, "reviewStatus": status}
        refs = []
        for ref in lesson["evidence"]:
            item = dict(ref)
            if not ref["src"].startswith("exam:"):
                source = ocr_index.book(ref["src"])
                for page in ref["pages"]:
                    text = ocr_index.squeeze(source.page(page))
                    start = ocr_index.normalize(text).find(ocr_index.normalize(ref["quote"]))
                    if start >= 0:
                        left, right = max(0, start - 80), start + len(ocr_index.squeeze(ref["quote"])) + 120
                        item["context"] = ("…" if left else "") + text[left:right] + ("…" if right < len(text) else "")
                        item["contextPage"] = page
                        break
            refs.append(item)
        lessons_public[lesson["id"]]["evidence"] = refs

    modules = []
    for module in module_defs:
        ids = module_lessons.get(module["id"])
        lessons = []
        for index, lesson_id in enumerate(ids or []):
            lesson = lesson_pool[lesson_id]
            lessons_public[lesson_id]["moduleId"] = module["id"]
            lessons_public[lesson_id]["order"] = index + 1
            lessons.append({
                "id": lesson_id, "order": index + 1, "title": lesson["title"],
                "minutes": lesson["minutes"], "tag": lesson.get("tag", ""),
            })
        entrance = [e for e in exams if e["topic"] in module["examTopics"]]
        modules.append({
            **module,
            "lessons": lessons,
            "planned": planned.get(module["id"], 0),
            "open": bool(lessons),
            "examCount": len(entrance),
        })
    return {
        "subject": subject,
        "modules": modules,
        "lessons": lessons_public,
        "framework": build_framework(subject, modules, lessons_public),
        "sources": {b.id: {"short": b.short, "title": b.title, "engine": b.engine} for b in ocr_index.books().values()
                    if b.id in subject["books"]},
        "totalOpen": sum(len(m["lessons"]) for m in modules),
    }


def embed(html, script_id, data):
    pattern = rf'(<script id="{script_id}" type="application/json">).*?(</script>)'
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    html, count = re.subn(pattern, lambda m: m.group(1) + payload + m.group(2), html,
                          count=1, flags=re.S)
    if count != 1:
        fail(f"找不到数据入口 {script_id}")
    return html


def main():
    merge_dual_evidence()
    check_lessons()
    check_dual()
    points = load_points()
    exam_texts = claim_texts()
    checked = check_evidence(exam_texts)
    exams = check_exam_data()
    course = build_course(exams)

    policy_pool = {l['id']: l for l in policy.LESSONS}
    if len(policy_pool) != len(policy.LESSONS):
        fail('822 课时 ID 重复')
    check_lessons(policy_pool, policy.MODULE_LESSONS, policy.MODULES)
    policy_checked = check_evidence(exam_texts, policy_pool)
    policy_points = load_points(PROJECT / 'policy_notes_data.json', policy.MODULES, policy.SUBJECT)
    policy_exams = check_exam_data('公共政策学')
    policy_strict, policy_loose = check_exam_provenance(policy_exams)
    policy_course = build_course(policy_exams, policy_pool, policy.MODULES,
                                 policy.MODULE_LESSONS, policy.PLANNED_LESSONS, policy.SUBJECT)

    html = OUTPUT.read_text(encoding="utf-8")
    html = embed(html, "exam-data", exams)
    html = embed(html, "course-data", course)
    html = embed(html, "points-data", points)
    html = embed(html, 'policy-data', {'course': policy_course, 'exams': policy_exams, 'points': policy_points})
    OUTPUT.write_text(html, encoding="utf-8")

    exercises = sum(len(l["exercises"]) for l in LESSON_POOL.values())
    print(f"已写入 {OUTPUT.name}：{course['totalOpen']} 课、{exercises} 道练习、"
          f"{len(exams)} 道真题、{checked} 条教材依据全部校验通过；"
          f"考点清单 {points['stats']['items']} 条（可定位原文 {points['stats']['verified']} 条）")
    print(f"822：{len(policy_pool)} 课、{sum(len(l['exercises']) for l in policy_pool.values())} 道练习、"
          f"{len(policy_exams)} 道真题（题干逐字回查 {policy_strict}、主题回查 {policy_loose}）、"
          f"{policy_checked} 条依据回查通过、{policy_points['stats']['items']} 条考点")
    return 0


if __name__ == "__main__":
    sys.exit(main())
