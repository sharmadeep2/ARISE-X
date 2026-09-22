// Copyright (c) Microsoft Corporation.
// SPDX-License-Identifier: MIT
// Node built-ins only: static KaTeX conversion, isolated CDP print, PDF inspection.
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
if (args[0] === '--math') {
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  const katex = createRequire(import.meta.url)(args[1]);
  const result = JSON.parse(input).map(({tex, display}) => katex.renderToString(tex, {
    displayMode: display, throwOnError: true, strict: 'error', trust: false,
    output: 'htmlAndMathml', maxExpand: 1000,
  }));
  process.stdout.write(JSON.stringify(result));
} else {
  await renderBuiltin(...args);
}

async function renderBuiltin(browser, html, pdf, assets, verification) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  for (const candidate of [html, pdf, assets]) {
    const relative = path.relative(root, path.resolve(candidate));
    if (relative.startsWith('..') || path.isAbsolute(relative)) throw Error('Outside research');
  }
  const work = pdf.replace(/\.pdf$/i, '.validation');
  await mkdir(work, {recursive:true});
  async function launch(url, extra) {
    const run = path.join(work, `builtin-${Date.now()}`);
    const env = {...process.env};
    for (const key of ['TEMP','TMP','TMPDIR','USERPROFILE','HOME','LOCALAPPDATA','APPDATA','XDG_CACHE_HOME','XDG_CONFIG_HOME']) {
      env[key] = path.join(run, key.toLowerCase());
      await mkdir(env[key], {recursive:true});
    }
    const flags = ['--headless=new', `--user-data-dir=${path.join(run,'profile')}`,
      `--disk-cache-dir=${path.join(run,'cache')}`,`--crash-dumps-dir=${path.join(run,'crashes')}`,
      '--disable-crash-reporter','--disable-breakpad','--disable-background-networking',
      '--disable-component-update','--disable-sync','--disable-extensions','--no-first-run',
      '--no-default-browser-check','--disable-default-apps','--metrics-recording-only',
      '--disable-features=OptimizationHints,MediaRouter','--password-store=basic',
      '--allow-file-access-from-files','--host-resolver-rules=MAP * ~NOTFOUND',
      '--run-all-compositor-stages-before-draw','--virtual-time-budget=15000', ...extra, url];
    return await new Promise((resolve,reject) => {
      const child = spawn(browser, flags, {env,cwd:run,stdio:['ignore','pipe','pipe']});
      let stdout='', stderr='';
      const timer = setTimeout(()=> {child.kill();reject(Error('Built-in browser timeout'));},90000);
      child.stdout.on('data', chunk=>stdout+=chunk.toString());
      child.stderr.on('data', chunk=>stderr+=chunk.toString());
      child.once('error', reject);
      child.once('close', async code=> {
        clearTimeout(timer);
        await writeFile(path.join(run,'stderr.log'),stderr);
        await writeFile(path.join(run,'stdout.html'),stdout);
        if(code!==0) reject(Error(`Browser exit ${code}: ${stderr}`));
        else resolve(stdout);
      });
    });
  }
  function evidence(dom) {
    const found=dom.match(/<script id="evidence" type="application\/json">([\s\S]*?)<\/script>/);
    if(!found) throw Error('Browser did not finish inspection');
    const result=JSON.parse(found[1]);
    if(result.error) throw Error(result.error);
    return result;
  }
  const emit = `function emit(value){const e=document.createElement('script');e.id='evidence';e.type='application/json';e.textContent=JSON.stringify(value);document.body.append(e);}`;
  const original=await readFile(html,'utf8');
  const probe=path.join(work,'html-inspector.html');
  await writeFile(probe, original.replace("default-src 'none';", "default-src 'none'; script-src 'unsafe-inline';") + `<script>${emit}
    addEventListener('load',async()=>{await document.fonts.ready;
    const overflow=[...document.querySelectorAll('pre,table,.katex-display')].filter(e=>e.scrollWidth>e.clientWidth+2).map(e=>({tag:e.tagName,width:e.clientWidth,scroll:e.scrollWidth,text:e.innerText.slice(0,80)}));
    emit({math:document.querySelectorAll('math').length,katexErrors:document.querySelectorAll('.katex-error').length,overflow,fonts:document.fonts.status,missingAnchors:[...document.querySelectorAll('a[href^="#"]')].filter(a=>!document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a=>a.hash),codeLines:[...document.querySelectorAll('pre')].map(e=>e.innerText.trimEnd().split('\\n').length)});});</script>`);
  const layout=evidence(await launch(pathToFileURL(probe).href,['--window-size=673,1123','--dump-dom']));
  await writeFile(path.join(work,'html-layout.json'),JSON.stringify(layout,null,2));
  if(layout.overflow.length || layout.missingAnchors.length || layout.katexErrors) throw Error(`HTML layout failed: ${JSON.stringify(layout)}`);
  await launch(pathToFileURL(html).href,[`--print-to-pdf=${pdf}`,'--no-pdf-header-footer']);
  const bytes=await readFile(pdf);
  if(!bytes.subarray(0,5).equals(Buffer.from('%PDF-'))) throw Error('Invalid PDF signature');
  if(verification!=='--verify') return;
  const inspector=path.join(work,'pdf-inspector.html');
  await writeFile(inspector,`<!doctype html><meta charset="utf-8"><title>Actual PDF inspection</title>
  <style>body{margin:0;background:#aeb8c2}canvas{display:block;background:white}</style><canvas></canvas>
  <script type="module">${emit}
  try {
    const pdfjs=await import(${JSON.stringify(pathToFileURL(path.join(assets,'pdf.mjs')).href)});
    globalThis.pdfjsWorker=await import(${JSON.stringify(pathToFileURL(path.join(assets,'pdf.worker.mjs')).href)});
    const pdf=await pdfjs.getDocument({url:${JSON.stringify(pathToFileURL(pdf).href)},isEvalSupported:false}).promise;
    const number=Number(new URL(location.href).searchParams.get('page')||1);
    const page=await pdf.getPage(number);const viewport=page.getViewport({scale:1.3});
    const canvas=document.querySelector('canvas');canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
    await page.render({canvasContext:canvas.getContext('2d'),viewport,intent:'print'}).promise;
    const text=await page.getTextContent();const annotations=await page.getAnnotations();
    emit({page:number,pages:pdf.numPages,view:page.view,text:text.items.map(t=>t.str).join(' '),items:text.items,
      links:annotations.filter(a=>a.subtype==='Link').map(a=>({url:a.url,dest:a.dest,rect:a.rect})),
      outOfBounds:text.items.filter(t=>t.str&&(t.transform[4]<-1||t.transform[4]+t.width>page.view[2]+1)),
      outline:number===1?await pdf.getOutline():null});
  }catch(error){emit({error:String(error)});}
  </script>`);
  const pages=[];
  let total=1;
  for(let number=1;number<=total;number++) {
    const pageUrl=pathToFileURL(inspector).href+`?page=${number}`;
    const dom=await launch(pageUrl,['--window-size=775,1096','--hide-scrollbars','--dump-dom']);
    const data=evidence(dom);total=data.pages;pages.push(data);
    await launch(pageUrl,['--window-size=775,1096','--hide-scrollbars',`--screenshot=${path.join(work,`pdf-page-${number}.png`)}`]);
  }
  await writeFile(path.join(work,'pdf-evidence.json'),JSON.stringify({bytes:bytes.length,pageCount:total,pages},null,2));
  await writeFile(path.join(work,'pdf-text.txt'),pages.map(p=>`PAGE ${p.page}\n${p.text}`).join('\n\n'));
  if(pages.some(p=>p.outOfBounds.length)) throw Error('PDF text outside horizontal page boundaries');
  console.log(JSON.stringify({pdf,pages:total,bytes:bytes.length,links:pages.reduce((n,p)=>n+p.links.length,0),math:layout.math,screenshots:work}));
}

