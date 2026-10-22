"""Render the existing methods draft offline; never edits the source or old PDFs."""
if not __debug__:
    raise RuntimeError("Run without -O or PYTHONOPTIMIZE; documentation checks must remain enabled")

import argparse
from hashlib import sha256
import html
import importlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import markdown
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper/drafts/staged_deliverability_methods.md"
CSS = """
@page { size: A4; margin: 18mm 20mm 19mm; }
* { box-sizing: border-box; }
body { margin: 0; width: 170mm; color: #20242a;
       font: 10pt/1.66 'Microsoft YaHei', Arial, sans-serif; }
@media print { body { width: auto; } }
h1 { font-size: 20pt; line-height: 1.4; margin: 0 0 13pt; color: #19334b; }
h2 { font-size: 14pt; line-height: 1.4; margin: 17pt 0 8pt; color: #19334b; }
h3 { font-size: 11pt; line-height: 1.5; margin: 12pt 0 6pt; }
h1, h2, h3 { break-after: avoid; }
p { margin: 6pt 0; orphans: 3; widows: 3; }
p:has(+ .display-math), p:has(+ table) { break-after: avoid; }
a { color: inherit; text-decoration: none; }
table { border-collapse: collapse; width: 100%; margin: 9pt 0;
        font-size: 8.5pt; line-height: 1.5; break-inside: avoid; }
th, td { padding: 5pt; border: .5pt solid #b8c4cf; text-align: left; vertical-align: top; }
th { background: #eef3f7; font-weight: 700; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
.display-math { font-size: 10pt; break-inside: avoid; padding: 1pt 0; }
body[class] .katex { font-size: 1.05em; }
.display-math .katex-display { margin: 8pt 0; }
"""

KATEX_RENDER = r"""
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
const katex = (await import(pathToFileURL(process.argv[1]).href)).default;
const blocks = JSON.parse(fs.readFileSync(0, 'utf8'));
const rendered = blocks.map(b => katex.renderToString(b.tex, {
  displayMode:b.display, throwOnError:true, strict:'error', trust:false,
  output:'htmlAndMathml'
}));
process.stdout.write(JSON.stringify({version:katex.version, rendered}));
"""

PRINT_PDF = r"""
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
const [chrome, work, input, output] = process.argv.slice(1);
const log = fs.openSync(path.join(work, 'chrome.log'), 'wx');
const child = spawn(chrome, ['--headless=new','--disable-gpu','--no-first-run',
 '--no-default-browser-check','--disable-extensions','--disable-background-networking',
 '--disable-component-update','--disable-sync','--allow-file-access-from-files',
 '--remote-debugging-port=0','--user-data-dir='+path.join(work,'chrome_profile'),'about:blank'],
 {windowsHide:true,stdio:['ignore',log,log]});
let ws;
try {
  const portFile = path.join(work,'chrome_profile','DevToolsActivePort');
  const deadline = Date.now()+20000;
  while(!fs.existsSync(portFile)) {
    if(child.exitCode!==null || Date.now()>deadline) throw Error('Chrome startup failed');
    await delay(100);
  }
  const port=fs.readFileSync(portFile,'utf8').split('\n')[0];
  const targets=await (await fetch('http://127.0.0.1:'+port+'/json/list')).json();
  ws=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
  let sequence=0;
  const pending=new Map();
  ws.onmessage=event=>{
    const value=JSON.parse(event.data);
    if(pending.has(value.id)){
      const {resolve,reject,timer}=pending.get(value.id);pending.delete(value.id);
      clearTimeout(timer);value.error?reject(Error(JSON.stringify(value.error))):resolve(value.result);
    }
  };
  function call(method,params={}){
    return new Promise((resolve,reject)=>{
      const id=++sequence;
      const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout: '+method));},20000);
      pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}));
    });
  }
  await call('Page.enable');
  await call('Network.enable');
  await call('Network.setBlockedURLs',{urls:['http://*','https://*']});
  await call('Emulation.setDeviceMetricsOverride',{width:643,height:1000,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:pathToFileURL(input).href});
  const deadlineReady=Date.now()+20000;
  while(true){
    const state=await call('Runtime.evaluate',{expression:'document.readyState',returnByValue:true});
    if(state.result.value==='complete') break;
    if(Date.now()>deadlineReady) throw Error('HTML load timeout');
    await delay(100);
  }
  const result=await call('Runtime.evaluate',{awaitPromise:true,returnByValue:true,expression:
   "(async()=>{await document.fonts.ready; const box=document.body.getBoundingClientRect();"+
   "return {font_status:document.fonts.status,fonts:[...document.fonts].map(f=>({family:f.family,status:f.status})),"+
   "math_font:getComputedStyle(document.querySelector('.katex')).fontFamily,"+
   "math_count:document.querySelectorAll('.katex').length,display_count:document.querySelectorAll('.display-math').length,"+
   "errors:[...document.querySelectorAll('.katex-error')].map(e=>e.textContent),"+
   "overflow:[...document.querySelectorAll('.katex-html,table')].map(e=>({text:e.textContent,rect:e.getBoundingClientRect().toJSON()}))"+
   ".filter(e=>e.rect.left<box.left-1||e.rect.right>box.right+1)};})()"});
  if(result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
  const audit=result.result.value;
  if(audit.errors.length||audit.overflow.length||audit.font_status!=='loaded') throw Error(JSON.stringify(audit));
  const pdf=await call('Page.printToPDF',{printBackground:true,preferCSSPageSize:true,displayHeaderFooter:true,
   headerTemplate:'<span></span>',
   footerTemplate:'<div style="font-size:7px;width:100%;padding:0 20mm;color:#59636e;display:flex;justify-content:space-between"><span>Staged deliverability | METHOD DRAFT | 2026-10-23</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'});
  fs.writeFileSync(output,Buffer.from(pdf.data,'base64'),{flag:'wx'});
  const version=await call('Browser.getVersion');
  fs.writeFileSync(path.join(work,'browser_check.json'),JSON.stringify({version,audit},null,2),{flag:'wx'});
  await call('Browser.close');
} finally {
  if(ws) ws.close();
  if(child.exitCode===null){
    await Promise.race([new Promise(r=>child.once('exit',r)),delay(5000)]);
    if(child.exitCode===null) child.kill();
  }
  fs.closeSync(log);
}
"""


