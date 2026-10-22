"""Assemble bilingual cartoon figures from four preserved PNG artworks.

Run with Python 3.12+. Text remains editable in SVG; the artwork is embedded.
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
    'rampup': {
        'title': ('业务和设备到位时，电网可能仍在施工',
                  'Work and equipment may be ready before the grid'),
        'labels': [(83, '早期运行', 'Early operation'),
                   (261, '业务与设备先到位', 'Work + equipment ready'),
                   (439, '电网扩建投运后', 'After grid completion')],
        'footer': ('同一中心的三个示意时点：只有已投运设施提供当期能力。',
                   'Three illustrative times at one center; only commissioned assets provide capability.'),
        'desc': 'The same data center at three illustrative times: early operation, a mismatch with grid construction, and completed reinforcement.',
    },
    'recovery': {
        'title': ('把任务延期，还要在截止前补做',
                  'Deferral still needs recovery before the deadline'),
        'labels': [(78, '当前延期', 'Defer now'),
                   (261, '之后的补做条件', 'Recovery conditions'),
                   (453, '两种可能结局', 'Alternative outcomes')],
        'footer': ('同一批橙色任务：上方按期完成；下方资源不足或逾期。',
                   'One orange cohort: on-time completion above; insufficient resources or overdue work below.'),
        'desc': 'Orange starred folders represent the same deferred cohort at successive times and in alternative possible outcomes.',
    },
    'network': {
        'title': ('电缆送电，证书记账：同一中心的两类核查',
                  'Power supply and clean-energy accounting at one center'),
        'labels': [(78, '已建电网与电表', 'Built grid + meter'),
                   (263, '同一个AI智算中心', 'One AI data center'),
                   (450, '小时CFE账本', 'Hourly CFE ledger')],
        'footer': ('下方依次检查：计算设备、实际取电、同小时清洁匹配。',
                   'Below: computing resources, metered power, and hourly clean matching are assessed.'),
        'desc': 'Physical power reaches a single data center through its meter; a paper ledger represents distinct hourly clean-energy attribution.',
    },
    'workflow': {
        'title': ('三种视角检查同一方案，再到新路径上验证',
                  'Assess the same plan, then test on independent paths'),
        'labels': [(59, '瞬时MW', 'MW snapshot'),
                   (161, '固定恢复余量', 'Fixed headroom'),
                   (263, '完整时序', 'Full timeline'),
                   (386, '冻结方案与策略', 'Freeze plan + policy'),
                   (466, '独立留出情景\n同一固定接入点', 'Independent holdout\nSame connection point')],
        'footer': ('共同输入、三种评价；冻结计划与运行策略后，再进行独立检验。',
                   'Common inputs, three assessments; freeze the plan and policy before independent testing.'),
        'desc': 'Three researchers inspect common inputs using a camera, fixed ruler and time filmstrip, then hand a locked plan to independent testing.',
    },
}


def text(x, y, value, size, bold=False, anchor='start'):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" '
            f'font-size="{size}" font-weight="{700 if bold else 400}" '
            f'text-anchor="{anchor}" fill="{INK}">{escape(value)}</text>')


def assemble(key, language):
    artwork = OUT / f'project_{key}_cartoon_v2.png'
    data = artwork.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', artwork
    width, height = struct.unpack('>II', data[16:24])
    image_height = WIDTH * height / width
    canvas_height = round(28 + image_height + 30, 3)
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
        f'<image x="0" y="28" width="{WIDTH}" height="{image_height:.3f}" '
        'preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,'
        + base64.b64encode(data).decode('ascii') + '"/>',
        '</g>',
        '<g id="n:figure-title">', text(18, 18, title, 11, True), '</g>',
        '<g id="n:localized-scene-labels">',
    ]
    for x, zh, en in spec['labels']:
        for line, label in enumerate((zh if language == 'cn' else en).split('\n')):
            elements.append(text(x, 48 + 12 * line, label, 7.6, True, 'middle'))
    elements.extend(['</g>', '<g id="n:reading-guide">',
                     text(WIDTH / 2, 28 + image_height + 18, spec['footer'][index], 7.6,
                          anchor='middle'), '</g>', '</svg>', ''])
    target = OUT / f'project_{key}_{language}.svg'
    target.write_text('\n'.join(elements), encoding='utf8', newline='\n')


if __name__ == '__main__':
    for figure in FIGURES:
        for lang in ('cn', 'en'):
            assemble(figure, lang)
    print('Assembled 8 bilingual cartoon figures from 4 preserved PNG artworks.')
