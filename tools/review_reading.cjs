// Offline Edge regression: NODE_PATH points to an existing Playwright runtime.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..');
const out=path.join(root,'截图','reading');
const url=pathToFileURL(path.join(root,'index.html')).href;
let checks=0;
const check=(value,label)=>{assert.ok(value,label);checks++};
(async()=>{
  fs.mkdirSync(out,{recursive:true});
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const measurements=[];
  try{
    for(const subject of ['618','822']){
      const context=await browser.newContext({offline:true,viewport:{width:1440,height:960}});
      const page=await context.newPage();
      const errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.goto(`${url}?subject=${subject}`);
      const data=await page.evaluate(()=>JSON.parse(document.querySelector(
        new URLSearchParams(location.search).get('subject')==='822'?'#policy-data':'#course-data'
      ).textContent));
      const course=data.course||data;
      const lesson=Object.keys(course.lessons).find(id=>course.lessons[id].write);
      const moduleId=Object.keys(course.framework.guides)[0];
      check(await page.locator('#reading-size').inputValue()==='large','Default large');
      const key=`yanxi-${subject}-v2`,other=`yanxi-${subject==='618'?'822':'618'}-v2`;
      await page.evaluate(({other})=>{
        localStorage.setItem(other,JSON.stringify({marker:'另一科进度'}));
      },{other});
      const go=async(route)=>{await page.evaluate(r=>{location.hash=r},route);await page.waitForTimeout(80)};
      await go(`#/lesson/${lesson}`);
      await page.locator('.write textarea').fill('原有写作');
      await page.waitForTimeout(700);
      const progress=await page.evaluate(k=>localStorage.getItem(k),key);
      for(const size of ['standard','large','extra']){
        await go(`#/lesson/${lesson}`);
        await page.locator('#reading-size').selectOption(size);
        check(await page.evaluate(k=>localStorage.getItem(k),key)===progress,'Resizing preserves progress');
        check(await page.locator('.write textarea').inputValue()==='原有写作','Resizing preserves draft');
        await page.reload();
        check(await page.locator('#reading-size').inputValue()===size,'Preference survives reload');
        const font=await page.locator('.prose').first().evaluate(e=>parseFloat(getComputedStyle(e).fontSize));
        check(font==={standard:16,large:20,extra:24}[size],`Reading font ${size}: ${font}`);
        if(size==='standard')continue;
        for(const width of [320,390,768,1440,1728]){
          await page.setViewportSize({width,height:960});
          for(const route of ['#/',`#/lesson/${lesson}`,'#/exam','#/points','#/review','#/framework',`#/module/${moduleId}`,`#/rebuild/${moduleId}`]){
            await go(route);
            if(route==='#/exam')await page.locator('.exam-card summary').first().click();
            const metrics=await page.evaluate(()=>{
              const visible=e=>!!(e.offsetWidth||e.offsetHeight);
              const overflow=[...document.querySelectorAll('body *')].filter(e=>{
                if(!visible(e)||e.closest('table.cmp,.nav,.secnav,.aside-modules'))return false;
                const r=e.getBoundingClientRect();
                return r.right>innerWidth+1&&r.width>0;
              }).slice(0,8).map(e=>e.tagName+'.'+e.className);
              return {width:innerWidth,scroll:document.documentElement.scrollWidth,overflow};
            });
            measurements.push({subject,size,route,...metrics});
            check(metrics.scroll<=width+1,`${subject} ${size} ${width} ${route} overflow ${JSON.stringify(metrics)}`);
            if(width>760)check(await page.locator('.aside-modules button').evaluateAll(buttons=>
              buttons.every(b=>b.scrollHeight<=b.clientHeight+1)
            ),'Sidebar chapter labels fit their rows');
            if(subject==='618'&&[390,1440].includes(width)&&['#/',`#/lesson/${lesson}`].includes(route)){
              await page.screenshot({path:path.join(out,`${size}-${width}-${route==='#/'?'map':'lesson'}.png`)});
              if(route!== '#/'){
                await page.locator('.prose').first().scrollIntoViewIfNeeded();
                await page.screenshot({path:path.join(out,`${size}-${width}-reading.png`)});
              }
            }
          }
        }
      }
      await page.locator('#open-search').click();
      await page.locator('#palette-input').fill('公共');
      check(await page.locator('.pal-item').count()>0,'Search works with enlarged text');
      await page.keyboard.press('Escape');
      check(await page.locator('#palette').isHidden(),'Search closes with keyboard');
      await page.locator('#reading-size').focus();
      check(await page.locator('#reading-size').evaluate(e=>getComputedStyle(e).outlineStyle!=='none'),'Keyboard focus visible');
      await page.keyboard.press('Home');
      await page.keyboard.press('Enter');
      check(await page.locator('#reading-size').inputValue()==='standard','Keyboard can change size');
      await page.locator('#reading-size').selectOption('extra');
      await page.locator('#subject-select').selectOption(subject==='618'?'822':'618');
      await page.waitForURL(u=>u.searchParams.get('subject')!==subject);
      check(await page.locator('#reading-size').inputValue()==='extra','Subject switch shares reading size');
      check(await page.evaluate(k=>JSON.parse(localStorage.getItem(k)).marker,other)==='另一科进度','Other subject preserved');
      check(errors.length===0,'No JavaScript errors: '+errors.join(';'));
      await context.close();
    }
    for(const blocked of [false,true]){
      const context=await browser.newContext({offline:true});
      await context.addInitScript(({blocked})=>{
        if(blocked){
          Storage.prototype.getItem=()=>{throw new Error('storage blocked')};
          Storage.prototype.setItem=()=>{throw new Error('storage blocked')};
        }else localStorage.setItem('yanxi-reading-size','invalid-value');
      },{blocked});
      const page=await context.newPage();
      await page.goto(url);
      check(await page.locator('#reading-size').inputValue()==='large','Unavailable/invalid storage defaults large');
      await page.locator('#reading-size').selectOption('extra');
      check(await page.locator('html').getAttribute('data-reading')==='extra','Reading works without storage');
      if(blocked)check((await page.locator('#reading-status').textContent()).includes('未允许保存'),'Failed save is explained');
      await context.close();
    }
    fs.writeFileSync(path.join(out,'measurements.json'),JSON.stringify(measurements,null,2));
    console.log(`PASS ${checks} checks; screenshots and DOM widths: ${out}`);
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
