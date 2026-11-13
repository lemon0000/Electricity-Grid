"""Assemble editable Scheme A guides around unchanged project cartoon assets.

Nonquantitative research-design figures. Native SVG additions; no raster edits.
Run this script to rebuild eight SVG/PDF/300-dpi PNG figures and their manifest.
"""
import base64
import hashlib
import json
from html import escape
from pathlib import Path
import struct
import subprocess
import tempfile
import pymupdf

OUT = Path(__file__).resolve().parent
W = 519
FONT = 'Arial, Microsoft YaHei, sans-serif'
INK = '#23364A'

def text(x, y, s, size=9, bold=False, anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{anchor}" fill="{INK}">{escape(s)}</text>'

def rect(x,y,w,h,fill='#EDF5F7'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{fill}" stroke="#B5C8D1" stroke-width="0.6"/>'

def art(name,y,height=None,crop=None):
    data=(OUT/name).read_bytes()
    w,h=struct.unpack('>II',data[16:24])
    uri='data:image/png;base64,'+base64.b64encode(data).decode()
    if crop:
        return f'<svg x="0" y="{y}" width="519" height="{height}" viewBox="{crop}" preserveAspectRatio="xMidYMid meet"><image width="{w}" height="{h}" href="{uri}"/></svg>'
    return f'<image x="0" y="{y}" width="519" height="{height or W*h/w}" preserveAspectRatio="xMidYMid meet" href="{uri}"/>'

def band(y,title,lines):
    parts=[rect(8,y,503,25+15*len(lines)),text(18,y+17,title,10,True)]
    parts += [text(18,y+34+15*i,line,9) for i,line in enumerate(lines)]
    return ''.join(parts)

def cards(y,items):
    p=[]
    for i,(title,lines) in enumerate(items):
        x=8+i*171
        p += [rect(x,y,161,91,'#FFF3DF' if i==1 else '#EDF5F7'),text(x+9,y+18,title,10,True)]
        p += [text(x+9,y+37+j*14,line,8.6) for j,line in enumerate(lines)]
    return ''.join(p)

def figure(key,lang):
    zh=lang=='cn'
    t=lambda a,b:a if zh else b
    titles={
      'framework':t('阶段接入、通知与状态保留','Stage capacity, notice and state preservation'),
      'recovery':t('暂停后，状态可以在哪里保留？','Where can state survive a pause?'),
      'rampup':t('三条进度共同改变接纳边界','Three progress paths shape admission boundaries'),
      'network':t('状态控制必须进入全站功率核算','State control enters whole-site power accounting'),
    }
    p=[]
    if key=='framework':
        # Preserve the existing business/equipment/grid cartoon row verbatim.
        # SVG viewport clipping selects the native source row; no pixels are edited.
        p += [art(f'project_framework_cartoon_v3_{lang}.png',42,74,'200 70 1360 185')]
        p += [band(125,t('1  适用合同与共同条件','1  Applicable agreement and common conditions'),[
            t('容量曲线 · 调用通知 · 持续时间 · 原任务期限','Import profile · call notice · duration · original deadlines'),
            t('已投运设备 · 可用本地电源 · 软件兼容性 · 小时CFE','Commissioned assets · permitted local supply · compatibility · hourly CFE')])]
        p += [text(18,196,t('状态保护方式可组合；主机暂存可继续转为持久化保存。','Paths can combine: host staging may precede durable saving.'),8.6)]
        p += [cards(202,[(t('2a  GPU保活','2a  GPU retention'),[
            t('停止部分计算','Pause some computation'),t('GPU与配套持续供电','Power GPU and support'),t('必要状态仍可恢复','Keep necessary state')]),
            (t('2b  主机暂存','2b  Host staging'),[t('先完成GPU到主机复制','Complete GPU-to-host copy'),t('主机内存仍需保活','Keep host memory powered'),t('核对容量与兼容性','Check capacity and support')]),
            (t('2c  持久化保存','2c  Durable saving'),[t('复制后完成持久化写入','Finish persistent write'),t('保存确认后方可关停','Confirm before shutdown'),t('恢复时间进入期限核查','Include restoration time')])])]
        p += [band(307,t('3  共同完整时序核查','3  Common temporal assessment'),[
            t('保护路径 → 剩余工作与必要重算 → 原期限内完成','Protection path → remaining work and any recomputation → original deadline'),
            t('网络：接入点净进口；小时CFE：全站消费与可归属电量','Network: net imports; hourly CFE: site consumption and clean attribution')])]
        p += [band(386,t('4  边界与适用范围','4  Boundaries and applicability'),[
            t('容量—通知—接纳量；报告基线一致与不同的区域','Capacity–notice–admission; retain both baseline agreement and disagreement'),
            t('可交付 / 不可交付 / 未决；冻结策略后独立留出','Deliverable / undeliverable / unresolved; hold out paths after policy selection')])]
        H=472
    elif key=='recovery':
        p += [cards(44,[(t('GPU显存','GPU memory'),[t('暂停计算，持续保活','Pause; retain powered state'),t('GPU和设施功率均计入','Include GPU and support'),t('恢复后继续有效进度','Resume preserved progress')]),
            (t('主机内存','Host memory'),[t('转存需要时间与功率','Transfer takes time/power'),t('GPU可释放，主机保活','Release GPU; retain host'),t('能力取决于软硬件支持','Compatibility is required')]),
            (t('持久化介质','Persistent storage'),[t('完整保存后允许关停','Save fully before shutdown'),t('暂存结束不等于落盘','Staging is not persistence'),t('计入保存及恢复开销','Count saving/restoration')])])]
        p += [text(18,144,t('主机暂存与持久化保存可串联，需分别核对供电与完成时点。','Host staging can precede persistence; check power and completion separately.'),8.6)]
        p += [band(154,t('允许路径中是否至少一条能够保护必要状态？','Can a permitted path protect the necessary state?'),[
            t('能够：暂停后的任务仍须按期完成；证据不足：保持未决','Yes: resumed work must still meet deadlines. Insufficient evidence: unresolved.'),
            t('不能：仅对失去保护的进度计重算，并重新检查期限','No: charge only lost progress as recomputation, then recheck deadlines.')])]
        p += [art('project_recovery_cartoon_v2.png',224,216)]
        p += [text(259.5,461,t('执行与补做需要设备、供电和清洁资源在原期限前共同可用。','Execution and recovery need equipment, supply and CFE before the deadline.'),9,True,'middle')]
        H=480
    elif key=='rampup':
        p += [art('project_rampup_cartoon_v2.png',45,235)]
        p += [cards(294,[(t('业务进度','Business progress'),[t('外生任务到达与原期限','Exogenous arrivals/deadlines'),t('负荷占用及剩余工作','Load and remaining work'),t('改变可接纳业务规模','Change admissible workload')]),
            (t('设备进度','Equipment progress'),[t('仅已投运设备提供能力','Only online assets count'),t('执行、保活和保存资源','Compute, retain and save'),t('新增设备也增加待机','New assets add idle load')]),
            (t('电网进度','Grid progress'),[t('实际建成网络与合同','Built grid and agreement'),t('供电与调用条件更新','Update supply/call conditions'),t('延期投运保留旧限制','Delay retains prior limits')])])]
        p += [band(398,t('跨阶段连续检查','Assess continuously across stages'),[
            t('任务状态、未完成工作与原期限持续传递；逐阶段重新求边界。','Carry task state, unfinished work and original deadlines; reassess boundaries.'),
            t('工程投运可能放宽约束；是否改变任务结局由评价确定。','Commissioning may relax limits; assessment determines the task outcome.')])]
        H=480
    else:
        p += [art('project_network_cartoon_v2.png',45,222)]
        p += [cards(280,[(t('设备与任务','Equipment and tasks'),[t('执行 / 暂停 / 保存 / 恢复','Run / pause / save / restore'),t('GPU、CPU、内存与网络','GPU, CPU, memory, network'),t('计入必要设施支撑','Include facility support')]),
            (t('功率与计量边界','Power and metering'),[t('全站消费与本地电源','Site load and local supply'),t('明确净进口功率平衡','Explicit net-import balance'),t('分钟取电汇总小时电量','Aggregate into hourly energy')]),
            (t('共同履约判据','Common criterion'),[t('网络与适用调用合同','Network and call agreement'),t('小时清洁属性归属','Hourly clean attribution'),t('状态与原任务期限','State and original deadline')])])]
        p += [band(386,t('保活功率须按完整路径核对','Check the full power requirement of each path'),[
            t('GPU低功率比例 ≠ 全站保活门槛；本地电源需核实可用性。','A GPU low-power fraction is not a site threshold; verify local supply.'),
            t('清洁属性与物理供电分别核算；同一负荷不重复计量。','Account for clean attributes and physical supply separately; avoid double counting.')])]
        H=472
    header=f'<svg xmlns="http://www.w3.org/2000/svg" width="183mm" height="{H*183/W:.5f}mm" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc"><title id="title">{escape(titles[key])}</title><desc id="desc">Nonquantitative proposed study design. Existing cartoon assets are unchanged. State loss is conditional, and credible-parameter existence remains unresolved.</desc><rect width="519" height="{H}" fill="white"/>'
    svg=header+text(8,22,titles[key],12,True)+'<g id="n:scheme-a-guide">'+''.join(p)+'</g></svg>\n'
    path=OUT/f'scheme_a_{key}_{lang}.svg';path.write_text(svg,encoding='utf-8')
    return dict(file=path.name,height_pt=H,svg_sha256=hashlib.sha256(svg.encode()).hexdigest())

def main():
    records=[figure(k,l) for l in ('cn','en') for k in ('framework','recovery','rampup','network')]
    scratch=Path(tempfile.mkdtemp(prefix='scheme-a-figures-'))
    for lang in ('cn','en'):
        selected=[r for r in records if r['file'].endswith(f'_{lang}.svg')]
        styles=[];sections=[]
        for i,r in enumerate(selected):
            styles.append(f'@page p{i} {{size:183mm {r["height_pt"]*183/W:.5f}mm;margin:0}} .p{i} {{page:p{i};break-after:page}}')
            sections.append(f'<section class="p{i}">'+(OUT/r['file']).read_text(encoding='utf-8')+'</section>')
        html=scratch/f'{lang}.html';pdf=scratch/f'{lang}.pdf'
        html.write_text('<!doctype html><meta charset="utf-8"><style>body,section{margin:0}svg{display:block}'+''.join(styles)+'</style>'+''.join(sections),encoding='utf-8')
        subprocess.run(['C:/Program Files/Google/Chrome/Application/chrome.exe','--headless=new','--disable-gpu','--no-pdf-header-footer','--user-data-dir='+str(scratch/lang),'--print-to-pdf='+str(pdf),html.as_uri()],capture_output=True,check=True,timeout=60)
        doc=pymupdf.open(pdf);assert len(doc)==4
        for i,r in enumerate(selected):
            page=doc[i];stem=OUT/Path(r['file']).stem
            single=pymupdf.open();single.insert_pdf(doc,from_page=i,to_page=i);single.save(stem.with_suffix('.pdf'))
            pix=page.get_pixmap(matrix=pymupdf.Matrix(300/72,300/72));pix.set_dpi(300,300);pix.save(stem.with_suffix('.png'))
            r.update(pdf_sha256=hashlib.sha256(stem.with_suffix('.pdf').read_bytes()).hexdigest(),png_sha256=hashlib.sha256(stem.with_suffix('.png').read_bytes()).hexdigest(),raster_artwork_images=len(page.get_images()),live_text_characters=len(page.get_text()))
    (OUT/'scheme_a_figures_manifest.json').write_text(json.dumps(dict(role='DRAFT_NONAUTHORITATIVE study-design figures',generator=Path(__file__).name,artwork='Unchanged existing project cartoon assets',figures=records),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(scratch)

if __name__=='__main__':
    main()
