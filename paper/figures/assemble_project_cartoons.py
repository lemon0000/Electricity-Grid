"""Assemble the overview and three explanatory bilingual cartoon figures.

Run with Python 3.12+. Native labels and guides are editable in SVG; embedded
artwork retains its raster text.
This assembles figure labels and does not generate or alter the cartoon pixels.
"""

import base64
from html import escape
from pathlib import Path
import struct


OUT = Path(__file__).resolve().parent
WIDTH = 519
INK = '#23364A'
FONT = 'Arial, Microsoft YaHei, sans-serif'

FIGURES = {
    'framework': {
        'title': ('项目整体研究框架', 'Overall research framework'),
        'footer': ('给定进度与规则 → 三种评价 → 阶段判断 → 冻结后的独立留出',
                   'Given paths and rules → three assessments → stage judgments → frozen-policy holdout'),
        'desc': 'Three given progress paths and common rules feed parallel assessments. Cohort debt persists through recovery. Stage comparisons precede frozen-plan execution on independent paths.',
    },
    'rampup': {
        'title': ('业务和设备到位时，电网可能仍在施工',
                  'Work and equipment may be ready before the grid'),
        'labels': [(83, '早期运行', 'Early operation'),
                   (261, '业务与设备先到位', 'Work + equipment ready'),
                   (439, '电网扩建投运后', 'After grid completion')],
        'notes': [('任务到达与设备投运 → 当期可执行、可延期工作',
                   'Task arrivals + commissioned equipment → work available to execute or defer'),
                  ('当前建成电网 → 调用要求与恢复供电条件；投运后重新评价',
                   'Built grid → response calls + recovery supply; reassess after commissioning')],
        'desc': 'The same data center at three illustrative times: early operation, a mismatch with grid construction, and completed reinforcement.',
    },
    'recovery': {
        'title': ('把任务延期，还要在截止前补做',
                  'Deferral still needs recovery before the deadline'),
        'labels': [(78, '当前延期', 'Defer now'),
                   (261, '之后的补做条件', 'Recovery conditions'),
                   (453, '两种可能结局', 'Alternative outcomes')],
        'notes': [('设备余量 + 供电余量 + 同小时CFE → 期限内可补做空间',
                   'Spare equipment + power headroom + hourly CFE → recovery before the deadline'),
                  ('延期q → 批次债务 → 后续补做r → 原期限检查；右侧为可能结局',
                   'Deferral q → cohort debt → later recovery r → deadline check; outcomes branch')],
        'desc': 'Orange starred folders represent the same deferred cohort at successive times and in alternative possible outcomes.',
    },
    'network': {
        'title': ('电缆送电，证书记账：同一中心的两类核查',
                  'Power supply and clean-energy accounting at one center'),
        'labels': [(78, '已建电网与电表', 'Built grid + meter'),
                   (263, '同一个AI智算中心', 'One AI data center'),
                   (450, '小时CFE账本', 'Hourly CFE ledger')],
        'notes': [('设备与任务 → 实际取电P → 当前网络检查',
                   'Equipment + tasks → metered power P → checks on the built network'),
                  ('实际用电记录 + 同小时归属额度Y → 小时CFE核算',
                   'Consumption records + attributable limit Y for that hour → hourly CFE accounting')],
        'desc': 'Physical power reaches a single data center through its meter; a paper ledger represents distinct hourly clean-energy attribution.',
    },
}


def text(x, y, value, size, bold=False, anchor='start'):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" '
            f'font-size="{size}" font-weight="{700 if bold else 400}" '
            f'text-anchor="{anchor}" fill="{INK}">{escape(value)}</text>')


