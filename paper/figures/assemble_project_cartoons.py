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

# Labels are paired Chinese/English. Leader endpoints use the artwork's
# coordinates after scaling to WIDTH, measured from its top-left corner.
DETAILS = {
    'rampup': {
        'question': ('三条进度不同步时，哪些运行条件会改变？',
                     'When progress paths diverge, which operating conditions change?'),
        'stages': [
            ('早期运行', 'Early operation', '业务较少，设备逐批到位', 'Work grows; equipment is phased in'),
            ('业务设备先到，电网仍施工', 'Work ready; reinforcement pending',
             '只有已投运资源提供当期能力', 'Only commissioned assets are available'),
            ('电网扩建实际投运', 'Reinforcement commissioned',
             '按新建成网络重新评价', 'Reassess on the newly built network'),
        ],
        'tags': [
            (42, 179, ('当期任务w',), ('Current work w',), (27, 149)),
            (98, 48, ('已投运K',), ('Commissioned K',), (75, 126)),
            (322, 14, ('扩建施工中',), ('Still being built',), (314, 111)),
            (271, 179, ('可能延期q',), ('Possible deferral q',), (265, 135)),
            (478, 14, ('扩建已投运',), ('New grid asset', 'commissioned'), (484, 117)),
        ],
        'bridge': ('同一中心沿连续时间推进 → 已有债务与预算跨阶段保留',
                   'One center through time → existing debt and budgets carry across stages'),
        'cards': [
            (('① 业务与设备', '1  Tasks and equipment'), [
                ('w：本小时的外生任务', 'w: external work in this hour'),
                ('K：已投运的计算能力', 'K: commissioned computing capacity'),
                ('任务少：可延期工作可能少', 'Little work may limit deferral'),
                ('设备有余量：才可能接纳补做', 'Spare equipment may allow recovery'),
            ]),
            (('② 扩建尚未投运', '2  Reinforcement pending'), [
                ('业务已到，计算设备可用', 'Work and computing may be ready'),
                ('供电仍按现有建成电网检查', 'Supply uses the currently built grid'),
                ('由当前网络重算调用要求', 'Recalculate required response calls'),
                ('补做还要有供电与清洁余量', 'Recovery also needs power and CFE'),
            ]),
            (('③ 投运后重新评价', '3  Reassess after commissioning'), [
                ('新网络改变调用与补做供电条件', 'New grid conditions change calls'),
                ('已欠任务与预算继续传递', 'Debt and budgets still carry forward'),
                ('重新检查响应、补做与期限', 'Recheck response, recovery, deadlines'),
                ('阶段履约结论由完整检查确定', 'Delivery follows the complete checks'),
            ]),
        ],
        'takeaway': ('进度错位 → 当期响应与后续补做条件变化 → 阶段判断可能变化',
                     'Progress mismatch → different response and recovery conditions → possible changes in stage judgments'),
    },
    'recovery': {
        'question': ('任务现在少做了，怎样判断以后能否按期补完？',
                     'If work is deferred now, can the same cohort finish by its deadline?'),
        'stages': [
            ('① 当期延期q', '1  Defer q now', '少做的任务记为批次债务', 'Deferred work becomes cohort debt'),
            ('② 以后小时补做r', '2  Recover r later', '设备、供电、CFE同时可用', 'Equipment, power and CFE must align'),
            ('③ 检查原始期限', '3  Check the original deadline', '按期完成，或保留逾期与未决', 'Record completion, overdue or unresolved'),
        ],
        'tags': [
            (204, 0, ('设备余量',), ('Spare', 'equipment'), (206, 42)),
            (257, 0, ('供电余量',), ('Power', 'headroom'), (254, 68)),
            (321, 0, ('同小时CFE',), ('Hourly', 'CFE quota'), (320, 63)),
            (119, 191, ('延期q：仍待完成',), ('Deferred q: still owed',), (135, 148)),
            (187, 115, ('以后小时',), ('Later hours',), (188, 139)),
            (255, 100, ('三项同时可用',), ('All three available',), (256, 115)),
            (302, 168, ('补做r：减少债务',), ('Recovery r reduces debt',), (293, 141)),
            (449, 19, ('原期限前完成',), ('Completed by deadline',), (448, 102)),
        ],
        'outcome_tags': [
            (289, ('原任务截止时间',), ('Original task deadline',), (312, 184)),
            (439, ('到期未完成 → 逾期',), ('Still owed at deadline → overdue',), (437, 187)),
        ],
        'cards': [
            (('① 延期并保留债务', '1  Defer and retain debt'), [
                ('蓝文件：当期处理的任务', 'Blue folders: current execution'),
                ('橙文件：同一批被延期的任务', 'Orange folders: one deferred cohort'),
                ('少做的任务仍须在原期限前完成', 'The original deadline still applies'),
                ('债务进入以后小时，不能清零', 'Debt carries forward into later hours'),
            ]),
            (('② 在以后小时补做', '2  Recover in later hours'), [
                ('已投运设备有空余', 'Commissioned equipment is spare'),
                ('当前网络允许补做用电', 'The built grid permits recovery load'),
                ('同一小时CFE额度足够', 'CFE is available in that same hour'),
                ('同时满足动作预算、效率与期限', 'Also respect budget, efficiency, deadline'),
            ]),
            (('③ 判断任务结局', '3  Record the cohort outcome'), [
                ('上：原期限前完成 → 按期', 'Above: finished by deadline → on time'),
                ('下：到期仍欠任务 → 记录逾期', 'Below: debt at deadline → overdue'),
                ('之后补做仍保留已发生的逾期', 'Later recovery retains the violation'),
                ('没有观察到结局 → 保留未决', 'Outcome not observed → unresolved'),
            ]),
        ],
        'takeaway': ('当期能延期，只说明现在能少做；可交付还要检查期限内能否补完。',
                     'Deferral provides response now; deliverability also requires recovery by the original deadline.'),
    },
    'network': {
        'question': ('任务怎样形成实际用电，又怎样接受网络与小时CFE核查？',
                     'How do tasks become metered power, then enter network and hourly CFE checks?'),
        'stages': [
            ('供电来自当前建成电网', 'Supply from the built grid', '粗蓝线：实际供电线路', 'Thick blue cable: physical supply'),
            ('同一中心形成实际取电P', 'One center, total power P', '计算、待机和配套均计入', 'Execution, recovery, idle and support'),
            ('CFE按同小时归属核算', 'CFE attribution for that hour', '细虚线：记录与属性的核对', 'Dotted links: records and attribution'),
        ],
        'tags': [
            (62, 13, ('当前建成网络',), ('Built network',), (64, 91)),
            (160, 13, ('固定接入点', '电表P'), ('Fixed POI', 'meter P'), (164, 100)),
            (256, 13, ('执行与补做',), ('Execution', 'and recovery'), (270, 109)),
            (335, 13, ('配套耗能',), ('Support', 'energy'), (337, 56)),
            (455, 13, ('外部同小时', '归属额度Y'), ('External hourly', 'CFE limit Y'), (454, 119)),
            (394, 53, ('用电记录与', '归属电量核对'), ('Match use records', 'with attributed energy'), (393, 84)),
        ],
        'bridge': ('电表记录 + 外部同小时额度Y → 核对目标份额α所需的清洁电量',
                   'Meter records + external hourly limit Y → check CFE needed for target share α'),
        'cards': [
            (('① 先检查计算资源', '1  Check computing resources'), [
                ('执行与补做不超过已投运K', 'Execution and recovery fit within K'),
                ('延期与补做共享：q+r≤D', 'Deferral and recovery share q+r≤D'),
                ('债务与原任务期限继续检查', 'Track debt and original deadlines'),
                ('待机与配套也产生用电', 'Idle and support also consume power'),
            ]),
            (('② 汇总电表取电P', '2  Account for total power P'), [
                ('计算量按设备映射换算为电力MW', 'Map computing effort to electrical MW'),
                ('P含执行、补做、待机与配套', 'P includes execution and recovery'),
                ('同一计量边界包括全部设备', 'Plus idle and support at the same meter'),
                ('小时用电量为PΔt', 'Energy in the interval is PΔt'),
            ]),
            (('③ 同一P接受两类核查', '3  Check network and CFE'), [
                ('运行：当前网络下检查实际P', 'Operation: check P on the built grid'),
                ('接入额度：正常状态检查F+X', 'Access: normal state checks full F+X'),
                ('故障：检查F及合同允许的X调用', 'Contingencies: F and permitted X calls'),
                ('同小时清洁：αPΔt≤y≤Y', 'Hourly matching: αPΔt≤y≤Y'),
                ('Y为外部同小时可归属电量', 'Y: externally attributable hourly energy'),
            ]),
        ],
        'takeaway': ('同一中心同时接受计算资源、网络供电与小时清洁匹配检查。',
                     'One center must satisfy computing-resource, network-supply and hourly clean-matching checks.'),
    },
}

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


