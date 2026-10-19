// NODE_PATH 指向含 playwright 的已有运行时；全程 file:// 验证离线单页。
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

(async () => {
  const root = path.resolve(__dirname, '..');
  const out = path.join(root, '截图', 'mineru核验');
  fs.mkdirSync(out, {recursive:true});
  const capture = fs.readFileSync(path.join(__dirname, 'spacing_capture.js'), 'utf8');
  const browser = await chromium.launch({channel:'msedge', headless:true});
  const errors = [];
  const results = [];
  try {
    for (const width of [390,1440,1728]) {
      for (const [subject, lesson] of [['618','l3-6'],['822','p6-4']]) {
        const context = await browser.newContext({viewport:{width,height:960},offline:true});
        const page = await context.newPage();
        page.on('pageerror', e => errors.push(e.message));
        await page.goto(pathToFileURL(path.join(root,'index.html')).href+`?subject=${subject}#/lesson/${lesson}`);
        await page.waitForLoadState('networkidle');
        await page.evaluate(() => document.fonts.ready);
        await page.screenshot({path:path.join(out,`${subject}-${width}-lesson.png`)});
        const summary = page.locator('#sec-evid > summary');
        await summary.focus();
        await page.keyboard.press('Enter');
        if (!await page.locator('#sec-evid').evaluate(e=>e.open)) throw Error('依据无法由键盘展开');
        const inner = page.locator('#sec-evid details').first();
        await inner.locator('summary').focus();
        await page.keyboard.press('Enter');
        if (!await inner.evaluate(e=>e.open)) throw Error('前后文无法由键盘展开');
        await inner.scrollIntoViewIfNeeded();
        if (!await inner.locator('.source-context').isVisible()) throw Error('前后文不可见');
        await page.screenshot({path:path.join(out,`${subject}-${width}-source.png`)});
        const state = await page.evaluate(capture);
        state.name = `${subject}-lesson-source-${width}`;
        fs.writeFileSync(path.join(out,`${subject}-${width}-spacing.json`),JSON.stringify(state));
        const sizes = await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,font:getComputedStyle(document.body).fontFamily}));
        if(sizes.scroll>sizes.width+1) throw Error('课时页面横向溢出');
        results.push({subject,width,sourceKeyboard:true,offline:true,...sizes});
        for(const route of ['#/','#/points']) {
          await page.evaluate(route=>{location.hash=route;},route);
          await page.waitForTimeout(80);
          if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)) throw Error(`${subject} ${route} ${width} 横向溢出`);
        }
        await context.close();
      }
    }
    if(errors.length) throw Error(errors.join('\n'));
    fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify(results,null,2));
    console.log(JSON.stringify({passed:results.length,errors,results}));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1);});
