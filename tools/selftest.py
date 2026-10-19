"""学生端回归自测：把断言注入 index.html 的副本，用无头 Edge 跑 618 与 822 两科。

运行：python tools/selftest.py
退出码 0 表示两科全部通过。临时文件在结束时删除。
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT / "index.html"
EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

TEST = r"""
<script>
(async()=>{
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  let pass=0,total=0;
  const ok=(name,cond,extra)=>{total++;if(cond)pass++;console.log("TESTLOG "+(cond?"PASS ":"FAIL ")+name+(extra?" :: "+extra:""))};
  const SC=new URLSearchParams(location.search).get("subject")==="822"?"822":"618";
  const PD=JSON.parse(document.querySelector("#policy-data").textContent||"{}");
  const COURSE=SC==="822"?PD.course:JSON.parse(document.querySelector("#course-data").textContent);
  const EXAMS=SC==="822"?PD.exams:JSON.parse(document.querySelector("#exam-data").textContent);
  const POINTS=SC==="822"?PD.points:JSON.parse(document.querySelector("#points-data").textContent);
  const KEY="yanxi-"+SC+"-v2", OTHER="yanxi-"+(SC==="822"?"618":"822")+"-v2";
  const primary=COURSE.subject.primaryLabel||(SC==="822"?"宁骚":"蔡立辉");
  const secondary=COURSE.subject.secondaryLabel||(SC==="822"?"谢明":"陈振明");
  const ids=Object.keys(COURSE.lessons);
  const prog=()=>document.querySelector("#nav-progress").textContent;

  async function solveLesson(id){
    const L=COURSE.lessons[id];
    for(let i=0;i<L.exercises.length;i++){
      const e=L.exercises[i];
      const box=document.querySelectorAll(".ex")[i];
      if(!box){ok("找到第 "+(i+1)+" 题",false);return}
      if(e.t==="choice"){box.querySelectorAll(".opt")[e.a].click()}
      else if(e.t==="judge"){box.querySelector('[data-judge="'+(e.a?"1":"0")+'"]').click()}
      else if(e.t==="multi"){
        e.a.forEach(k=>box.querySelectorAll(".opt")[k].click());
        box.querySelector("[data-submit]").click();
      } else if(e.t==="order"){
        for(let pos=0;pos<e.a.length;pos++){
          for(let g=0;g<20;g++){
            const rows=[...box.querySelectorAll(".order-item")];
            const idx=rows.findIndex(r=>Number(r.dataset.item)===e.a[pos]);
            if(idx===pos)break;
            rows[idx].querySelector('[data-move="up"]').click();
          }
        }
        box.querySelector("[data-submit]").click();
      }
      await wait(40);
    }
  }

  try{localStorage.setItem("__probe","1");ok("localStorage 可用",localStorage.getItem("__probe")==="1");localStorage.removeItem("__probe");}
  catch(e){ok("localStorage 可用",false,e.message)}
  localStorage.setItem(OTHER,JSON.stringify({marker:"keep"}));

  ok("科目选择器",document.querySelector("#subject-select").value===SC,document.querySelector("#subject-select").value);
  ok("品牌显示科目",document.querySelector(".brand p").textContent.indexOf(SC)>=0,document.querySelector(".brand p").textContent);

  const modules=COURSE.modules.length;
  ok("地图模块数",document.querySelectorAll(".route-item").length===modules,document.querySelectorAll(".route-item").length+"/"+modules);
  ok("地图课时数",document.querySelectorAll(".lesson-row").length===ids.length,document.querySelectorAll(".lesson-row").length+"/"+ids.length);
  ok("初始进度",prog()==="0/"+ids.length,prog());

  location.hash="#/lesson/"+ids[0]; await wait(220);
  ok("进入课时页",!!document.querySelector("#lesson-body"));
  const first=COURSE.lessons[ids[0]];
  ok("练习数量",document.querySelectorAll(".ex").length===first.exercises.length,document.querySelectorAll(".ex").length+"/"+first.exercises.length);

  await solveLesson(ids[0]);
  await wait(140);
  const readHasWrite=!!COURSE.lessons[ids[0]].write;
  if(readHasWrite){
    ok("练习做完但没对照写作不算学完",prog()==="0/"+ids.length,prog());
  }else{
    ok("第一课学完",prog()==="1/"+ids.length,prog());
    let saved=JSON.parse(localStorage.getItem(KEY)||"{}");
    ok("写入复习日期",!!(saved.lessons&&saved.lessons[ids[0]]&&saved.lessons[ids[0]].next));
  }

  const writeId=ids.find(id=>COURSE.lessons[id].write);
  const sameLesson=writeId===ids[0];
  location.hash="#/lesson/"+writeId; await wait(220);
  if(!sameLesson) await solveLesson(writeId);
  await wait(140);
  if(!sameLesson) ok("写作未对照不算学完",prog()==="1/"+ids.length,prog());
  document.querySelector("[data-check]").click(); await wait(100);
  ok("要点清单展开",!document.querySelector("#write-check").hidden);
  const pts=[...document.querySelectorAll(".point")];
  // 真实用户点的是按钮里的文字，不是按钮本身——这里专门点子元素验证事件代理。
  if(pts.length){
    pts[0].querySelectorAll("span")[1].click();
    await wait(80);
    ok("点子元素也能勾选要点",pts[0].classList.contains("hit"),pts.length+" 个要点");
  }
  pts.slice(1).forEach(p=>p.click()); await wait(140);
  ok("全部命中",document.querySelector("#score-line").textContent.indexOf("命中 "+pts.length+" /")>=0,document.querySelector("#score-line").textContent);
  await wait(120);
  const doneAfterWrite=sameLesson?1:2;
  ok("写作完成后学完",prog()===doneAfterWrite+"/"+ids.length,prog());
  if(sameLesson){
    let saved=JSON.parse(localStorage.getItem(KEY)||"{}");
    ok("写入复习日期",!!(saved.lessons&&saved.lessons[writeId]&&saved.lessons[writeId].next));
  }
  ok("完成度卡显示已完成",/已完成/.test(document.querySelector("#rail-done").textContent));

  location.hash="#/review"; await wait(200);
  ok("复习页三板块",["做错过的练习","写作要点没写全","到期复习"].every(x=>document.body.textContent.indexOf(x)>=0));

  location.hash="#/exam"; await wait(240);
  ok("真题条数",document.querySelectorAll(".exam-card").length===EXAMS.length,document.querySelectorAll(".exam-card").length+"/"+EXAMS.length);
  const card=document.querySelector(".exam-card");
  card.querySelector("summary").click(); await wait(100);
  ok("真题含提纲与依据",card.textContent.indexOf("作答提纲")>=0&&card.textContent.indexOf("教材依据")>=0);
  const sel=document.querySelector("#f-type"); sel.value=EXAMS[0].type; sel.dispatchEvent(new Event("change")); await wait(180);
  ok("题型筛选生效",document.querySelectorAll(".exam-card").length<EXAMS.length,document.querySelectorAll(".exam-card").length);
  const q=document.querySelector("#f-q"); q.value=EXAMS[0].question.slice(0,4); q.dispatchEvent(new Event("input")); await wait(180);
  ok("真题搜索生效",document.querySelectorAll(".exam-card").length>=1&&document.querySelectorAll(".exam-card").length<=EXAMS.length,document.querySelectorAll(".exam-card").length);

  location.hash="#/points"; await wait(280);
  const kpItems=document.querySelectorAll(".kp-item").length;
  ok("考点条数",kpItems===POINTS.stats.items,kpItems+"/"+POINTS.stats.items);
  ok("两本书都在清单里",document.querySelectorAll(".kp-book").length===POINTS.books.length,document.querySelectorAll(".kp-book").length+"/"+POINTS.books.length);
  ok("考点能跳模块",!!document.querySelector(".kp-chapter-head a[href^='#/module/']"));
  document.querySelector('[data-kp="red"]').click(); await wait(200);
  const redAfter=document.querySelectorAll(".kp-item").length;
  ok("只看考过生效",redAfter>0&&redAfter===POINTS.stats.red,redAfter+"/"+POINTS.stats.red);
  document.querySelector('[data-kp="red"]').click(); await wait(160);
  const kq=document.querySelector("#k-q");
  const term=(POINTS.books[0].chapters[0].items[0].term||"").slice(0,4);
  kq.value=term; kq.dispatchEvent(new Event("input")); await wait(200);
  const qAfter=document.querySelectorAll(".kp-item").length;
  ok("考点搜索生效",qAfter>0&&qAfter<kpItems,term+" → "+qAfter+"/"+kpItems);
  kq.value=""; kq.dispatchEvent(new Event("input")); await wait(160);
  ok("考点页无横向溢出",document.documentElement.scrollWidth<=window.innerWidth+1,document.documentElement.scrollWidth+" vs "+window.innerWidth);

  const dualId=ids.find(id=>COURSE.lessons[id].dual||(COURSE.modules.find(m=>m.lessons.some(l=>l.id===id))||{}).dual);
  location.hash="#/lesson/"+dualId; await wait(240);
  const dual=document.querySelector(".dual");
  ok("课时显示两书对照",!!dual&&dual.textContent.indexOf(primary)>=0&&dual.textContent.indexOf(secondary)>=0,dualId);
  const evid=document.querySelector(".evid");
  ok("教材依据可展开",!!evid);
  const refs=COURSE.lessons[dualId].evidence;
  ok("依据条数与数据一致",!!evid&&evid.querySelectorAll(".evid-quote").length===refs.length,
     (evid?evid.querySelectorAll(".evid-quote").length:0)+"/"+refs.length);
  ok("按教材分组",!!evid&&evid.querySelectorAll(".evid-group").length===new Set(refs.map(r=>r.src)).size);
  ok("课时有章节导航",document.querySelectorAll(".secnav a").length>=3);

  document.dispatchEvent(new KeyboardEvent("keydown",{key:"k",ctrlKey:true})); await wait(180);
  ok("Ctrl+K 打开搜索",!document.querySelector("#palette").hidden);
  const pi=document.querySelector("#palette-input"); pi.value=term; pi.dispatchEvent(new Event("input")); await wait(220);
  ok("搜索有结果",document.querySelectorAll(".pal-item").length>0,document.querySelectorAll(".pal-item").length);
  ok("搜索结果分类",[...document.querySelectorAll(".pal-kind")].some(x=>x.textContent==="考点"));
  document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape"})); await wait(140);
  ok("Esc 关闭搜索",document.querySelector("#palette").hidden);

  let renderFail=0;
  for(const lid of ids){
    location.hash="#/lesson/"+lid; await wait(40);
    const L=COURSE.lessons[lid];
    const h=document.querySelector(".lesson-head h2");
    const ex=document.querySelectorAll(".ex").length;
    const q=document.querySelectorAll(".evid-quote").length;
    const want=(L.evidence||[]).filter(r=>COURSE.sources[r.src]).length;
    if(!h||h.textContent!==L.title||ex!==L.exercises.length||q!==want) renderFail++;
  }
  ok("全部课时可渲染且题量/依据齐全",renderFail===0,renderFail+" 个异常");
  ok("当前两本教材均来自 MinerU",Object.values(COURSE.sources).every(s=>s.engine==="MinerU"));
  const contextCount=document.querySelectorAll(".source-context").length;
  ok("教材依据有前后文",contextCount===document.querySelectorAll(".evid-quote").length && contextCount>0);
  const evidence=document.querySelector("#sec-evid");
  evidence.open=true;
  const detail=evidence.querySelector("details");
  detail.querySelector("summary").click();
  ok("前后文可展开",detail.open && detail.textContent.includes("PDF"));


  const reviewed=ids.filter(id=>COURSE.lessons[id].reviewStatus==="reviewed");
  if(reviewed.length){
    location.hash="#/lesson/"+reviewed[0]; await wait(160);
    ok("已抽核课时显示核对说明",!!document.querySelector(".review-note.ok"),reviewed.length+" 课");
  }

  const fw=COURSE.framework||{groups:[],guides:{}};
  const guideId=Object.keys(fw.guides)[0];
  location.hash="#/framework"; await wait(220);
  ok("全科框架分组数",document.querySelectorAll(".framework-groups>li").length===fw.groups.length,
     document.querySelectorAll(".framework-groups>li").length+"/"+fw.groups.length);
  const fwLinks=document.querySelectorAll('.framework-groups a[href^="#/module/"]').length;
  const fwWant=fw.groups.reduce((n,g)=>n+g.modules.length,0);
  ok("框架覆盖全部正课模块",fwLinks===fwWant,fwLinks+"/"+fwWant);
  ok("全部正课章节都有章前定位",Object.keys(fw.guides).length===COURSE.modules.length-1,
     Object.keys(fw.guides).length+"/"+(COURSE.modules.length-1));
  let guideFail=0;
  for(const gid of Object.keys(fw.guides)){
    location.hash="#/module/"+gid; await wait(30);
    if(document.querySelectorAll(".framework-groups>li").length!==fw.guides[gid].branches.length) guideFail++;
  }
  ok("全部章前定位可渲染",guideFail===0,guideFail+" 个异常");

  location.hash="#/module/"+guideId; await wait(220);
  const guide=fw.guides[guideId];
  ok("章前定位分支数",document.querySelectorAll(".framework-groups>li").length===guide.branches.length);
  ok("章前知识联系数",document.querySelectorAll(".framework-relation").length===guide.relations.length);
  const bridge=document.querySelector('.framework-page a[href*="subject="]');
  ok("跨科桥接指向另一科",!!bridge&&bridge.href.indexOf("subject="+(SC==="822"?"618":"822"))>=0);
  ok("共享案例已扩展",(COURSE.framework.case.text||"").length>300&&document.querySelectorAll(".framework-case p").length>=4);
  ok("未开始章节显示未重建",document.querySelector(".framework-status").textContent.indexOf("还未重建")>=0);

  location.hash="#/rebuild/"+guideId; await wait(220);
  ok("三个闭卷任务",document.querySelectorAll("#rebuild-form textarea").length===3);
  ok("初始不渲染参考",!document.querySelector("#rebuild-reference"));
  document.querySelector('#rebuild-form button[type="submit"]').click(); await wait(120);
  ok("空白提交有提示",document.querySelector("#rebuild-error").textContent.length>0);
  ok("空白提交聚焦第一项",document.activeElement.id==="recall-structure");

  const ta=document.querySelector("#recall-structure");
  ta.value="测试草稿：先列组织类型与结构。"; ta.dispatchEvent(new Event("input")); await wait(100);
  let chapterSaved=JSON.parse(localStorage.getItem(KEY)||"{}").chapters||{};
  ok("草稿即时保存",!!chapterSaved[guideId]&&chapterSaved[guideId].answers.structure===ta.value);
  ok("保存状态提示",document.querySelector("#rebuild-save").textContent.indexOf("已保存")>=0);

  document.querySelector("#rebuild-hint").click(); await wait(100);
  chapterSaved=JSON.parse(localStorage.getItem(KEY)||"{}").chapters||{};
  ok("结构提示使用被记录",!!chapterSaved[guideId]&&chapterSaved[guideId].hint===true);
  ok("结构提示文本显示",!document.querySelector("#rebuild-hint-text").hidden);

  for(const [tid,txt] of [["relation","类型与结构回答不同问题，需要联系目标解释。"],["application","核实需求与组织能力，再比较安排并落实责任。"]]){
    const el=document.querySelector("#recall-"+tid);
    el.value=txt; el.dispatchEvent(new Event("input"));
  }
  await wait(100);
  document.querySelector('#rebuild-form button[type="submit"]').click(); await wait(180);
  ok("三个任务写完后展开参考",!!document.querySelector("#rebuild-reference"));
  ok("参考含三项自评",document.querySelectorAll(".framework-check input").length===3);
  ok("对照时锁定草稿",document.querySelector("#recall-structure").readOnly);
  ok("展开后提示草稿锁定",!!document.querySelector("#rebuild-locked"));
  ok("参考顶部有修改入口",!!document.querySelector("#rebuild-edit-top"));
  ok("展开后焦点在参考标题",document.activeElement.tagName==="H3");
  ok("重建参考保留 MinerU 来源",document.querySelector("#rebuild-reference").textContent.indexOf("MinerU")>=0);

  const beforeChapters=prog();
  document.querySelector(".framework-check input").click(); await wait(120);
  chapterSaved=JSON.parse(localStorage.getItem(KEY)||"{}").chapters||{};
  ok("自评写入存储",!!chapterSaved[guideId]&&chapterSaved[guideId].checks.length===1);
  ok("自评不改变课时完成度",prog()===beforeChapters);

  document.querySelector("#rebuild-edit-top").click(); await wait(160);
  chapterSaved=JSON.parse(localStorage.getItem(KEY)||"{}").chapters||{};
  ok("修改时移除参考",!document.querySelector("#rebuild-reference"));
  ok("修改清除旧自评",(chapterSaved[guideId].checks||[]).length===0);
  ok("修改后恢复可写",!document.querySelector("#recall-structure").readOnly);

  document.querySelector('#rebuild-form button[type="submit"]').click(); await wait(160);
  document.querySelector(".framework-check input").click(); await wait(100);
  document.querySelector("#rebuild-new").click(); await wait(160);
  chapterSaved=JSON.parse(localStorage.getItem(KEY)||"{}").chapters||{};
  ok("新一轮清空作答",Object.keys(chapterSaved[guideId].answers).length===0,JSON.stringify(chapterSaved[guideId].answers).slice(0,120));
  ok("上一轮作答保留",!!chapterSaved[guideId].lastAttempt&&
     chapterSaved[guideId].lastAttempt.answers.structure.indexOf("测试草稿")>=0);
  ok("新一轮不泄漏参考",!document.querySelector("#rebuild-reference"));

  location.hash="#/review"; await wait(220);
  ok("复习页有章节重建入口",document.querySelectorAll('a[href^="#/rebuild/"]').length>0);

  location.hash="#/rebuild/"+guideId; await wait(200);
  const realSet=Storage.prototype.setItem;
  Storage.prototype.setItem=function(){throw new DOMException("quota","QuotaExceededError")};
  const taFail=document.querySelector("#recall-structure");
  taFail.value="保存失败也保留当前输入"; taFail.dispatchEvent(new Event("input")); await wait(120);
  ok("保存失败有持续提示",document.querySelector("#rebuild-save").textContent.indexOf("保存失败")>=0);
  ok("保存失败仍保留输入",taFail.value.indexOf("保存失败")>=0);
  for(const [tid,txt] of [["relation","保存失败时也要说明关系。"],["application","保存失败时也要给出应用思路。"]]){
    const el=document.querySelector("#recall-"+tid);
    el.value=txt; el.dispatchEvent(new Event("input"));
  }
  document.querySelector('#rebuild-form button[type="submit"]').click(); await wait(180);
  ok("保存失败仍可展开参考",!!document.querySelector("#rebuild-reference"));
  ok("重绘不掩盖保存失败",document.querySelector("#rebuild-save").textContent.indexOf("保存失败")>=0);
  document.querySelector("#rebuild-new").click(); await wait(140);
  ok("保存失败不清空当前作答",document.querySelector("#recall-structure").value.indexOf("保存失败")>=0);
  Storage.prototype.setItem=realSet;

  location.hash="#/rebuild/none"; await wait(160);
  ok("无章前定位的重建地址回到框架",location.hash==="#/framework");

  location.hash="#/"; await wait(220);
  ok("回地图保留进度",prog()===doneAfterWrite+"/"+ids.length,prog());
  ok("进度按科目隔离",(()=>{
    try{return JSON.parse(localStorage.getItem(OTHER)||"{}").marker==="keep"}catch(e){return false}
  })());
  ok("无横向溢出",document.documentElement.scrollWidth<=window.innerWidth+1,document.documentElement.scrollWidth+" vs "+window.innerWidth);

  console.log("TESTRESULT "+pass+"/"+total);
})().catch(e=>console.log("TESTERROR "+e.message));
</script>
"""


def find_browser():
    for path in EDGE_CANDIDATES:
        if Path(path).exists():
            return path
    raise SystemExit("找不到 Edge/Chrome，无法运行自测")


def run_case(browser, subject, page):
    tmp = Path(tempfile.mkdtemp(prefix=f"yanxi-selftest-{subject}-"))
    test_file = tmp / "selftest.html"
    test_file.write_text(page, encoding="utf-8")
    url = test_file.as_uri() + (f"?subject={subject}" if subject == "822" else "")
    result = subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--no-first-run",
         "--enable-logging=stderr", "--v=0", "--virtual-time-budget=30000",
         "--window-size=1200,900", f"--screenshot={tmp / 'shot.png'}", url],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    text = (result.stderr or "") + (result.stdout or "")
    shutil.rmtree(tmp, ignore_errors=True)
    return text


def main():
    html = SOURCE.read_text(encoding="utf-8")
    if "</body>" not in html:
        raise SystemExit("index.html 缺少 </body>")
    page = html.replace("</body>", TEST + "\n</body>")
    browser = find_browser()
    passed = failed = 0
    incomplete = []
    for subject in ("618", "822"):
        print(f"\n===== {subject} =====")
        text = run_case(browser, subject, page)
        lines = [l for l in text.splitlines() if "TESTLOG" in l or "TESTRESULT" in l or "TESTERROR" in l]
        if not lines:
            print(text[-2000:])
            print(f"{subject}：没有输出，页面可能没启动")
            failed += 1
            continue
        for line in lines:
            clean = re.sub(r'^.*?CONSOLE:\d+\]\s*"', "", line).split('", source:')[0]
            if clean.startswith("TESTLOG"):
                print(clean[8:])
                if clean.startswith("TESTLOG FAIL"):
                    failed += 1
                else:
                    passed += 1
            else:
                print(clean)
        done = re.search(r'TESTRESULT (\d+)/(\d+)', text)
        if not done or done.group(1) != done.group(2) or "TESTERROR" in text:
            incomplete.append(subject)
    print(f"\n通过 {passed}，失败 {failed}")
    return 1 if failed or incomplete else 0


if __name__ == "__main__":
    sys.exit(main())