def annotation_tag(cx, baseline, lines, target, image_y):
    """Point a neutral leader at one pictured object; it is not a flow arrow."""
    size = 8.2
    width = 12 + max(sum(1 if ord(c) > 255 else 0.53 for c in line)
                     for line in lines) * size
    top = image_y + baseline - 10
    height = 8 + 10 * len(lines)
    tx, ty = target[0], image_y + target[1]
    edge = top + height if ty > top + height else top
    parts = [f'<path d="M{cx},{edge:.3f} L{tx},{ty:.3f}" fill="none" '
             'stroke="#53748B" stroke-width="0.65"/>',
             f'<circle cx="{tx}" cy="{ty:.3f}" r="1.15" fill="#53748B"/>',
             f'<rect x="{cx-width/2:.3f}" y="{top:.3f}" width="{width:.3f}" '
             f'height="{height}" rx="2" fill="white" stroke="#B4C7D3" stroke-width="0.4"/>']
    for row, value in enumerate(lines):
        parts.append(text(cx, image_y + baseline + 10 * row, value, size, True, 'middle'))
    return parts


def assemble_detail(key, language, data, width, height):
    index = 0 if language == 'cn' else 1
    spec, guide = FIGURES[key], DETAILS[key]
    image_y = 111
    image_height = WIDTH * height / width
    bottom = image_y + image_height
    card_y = bottom + 39
    card_height = 98 if key == 'network' else 85
    takeaway_y = card_y + card_height + 15
    canvas_height = round(takeaway_y + 39, 3)
    title = spec['title'][index]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="183mm" '
        f'height="{canvas_height * 183 / WIDTH:.3f}mm" viewBox="0 0 {WIDTH} {canvas_height}" '
        'role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="desc">{escape(spec["desc"])}</desc>',
        f'<rect width="{WIDTH}" height="{canvas_height}" fill="white"/>',
        '<defs><marker id="step-arrow" markerWidth="4" markerHeight="4" refX="3.5" '
        'refY="2" orient="auto"><path d="M0,0 L4,2 L0,4 Z" fill="#53748B"/></marker></defs>',
        '<g id="n:figure-title">', text(8, 18, title, 11, True),
        text(8, 34, guide['question'][index], 8.8), '</g>',
        '<g id="n:scene-reading-order">',
    ]
    colors = ('#EAF4FA', '#FFF2DC', '#E8F4F0')
    for col, stage in enumerate(guide['stages']):
        x = 8 + 171 * col
        head, subtitle = stage[index], stage[2 + index]
        if language == 'en':
            head = head.replace('Work ready; reinforcement pending', 'Work ready;\nreinforcement pending')
            head = head.replace('3  Check the original deadline', '3  Check the\noriginal deadline')
        parts.append(f'<rect x="{x}" y="45" width="161" height="47" rx="4" '
                     f'fill="{colors[col]}" stroke="#C6D5DE" stroke-width="0.6"/>')
        for line, value in enumerate(head.split('\n')):
            parts.append(text(x + 80.5, 61 + line * 10, value, 9, True, 'middle'))
        parts.append(text(x + 80.5, 83, subtitle, 8.2, anchor='middle'))
        if col < 2:
            parts.append(f'<path d="M{x+162},67 H{x+170}" stroke="#53748B" '
                         'stroke-width="0.8" marker-end="url(#step-arrow)"/>')
    parts.extend(['</g>', '<g id="n:cartoon-artwork">',
                  f'<image x="0" y="{image_y}" width="{WIDTH}" height="{image_height:.3f}" '
                  'preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,'
                  + base64.b64encode(data).decode('ascii') + '"/>', '</g>',
                  '<g id="n:object-and-arrow-annotations">'])
    for cx, baseline, zh, en, target in guide['tags']:
        parts.extend(annotation_tag(cx, baseline, zh if index == 0 else en, target, image_y))
    if 'outcome_tags' in guide:
        for cx, zh, en, target in guide['outcome_tags']:
            parts.extend(annotation_tag(cx, image_height + 15, zh if index == 0 else en,
                                        target, image_y))
    else:
        parts.append(text(WIDTH / 2, bottom + 18, guide['bridge'][index], 8.3, True, 'middle'))
    parts.extend(['</g>', '<g id="n:explanatory-steps">'])
    for col, (heading, body) in enumerate(guide['cards']):
        x = 8 + 171 * col
        parts.append(f'<rect x="{x}" y="{card_y:.3f}" width="161" height="{card_height}" '
                     f'rx="4" fill="{colors[col]}" stroke="#B4C7D3" stroke-width="0.6"/>')
        parts.append(text(x + 8, card_y + 18, heading[index], 8.8, True))
        for line, values in enumerate(body):
            parts.append(text(x + 8, card_y + 36 + 12 * line, values[index], 8.2))
        if col < 2:
            parts.append(f'<path d="M{x+162},{card_y+45:.3f} H{x+170}" stroke="#53748B" '
                         'stroke-width="0.8" marker-end="url(#step-arrow)"/>')
    parts.extend(['</g>', '<g id="n:figure-message">',
                  f'<rect x="8" y="{takeaway_y:.3f}" width="503" height="27" rx="4" fill="#F2F6F8"/>'])
    message = guide['takeaway'][index]
    if language == 'en' and key == 'rampup':
        message = message.replace(' → possible', '\n→ possible')
    for line, value in enumerate(message.split('\n')):
        parts.append(text(WIDTH / 2, takeaway_y + 12 + 11 * line, value, 8.5, True, 'middle'))
    parts.extend(['</g>', '</svg>', ''])
    (OUT / f'project_{key}_{language}.svg').write_text('\n'.join(parts), encoding='utf8', newline='\n')


def assemble(key, language):
    artwork = OUT / (f'project_framework_cartoon_v3_{language}.png' if key == 'framework'
                     else f'project_{key}_cartoon_v2.png')
    data = artwork.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', artwork
    width, height = struct.unpack('>II', data[16:24])
    if key != 'framework':
        assemble_detail(key, language, data, width, height)
        return
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
