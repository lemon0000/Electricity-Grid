"""Rebuild current reading PDFs from Markdown, using local KaTeX and Chrome."""
import argparse
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import hashlib
import markdown
import pymupdf
from PIL import Image
from render_staged_methods import CSS, KATEX_RENDER, PRINT_PDF

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--katex-dir', type=Path)
    parser.add_argument('--stems', nargs='+', choices=('project_introduction', 'project_introduction_en'),
                        default=('project_introduction', 'project_introduction_en'))
    args = parser.parse_args()
    scratch = Path(tempfile.mkdtemp(prefix='grid-draft-render-'))
    manifest_path = ROOT/'drafts/render_manifest.json'
    report = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    for stem in args.stems:
        work = scratch / stem
        work.mkdir()
        source = ROOT / 'drafts' / (stem + '.md')
        raw = source.read_bytes()
        blocks = []
        def capture(m):
            blocks.append(dict(tex=m[1] if m[1] is not None else m[2], display=m[1] is not None))
            return 'MATHPLACEHOLDER' + str(len(blocks)-1) + 'END'
        prepared = re.sub(r'\$\$(.*?)\$\$|\\\((.*?)\\\)', capture, raw.decode('utf-8'), flags=re.S)
        body = markdown.markdown(prepared, extensions=['tables', 'sane_lists'])
        if blocks:
            if args.katex_dir is None:
                raise ValueError('--katex-dir is required when a selected draft contains TeX')
            result = subprocess.run(['node', '--input-type=module', '-e', KATEX_RENDER, str(args.katex_dir / 'katex.mjs')], input=json.dumps(blocks).encode(), capture_output=True, check=True)
            for i, (block, markup) in enumerate(zip(blocks, json.loads(result.stdout)['rendered'])):
                token = 'MATHPLACEHOLDER' + str(i) + 'END'
                if block['display']:
                    body = body.replace('<p>'+token+'</p>', '<div class="display-math">'+markup+'</div>')
                body = body.replace(token, markup)
        body = re.sub(r'src="([^"]+)"', lambda m: 'src="'+(source.parent / m[1].replace('.svg', '.png')).resolve().as_uri()+'"', body)
        katex_css = '<link rel="stylesheet" href="'+(args.katex_dir / 'katex.min.css').as_uri()+'">' if args.katex_dir else ''
        doc = '<!doctype html><meta charset="utf-8">'+katex_css+'<style>'+CSS+'img{display:block;width:160mm;height:auto;max-height:190mm;object-fit:contain}p:has(img){break-inside:avoid;break-after:avoid}code{overflow-wrap:anywhere}td{overflow-wrap:anywhere}a{overflow-wrap:anywhere}</style><body>'+body+'</body>'
        inp, out = work/'draft.html', work/'draft.pdf'
        inp.write_text(doc, encoding='utf-8')
        js = PRINT_PDF.replace('20000', '60000').replace('printBackground:true,preferCSSPageSize:true', 'generateTaggedPDF:false,generateDocumentOutline:false,printBackground:true,preferCSSPageSize:true').replace("getComputedStyle(document.querySelector('.katex')).fontFamily", "(document.querySelector('.katex')?getComputedStyle(document.querySelector('.katex')).fontFamily:'')").replace('Staged deliverability | METHOD DRAFT | 2026-10-23', 'Research draft')
        subprocess.run(['C:/Program Files/Google/Chrome/Application/chrome.exe', '--headless=new', '--disable-gpu', '--no-pdf-header-footer', '--user-data-dir='+str(work/'chrome_cli'), '--print-to-pdf='+str(out), inp.as_uri()], capture_output=True, check=True, timeout=90)
        pdf = pymupdf.open(out)
        pages = []
        for i, page in enumerate(pdf):
            assert page.get_text().strip(), (stem, i)
            png = work / f'page_{i+1}.png'
            page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(png)
            pages.append(png)
        for start in range(0,len(pages),6):
            sheet = Image.new('RGB',(1200,1700),'#dddddd')
            for j,p in enumerate(pages[start:start+6]):
                im=Image.open(p); im.thumbnail((395,840)); sheet.paste(im,((j%3)*400,(j//3)*850))
            sheet.save(work/f'contact_{start//6}.png')
        assert source.read_bytes() == raw
        shutil.copy2(out, source.with_suffix('.pdf'))
        report[stem] = dict(source_sha256=hashlib.sha256(raw).hexdigest(),pdf_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),pages=len(pdf),math_blocks=len(blocks))
    (ROOT/'drafts/render_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(scratch)
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