def stamp(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--katex-js", type=Path, required=True)
    parser.add_argument("--katex-css", type=Path, required=True)
    parser.add_argument("--pdf-deps", type=Path)
    parser.add_argument("--chrome", type=Path, default=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
    args = parser.parse_args()
    if args.pdf_deps:
        sys.path.insert(0, str(args.pdf_deps.resolve()))
    pymupdf = importlib.import_module("pymupdf")
    source_pin = stamp(SOURCE)
    asset_pins = {str(p.resolve()): stamp(p) for p in (args.katex_js, args.katex_css)}
    for url in re.findall(r'url\(([^)]+)\)', args.katex_css.read_text(encoding="utf-8")):
        if not url.startswith("data:"):
            path = (args.katex_css.resolve().parent / url.strip("'\"")).resolve()
            asset_pins[str(path)] = stamp(path)
    source = SOURCE.read_text(encoding="utf-8")
    work = Path(tempfile.mkdtemp(prefix="electricity-grid-methods-"))
    blocks = []

    def capture(match):
        display = match[1] is not None
        tex = match[1] if display else match[2]
        blocks.append(dict(tex=tex, display=display))
        return "MATHRENDERPLACEHOLDER" + str(len(blocks)-1) + "END"

    assert "MATHRENDERPLACEHOLDER" not in source
    prepared = re.sub(r"\$\$(.*?)\$\$|\\\((.*?)\\\)", capture, source, flags=re.S)
    rendered = subprocess.run(
        ["node", "--input-type=module", "-e", KATEX_RENDER, str(args.katex_js.resolve())],
        input=json.dumps(blocks).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=30, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    math = json.loads(rendered.stdout)
    assert len(math["rendered"]) == len(blocks)
    body = markdown.markdown(prepared, extensions=["tables", "sane_lists"])
    for i, (block, markup) in enumerate(zip(blocks, math["rendered"])):
        token = "MATHRENDERPLACEHOLDER" + str(i) + "END"
        fragment = '<div class="display-math">' + markup + "</div>" if block["display"] else markup
        if block["display"]:
            body = body.replace("<p>"+token+"</p>", fragment)
        body = body.replace(token, fragment)
    assert "MATHRENDERPLACEHOLDER" not in body
    body = re.sub(r'<a href="(?!https?://)[^"]*">', "<a>", body)
    scope = re.search(r"\.([\w-]+)\s+\.katex\{", args.katex_css.read_text(encoding="utf-8"))
    scope_class = scope[1] if scope else ""
    document = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
                '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\' file:; font-src file: data:; img-src data:">'
                '<title>分阶段接入计划的连续时序评价方法</title>'
                '<link rel="stylesheet" href="' + html.escape(args.katex_css.resolve().as_uri()) + '">'
                '<style>' + CSS + '</style></head><body class="' + html.escape(scope_class) + '">' + body + '</body></html>')
    html_path, pdf_path = work / "methods.html", work / "methods.pdf"
    html_path.write_text(document, encoding="utf-8")
    result = subprocess.run(
        ["node", "--input-type=module", "-e", PRINT_PDF, str(args.chrome.resolve()),
         str(work), str(html_path), str(pdf_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=70, creationflags=subprocess.CREATE_NO_WINDOW)
    (work/"node_stdout.log").write_bytes(result.stdout)
    (work/"node_stderr.log").write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError("Offline PDF print failed; inspect " + str(work))
    browser = json.loads((work/"browser_check.json").read_bytes())
    assert browser["audit"]["math_count"] == len(blocks)
    assert browser["audit"]["display_count"] == 23
    assert not any(f["status"] == "error" for f in browser["audit"]["fonts"])
    assert any(f["status"] == "loaded" and f["family"] == "KaTeX_Main" for f in browser["audit"]["fonts"])
    assert "KaTeX_Main" in browser["audit"]["math_font"]
    doc = pymupdf.open(pdf_path)
    errors, text, pages = [], [], []
    for index, page in enumerate(doc):
        value = page.get_text()
        text.append(value)
        if len(value.strip()) < 40 or "\ufffd" in value:
            errors.append(dict(page=index+1, reason="blank_or_replacement_text"))
        for span in (s for b in page.get_text("dict")["blocks"] if b["type"] == 0
                     for line in b["lines"] for s in line["spans"]):
            x0, y0, x1, y1 = span["bbox"]
            if x0 < 24 or x1 > page.rect.width-24 or y0 < 20 or y1 > page.rect.height-12:
                errors.append(dict(page=index+1, reason="text_outside_page_safe_area", text=span["text"]))
        target = work / f"page_{index+1:02d}.png"
        page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False).save(target)
        pages.append(target)
    for start in range(0, len(pages), 4):
        canvas = Image.new("RGB", (1100, 1600), "#e8edf1")
        draw = ImageDraw.Draw(canvas)
        for j, path in enumerate(pages[start:start+4]):
            image = Image.open(path)
            image.thumbnail((530, 750))
            x, y = (j % 2)*550+(550-image.width)//2, (j//2)*800+28
            canvas.paste(image, (x, y))
            draw.text(((j % 2)*550+12, (j//2)*800+8), f"Page {start+j+1}", fill="black")
        canvas.save(work / f"contact_{start//4+1:02d}.png")
    assert stamp(SOURCE) == source_pin
    assert all(stamp(Path(name)) == pin for name, pin in asset_pins.items())
    all_text = "\n".join(text)
    chinese = lambda value: "".join(re.findall(r"[\u3400-\u9fff]", value))
    assert chinese(source) == chinese(all_text), "Chinese body text changed during rendering"
    equation_labels = [int(n) for n in re.findall(r"\((\d{1,2})\)", all_text)]
    assert equation_labels == list(range(1, 24)), equation_labels
    report = dict(authority="DRAFT_NONAUTHORITATIVE", scope="offline_methods_document_render",
                  source={SOURCE.relative_to(ROOT).as_posix(): source_pin},
                  renderer=stamp(Path(__file__)), pdf=stamp(pdf_path),
                  katex=dict(version=math["version"], css_scope_class=scope_class, javascript=stamp(args.katex_js),
                             css=stamp(args.katex_css)), chrome=browser["version"],
                  local_math_asset_pins=asset_pins,
                  markdown_version=markdown.__version__, pymupdf_version=pymupdf.VersionBind,
                  math_count=len(blocks), display_equations=23, pages=len(doc),
                  pdf_equation_labels=equation_labels, chinese_text_preserved=True,
                  pdf_fonts=sorted({font[3] for page in doc for font in page.get_fonts()}),
                  page_text_characters=[len(t) for t in text], errors=errors,
                  browser_audit=browser["audit"], visual_review_required=True,
                  page_network_blocked_patterns=["http://*", "https://*"],
                  controller_loopback_cdp=True, controller_transport="http_and_websocket_on_127.0.0.1",
                  cleanup_scope="owned_direct_chrome_child_only", solver_calls=0,
                  formal_result=False, official_verdict=None, receipt=None, seal=None)
    (work/"render_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (work/"extracted_text.txt").write_text("\n\f\n".join(text), encoding="utf-8")
    print(json.dumps(dict(work_dir=str(work), pages=len(doc), math_count=len(blocks), errors=errors)), flush=True)
    if errors:
        raise RuntimeError("PDF geometry/text checks failed")


if __name__ == "__main__":
    main()
