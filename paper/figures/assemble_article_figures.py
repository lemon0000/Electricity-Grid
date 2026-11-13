"""Paper-style bilingual illustrations using unchanged project cartoon artwork."""
from pathlib import Path
import json,hashlib,subprocess,tempfile
import pymupdf
from assemble_scheme_a_figures import art,text,OUT

def main():
    scratch=Path(tempfile.mkdtemp(prefix='article-figures-'))
    records=[]
    for lang in ('cn','en'):
        zh=lang=='cn';t=lambda a,b:a if zh else b
        for key in ('rampup','recovery'):
            H=285 if key=='rampup' else 305
            if key=='rampup':
                labels=[t('早期运行','Early operation'),t('业务、设备先于电网到位','Work and equipment precede the grid'),t('电网扩建投运','Reinforcement enters service')]
                notes=[t('业务逐步到达，设备分批投运','Work arrives; equipment enters service'),t('计算能力就绪，供电仍受限','Computing ready; supply constrained'),t('按新供电条件评价任务','Reassess tasks under the new supply')]
                body=art('project_rampup_cartoon_v2.png',35,203)
                footer=t('未完成工作与原期限跨阶段延续','Unfinished work and original deadlines carry across stages')
            else:
                labels=[t('GPU显存保活','Retain state on the GPU'),t('转存主机内存','Stage state in host memory'),t('完成持久化保存','Complete a durable checkpoint')]
                notes=[t('持续维持必要设备供电','Maintain required equipment power'),t('完成复制后仍需主机供电','Complete transfer; keep host powered'),t('确认写入后按条件关停','Confirm the write before shutdown')]
                body=art('project_recovery_cartoon_v2.png',86,194)
                footer=t('保存、恢复与必要重算均须纳入原期限','Saving, restoration and any recomputation remain subject to the original deadline')
            items=[]
            for i,(label,note) in enumerate(zip(labels,notes)):
                x=86.5+173*i
                items += [text(x,17,label,9,True,'middle'),text(x,32,note,7.7,False,'middle')]
            if key=='recovery':
                items += [text(259.5,54,t('状态保护方式可组合：主机暂存可以继续转为持久化保存','Protection can combine paths: host staging may precede persistence'),8,False,'middle')]
                items += ['<path d="M8,62 H511" stroke="#B5C8D1" stroke-width="0.6"/>',text(8,76,t('期限内恢复：设备、供电与清洁资源须同时可用','Recovery before the deadline: equipment, supply and clean energy'),8,True)]
            else:
                items += [text(259.5,249,t('业务增长、设备投运与电网建设分别确定阶段条件','Workload growth, equipment commissioning and grid construction define each stage'),8,False,'middle')]
            svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="183mm" height="{H*183/519}mm" viewBox="0 0 519 {H}"><title>{key}: staged interconnection and task preservation</title><rect width="519" height="{H}" fill="white"/><g id="n:labels">'+''.join(items)+'</g><g id="n:existing-cartoon">'+body+'</g>'+text(259.5,H-10,footer,8,True,'middle')+'</svg>'
            stem=OUT/f'article_{key}_{lang}';stem.with_suffix('.svg').write_text(svg,encoding='utf-8')
            html=scratch/f'{key}_{lang}.html';target=scratch/f'{key}_{lang}.pdf'
            html.write_text(f'<!doctype html><meta charset="utf-8"><style>@page{{size:183mm {H*183/519}mm;margin:0}}body{{margin:0}}svg{{display:block}}</style>'+svg,encoding='utf-8')
            subprocess.run(['C:/Program Files/Google/Chrome/Application/chrome.exe','--headless=new','--disable-gpu','--no-pdf-header-footer','--user-data-dir='+str(scratch/f'chrome_{key}_{lang}'),'--print-to-pdf='+str(target),html.as_uri()],capture_output=True,check=True,timeout=60)
            doc=pymupdf.open(target);assert len(doc)==1;doc.save(stem.with_suffix('.pdf'))
            pix=doc[0].get_pixmap(matrix=pymupdf.Matrix(300/72,300/72));pix.set_dpi(300,300);pix.save(stem.with_suffix('.png'))
            records.append(dict(stem=stem.name,svg_sha256=hashlib.sha256(svg.encode()).hexdigest(),pdf_sha256=hashlib.sha256(stem.with_suffix('.pdf').read_bytes()).hexdigest()))
    (OUT/'article_figures_manifest.json').write_text(json.dumps({'role':'conceptual paper illustrations; no experimental data','figures':records},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