def framework_links(image_height, language):
    """Resource conditions enter recovery; total P covers site consumption."""
    x = lambda ratio: round(WIDTH * ratio, 3)
    y = lambda ratio: round(image_height * ratio, 3)
    parts = ['<g id="n:recovery-condition-links" fill="none" stroke="#53748B" '
             'stroke-width="0.8">',
             '<defs><marker id="condition-arrow" markerWidth="5" markerHeight="5" '
             'refX="4" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 Z" '
             'fill="#53748B" stroke="none"/></marker></defs>']
    for source in (0.817, 0.880, 0.946):
        parts.append(f'<path d="M{x(source)},{y(0.355)} V{y(0.348)}"/>')
    parts.append(f'<path d="M{x(0.946)},{y(0.348)} H{x(0.704)} V{y(0.429)}" '
                 'marker-end="url(#condition-arrow)"/>')
    parts.append('</g>')
    parts.append(f'<rect x="{x(0.650)}" y="{y(0.458)}" width="{x(0.037)}" '
                 f'height="{y(0.034)}" fill="white"/>')
    parts.append(f'<rect x="{x(0.652)}" y="{y(0.433)}" width="{x(0.090)}" '
                 f'height="{y(0.031)}" fill="white"/>')
    parts.append(text(x(0.704), y(0.455), '后续补做r' if language == 'cn' else 'Recovery r',
                      7.6, True, 'middle'))
    parts.append(f'<path d="M{x(0.844)},{y(0.255)} V{y(0.264)}" '
                 'stroke="#164969" stroke-width="1.7"/>')
    parts.append(f'<path d="M{x(0.839)},{y(0.263)} L{x(0.849)},{y(0.263)} '
                 f'L{x(0.844)},{y(0.271)} Z" fill="#164969"/>')
    parts.append(f'<rect x="{x(0.794)}" y="{y(0.596)}" width="{x(0.070)}" '
                 f'height="{y(0.043)}" fill="white"/>')
    parts.append(text(x(0.829), y(0.623), '总取电P' if language == 'cn' else 'Total P',
                      7.6, True, 'middle'))
    parts.append(text(x(0.850 if language == 'cn' else 0.870), y(0.657),
                      '含执行、补做、待机与配套' if language == 'cn'
                      else 'Execution, recovery, idle, support', 7.6, anchor='middle'))
    return parts


def assemble(key, language):
    artwork = OUT / (f'project_framework_cartoon_v3_{language}.png' if key == 'framework'
                     else f'project_{key}_cartoon_v2.png')
    data = artwork.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', artwork
    width, height = struct.unpack('>II', data[16:24])
    image_height = WIDTH * height / width
    image_y = 0 if key == 'framework' else 28
    canvas_height = round(image_y + image_height + (24 if key == 'framework' else 44), 3)
    index = 0 if language == 'cn' else 1
    spec = FIGURES[key]
    title = spec['title'][index]
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="183mm" '
        f'height="{canvas_height * 183 / WIDTH:.3f}mm" '
        f'viewBox="0 0 {WIDTH} {canvas_height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="desc">{escape(spec["desc"])}</desc>',
        f'<rect x="0" y="0" width="{WIDTH}" height="{canvas_height}" fill="white"/>',
        '<g id="n:cartoon-artwork">',
        f'<image x="0" y="{image_y}" width="{WIDTH}" height="{image_height:.3f}" '
        'preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,'
        + base64.b64encode(data).decode('ascii') + '"/>',
        '</g>',
    ]
    if key == 'framework':
        elements.extend(framework_links(image_height, language))
    if key != 'framework':
        elements.extend(['<g id="n:figure-title">', text(18, 18, title, 11, True), '</g>'])
    elements.append('<g id="n:localized-scene-labels">')
    for x, zh, en in spec.get('labels', []):
        for line, label in enumerate((zh if language == 'cn' else en).split('\n')):
            elements.append(text(x, 48 + 12 * line, label, 7.6, True, 'middle'))
    elements.extend(['</g>', '<g id="n:reading-guide">'])
    notes = spec.get('notes', [spec.get('footer')])
    for row, note in enumerate(notes):
        elements.append(text(WIDTH / 2, image_y + image_height + 16 + 13 * row,
                             note[index], 7.6, anchor='middle'))
    elements.extend(['</g>', '</svg>', ''])
    target = OUT / f'project_{key}_{language}.svg'
    target.write_text('\n'.join(elements), encoding='utf8', newline='\n')


if __name__ == '__main__':
    for figure in FIGURES:
        for lang in ('cn', 'en'):
            assemble(figure, lang)
    print('Assembled the bilingual overview and three explanatory cartoons.')