async function render(browser, html, pdf, assets, verification) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  for (const candidate of [html, pdf, assets]) {
    const relative = path.relative(root, path.resolve(candidate));
    if (relative.startsWith('..') || path.isAbsolute(relative)) throw Error('Outside research');
  }
  const work = pdf.replace(/\.pdf$/i, '.validation');
  const run = path.join(work, `browser-${Date.now()}`);
  const env = {...process.env};
  for (const name of ['TEMP', 'TMP', 'TMPDIR', 'USERPROFILE', 'HOME', 'LOCALAPPDATA', 'APPDATA', 'XDG_CACHE_HOME', 'XDG_CONFIG_HOME']) {
    env[name] = path.join(run, name.toLowerCase());
    await mkdir(env[name], {recursive: true});
  }
  const browserArgs = [
    '--headless=new', '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1',
    `--user-data-dir=${path.join(run, 'profile')}`, `--disk-cache-dir=${path.join(run, 'cache')}`,
    `--crash-dumps-dir=${path.join(run, 'crashes')}`, '--disable-crash-reporter', '--disable-breakpad',
    '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
    '--disable-component-update', '--disable-sync', '--disable-extensions', '--disable-default-apps',
    '--disable-features=OptimizationHints,MediaRouter', '--metrics-recording-only',
    '--password-store=basic', '--use-mock-keychain', '--allow-file-access-from-files',
    '--host-resolver-rules=MAP * ~NOTFOUND', 'about:blank',
  ];
  const child = spawn(browser, browserArgs, {env, cwd: run, stdio: ['ignore', 'ignore', 'pipe']});
  let logs = '';
  let ws;
  try {
    const endpoint = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(Error('Browser start timed out')), 30000);
      child.once('error', reject);
      child.once('exit', code => reject(Error(`Browser exited early: ${code}`)));
      child.stderr.on('data', chunk => {
        logs += chunk.toString();
        const found = logs.match(/DevTools listening on (ws:\/\/[^\s]+)/);
        if (found) { clearTimeout(timer); resolve(found[1]); }
      });
    });
    ws = new WebSocket(endpoint);
    await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
    let counter = 0;
    const pending = new Map();
    ws.onmessage = event => {
      const message = JSON.parse(event.data);
      if (!pending.has(message.id)) return;
      const {resolve, reject, timer} = pending.get(message.id);
      clearTimeout(timer);
      pending.delete(message.id);
      if (message.error) reject(Error(JSON.stringify(message.error)));
      else resolve(message.result);
    };
    function cdp(method, params = {}, sessionId) {
      return new Promise((resolve, reject) => {
        const id = ++counter;
        const timer = setTimeout(() => { pending.delete(id); reject(Error(`CDP timeout: ${method}`)); }, 60000);
        pending.set(id, {resolve, reject, timer});
        ws.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}));
      });
    }
    const {targetId} = await cdp('Target.createTarget', {url: 'about:blank'});
    const {sessionId} = await cdp('Target.attachToTarget', {targetId, flatten: true});
    const send = (method, params) => cdp(method, params, sessionId);
    async function evaluate(expression) {
      const result = await send('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
      if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
      return result.result.value;
    }
    await send('Page.enable');
    await send('Network.enable');
    await send('Network.setBlockedURLs', {urls: ['http://*', 'https://*']});
    await send('Emulation.setDeviceMetricsOverride', {width: 673, height: 1123, deviceScaleFactor: 1, mobile: false});
    await send('Emulation.setEmulatedMedia', {media: 'print'});
    await send('Page.navigate', {url: pathToFileURL(html).href});
    await evaluate(`new Promise(resolve => { if (document.readyState === 'complete') resolve(); else addEventListener('load', resolve, {once:true}); }).then(() => document.fonts.ready)`);
    const layout = await evaluate(`(() => {
      const main = document.querySelector('main');
      const missing = [...document.querySelectorAll('a[href^="#"]')].filter(a => !document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a => a.hash);
      const overflow = [...document.querySelectorAll('pre,table,.katex-display')].filter(e => e.scrollWidth > e.clientWidth + 2).map(e => ({tag:e.tagName, text:e.innerText.slice(0,80),width:e.clientWidth,scroll:e.scrollWidth}));
      return {title: document.title, math: document.querySelectorAll('math').length, katexErrors: document.querySelectorAll('.katex-error').length, missingAnchors:missing, overflow, codeLines:[...document.querySelectorAll('pre')].map(e=>e.innerText.trimEnd().split('\\n').length), mainPresent:!!main, fonts:document.fonts.status};
    })()`);
    await writeFile(path.join(work, 'html-layout.json'), JSON.stringify(layout, null, 2));
    if (!layout.mainPresent || layout.katexErrors || layout.missingAnchors.length || layout.overflow.length) {
      throw Error(`HTML validation failed: ${JSON.stringify(layout)}`);
    }
    const result = await send('Page.printToPDF', {
      printBackground: true, preferCSSPageSize: true, displayHeaderFooter: true,
      headerTemplate: '<span></span>',
      footerTemplate: '<div style="font-family:Arial;font-size:8px;color:#50647c;width:100%;text-align:center">Learning handbook &nbsp; | &nbsp; <span class="pageNumber"></span> / <span class="totalPages"></span></div>',
      generateTaggedPDF: true, generateDocumentOutline: true,
    });
    const bytes = Buffer.from(result.data, 'base64');
    if (!bytes.subarray(0, 5).equals(Buffer.from('%PDF-'))) throw Error('Invalid PDF signature');
    await writeFile(pdf, bytes);
    if (verification === '--verify') {
      // A separate local PDF.js canvas inspects the generated PDF, not its source HTML.
      const inspector = path.join(work, 'pdf-inspector.html');
      await writeFile(inspector, '<!doctype html><meta charset="utf-8"><title>Local PDF inspection</title><style>body{margin:0;background:#aeb8c2}canvas{display:block;background:white;margin:0 auto}</style><canvas id="page"></canvas>');
      await send('Page.navigate', {url: pathToFileURL(inspector).href});
      await evaluate(`new Promise(resolve => { if(document.readyState==='complete')resolve();else addEventListener('load',resolve,{once:true}); })`);
      const init = `async () => {
        const pdfjs = await import(${JSON.stringify(pathToFileURL(path.join(assets, 'pdf.mjs')).href)});
        pdfjs.GlobalWorkerOptions.workerSrc = ${JSON.stringify(pathToFileURL(path.join(assets, 'pdf.worker.mjs')).href)};
        globalThis.checkedPdf = await pdfjs.getDocument({url:${JSON.stringify(pathToFileURL(pdf).href)}, isEvalSupported:false}).promise;
        return {pages:checkedPdf.numPages, metadata:await checkedPdf.getMetadata(), outline:await checkedPdf.getOutline()};
      }`;
      const info = await evaluate(`(${init})()`);
      const pages = [];
      for (let number = 1; number <= info.pages; number++) {
        const pageResult = await evaluate(`(async () => {
          const page = await checkedPdf.getPage(${number});
          const viewport = page.getViewport({scale:1.3});
          const canvas = document.querySelector('canvas');
          canvas.width = Math.ceil(viewport.width); canvas.height = Math.ceil(viewport.height);
          await page.render({canvasContext:canvas.getContext('2d'),viewport}).promise;
          const text = await page.getTextContent();
          const annotations = await page.getAnnotations();
          const outOfBounds = text.items.filter(t => t.str && (t.transform[4] < -1 || t.transform[4] + t.width > page.view[2]+1));
          return {page:${number}, view:page.view, text:text.items.map(t=>t.str).join(' '), items:text.items, links:annotations.filter(a=>a.subtype==='Link').map(a=>({url:a.url,dest:a.dest,rect:a.rect})),outOfBounds, width:canvas.width,height:canvas.height};
        })()`);
        await send('Emulation.setDeviceMetricsOverride', {width: pageResult.width, height: pageResult.height, deviceScaleFactor: 1, mobile: false});
        const screenshot = await send('Page.captureScreenshot', {format:'png', captureBeyondViewport:true});
        await writeFile(path.join(work, `pdf-page-${number}.png`), Buffer.from(screenshot.data, 'base64'));
        pages.push(pageResult);
      }
      await writeFile(path.join(work, 'pdf-evidence.json'), JSON.stringify({bytes:bytes.length, ...info, pages}, null, 2));
      await writeFile(path.join(work, 'pdf-text.txt'), pages.map(p=>`PAGE ${p.page}\n${p.text}`).join('\n\n'));
      if (pages.some(p=>p.outOfBounds.length)) throw Error('PDF text outside horizontal page boundaries');
      console.log(JSON.stringify({pdf, pages:info.pages, bytes:bytes.length, links:pages.reduce((n,p)=>n+p.links.length,0), math:layout.math, screenshots:work}));
    }
    await cdp('Browser.close');
  } finally {
    ws?.close();
    if (child.exitCode === null) child.kill();
    await writeFile(path.join(work, 'browser-stderr.log'), logs);
  }
}