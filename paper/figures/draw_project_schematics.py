"""Build the bilingual introduction's editable conceptual SVGs (no result data).

Run with Python 3.12+. Each drawing unit is one point at a width of 183 mm.
Source: project introduction sections 1, 3, 5 and 6, and the minimum stage spec.
"""

from html import escape
from pathlib import Path


OUT = Path(__file__).resolve().parent
INK = "#23364A"
BLUE = "#496F91"
TEAL = "#287F80"
AMBER = "#BD8238"
RED = "#AA554C"
LINE = "#CAD4DC"
PALE = "#F2F5F7"
ICE = "#EDF3F8"
MINT = "#EAF4F1"
SAND = "#FBF2E6"
FONT = "Arial, Microsoft YaHei, sans-serif"


class SVG:
    def __init__(self, height, title, desc):
        self.height = height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="183mm" '
            f'height="{height * 183 / 519:.3f}mm" viewBox="0 0 519 {height}" '
            'role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(desc)}</desc>',
            '<defs><marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" '
            'markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
            f'<path d="M0 0 L8 4 L0 8 Z" fill="{INK}"/></marker></defs>',
            f'<rect x="0" y="0" width="519" height="{height}" fill="white"/>',
        ]

    def group(self, name):
        self.parts.append(f'<g id="{name}">')

    def end(self):
        self.parts.append('</g>')

    def rect(self, x, y, w, h, fill="white", stroke=LINE, radius=4, dash=None):
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="0.8"{dash_attr}/>'
        )

    def text(self, x, y, value, size=8, bold=False, anchor="start"):
        lines = value.split('\n')
        for i, line in enumerate(lines):
            self.parts.append(
                f'<text x="{x}" y="{y + i * (size + 4)}" font-family="{FONT}" '
                f'font-size="{size}" font-weight="{700 if bold else 400}" '
                f'text-anchor="{anchor}" fill="{INK}">{escape(line)}</text>'
            )

    def line(self, x1, y1, x2, y2, color=LINE, width=0.8, arrow=False, dash=None):
        extra = ' marker-end="url(#arrow)"' if arrow else ''
        extra += f' stroke-dasharray="{dash}"' if dash else ''
        self.parts.append(
            f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{color}" '
            f'stroke-width="{width}"{extra}/>'
        )

    def path(self, points, color=INK, width=1, arrow=False):
        extra = ' marker-end="url(#arrow)"' if arrow else ''
        self.parts.append(
            f'<path d="{points}" fill="none" stroke="{color}" '
            f'stroke-width="{width}"{extra}/>'
        )

    def circle(self, x, y, r, fill="white", stroke=BLUE):
        self.parts.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1"/>'
        )

    def header(self, title, subtitle):
        self.text(18, 22, title, 11, True)
        self.text(18, 38, subtitle, 7.6)

    def save(self, filename):
        (OUT / filename).write_text('\n'.join(self.parts + ['</svg>', '']), encoding='utf-8', newline='\n')


def pick(cn, zh, en):
    return zh if cn else en


def rack(s, x, y, active=True):
    s.rect(x, y, 15, 26, MINT if active else PALE, TEAL if active else LINE, 1.2)
    for dy in (5, 11, 17):
        s.line(x + 3, y + dy, x + 12, y + dy, TEAL if active else LINE, 1.3)


def tickets(s, x, y, dense=False):
    for dx, dy in ((0, 4), (12, 0), (24, 4)) if dense else ((10, 2),):
        s.rect(x + dx, y + dy, 17, 21, ICE, BLUE, 1.5)
        s.line(x + dx + 4, y + dy + 7, x + dx + 13, y + dy + 7, BLUE)
        s.line(x + dx + 4, y + dy + 12, x + dx + 13, y + dy + 12, BLUE)


def rampup(cn):
    s = SVG(294, '进度错位与分阶段接入' if cn else 'Misaligned progress and staged access',
            'Conceptual example on one shared time axis; icon counts do not encode measured quantities.')
    s.header(pick(cn, '三条进度路径，共同决定每个阶段的履约条件',
                        'Three progress paths shape delivery at each stage'),
             pick(cn, '同一个AI智算中心 · 共同时间轴 · 阶段由实际状态变化界定',
                        'One AI data center · shared chronology · boundaries follow state changes'))
    s.group('c:misalignment-window')
    s.rect(263, 52, 117, 192, SAND, '#E9D3B4', 5)
    s.text(321.5, 67, pick(cn, '进度错位窗口', 'Misalignment window'), 8.5, True, 'middle')
    s.end()
    s.line(125, 82, 502, 82, INK, 0.8, True)
    for x, zh, en in ((183, '早期', 'Early operation'),
                       (321.5, '业务与设备先到位', 'Work + equipment ready'),
                       (450, '电网扩建投运后', 'After grid completion')):
        s.text(x, 97, pick(cn, zh, en), 7.6, anchor='middle')
    labels = [
        ('业务', 'Business', '到达的任务', 'Arriving tasks'),
        ('计算设备', 'Equipment', '已投运能力 K', 'Commissioned K'),
        ('电网', 'Grid', '实际建成状态', 'Built network'),
    ]
    for i, (zh, en, sub_zh, sub_en) in enumerate(labels):
        y = 128 + i * 47
        s.text(18, y, pick(cn, zh, en), 9, True)
        s.text(18, y + 14, pick(cn, sub_zh, sub_en), 7.6)
        s.line(120, y + 20, 502, y + 20)
    s.group('n:business-path')
    for x, dense, zh, en in ((148, False, '任务较少', 'Fewer tasks'),
                              (286, True, '业务增长', 'More tasks'),
                              (407, True, '业务持续', 'Ongoing work')):
        tickets(s, x, 108, dense)
        s.text(x + 50, 124, pick(cn, zh, en), 7.6)
    s.end()
    s.group('n:equipment-path')
    for x, extra, zh, en in ((146, False, '首批投运', 'First batch'),
                              (284, True, '后续投运', 'Added batch'),
                              (417, True, '已投运可用', 'Available')):
        rack(s, x, 153)
        if extra:
            rack(s, x + 19, 153)
        s.text(x + 42, 168, pick(cn, zh, en), 7.6)
    s.end()
    s.group('n:grid-path')
    for x, fill, zh, en in ((139, ICE, '既有电网', 'Existing grid'),
                             (277, SAND, '既有电网', 'Existing grid'),
                             (410, MINT, '扩建已可用', 'Reinforced grid')):
        s.rect(x, 204, 83, 23, fill, LINE, 2)
        s.text(x + 41.5, 219, pick(cn, zh, en), 7.6, anchor='middle')
    s.text(321.5, 239, pick(cn, '扩建仍在施工', 'Reinforcement pending'), 7.6, anchor='middle')
    s.end()
    s.rect(18, 254, 483, 26, ICE, ICE, 4)
    s.text(259.5, 271, pick(cn, '研究问题：错位窗口内，给定接入计划能否持续履约？',
                                'Question: can the given access plan deliver through the mismatch?'),
           8.6, True, 'middle')
    s.save('project_rampup_' + ('cn' if cn else 'en') + '.svg')


def recovery(cn):
    s = SVG(272, '延期与期限内恢复' if cn else 'Deferral and recovery before deadlines',
            'The same task cohort moves from deferral to recovery; completion and shortfall are alternative outcomes.')
    s.header(pick(cn, '当前能够削减，仍需检查任务能否按期补做',
                        'A reduction now still needs recovery before the deadline'),
             pick(cn, '同一批延期任务 · 恢复资源必须在原始截止时间前足够可用',
                        'One deferred cohort · sufficient recovery resources before its original deadline'))
    s.group('n:deferred-cohort')
    s.rect(18, 62, 112, 128, SAND, '#E9D3B4')
    s.text(74, 80, pick(cn, '当前：延期 q', 'Now: defer q'), 8.5, True, 'middle')
    s.rect(51, 94, 46, 35, '#F5DAB4', AMBER, 2)
    s.line(59, 105, 88, 105, AMBER, 1.5)
    s.line(59, 114, 83, 114, AMBER, 1.5)
    s.text(74, 147, pick(cn, '形成未完成工作', 'Unfinished work'), 8, anchor='middle')
    s.text(74, 163, pick(cn, '按任务批次保留', 'Tracked by cohort'), 7.6, anchor='middle')
    s.end()
    s.line(133, 124, 156, 124, INK, 1.3, True)
    s.group('c:recovery-conditions')
    s.rect(160, 62, 204, 128, ICE, LINE)
    s.text(262, 80, pick(cn, '之后：寻找可行补做 r', 'Later: find feasible recovery r'), 8.5, True, 'middle')
    for y, zh, en in ((100, '已投运设备的空闲能力', 'Spare commissioned equipment'),
                       (121, '补做时段的网络供电余量', 'Power headroom in recovery hours'),
                       (142, '同小时可归属的CFE电量', 'Attributable CFE in those hours')):
        s.circle(175, y - 3, 3, MINT, TEAL)
        s.text(186, y, pick(cn, zh, en), 8)
    s.line(172, 153, 352, 153)
    s.text(262, 168, pick(cn, '同时满足动作预算、恢复效率与期限',
                             'Also: action budget, efficiency, deadlines'), 7.6, anchor='middle')
    s.end()
    s.group('e:alternative-outcomes')
    s.path('M367 124 L383 124 L383 92 L402 92', arrow=True)
    s.path('M383 124 L383 162 L402 162', arrow=True)
    s.circle(383, 124, 1.5, INK, INK)
    s.rect(406, 62, 95, 60, MINT, '#ADD2CA')
    s.text(453.5, 80, pick(cn, '资源与期限满足', 'Conditions met'), 7.6, anchor='middle')
    s.text(453.5, 99, pick(cn, '按期完成', 'On-time completion'), 8.5, True, 'middle')
    s.rect(406, 132, 95, 58, '#FBEEEA', '#DEBDB8')
    s.text(453.5, 150, pick(cn, '不足或来得太晚', 'Insufficient / late'), 7.6, anchor='middle')
    s.text(453.5, 169, pick(cn, '缺口或逾期', 'Shortfall / overdue'), 8.5, True, 'middle')
    s.end()
    s.group('n:continuous-ledger')
    s.line(29, 218, 492, 218, INK, 1, True)
    for x, zh, en in ((75, '延期发生', 'Deferral'), (262, '债务随时间延续并按补做核减', 'Debt carries and is reduced by recovery'),
                       (454, '原始截止时间', 'Original deadline')):
        s.line(x, 212, x, 224, INK)
        s.text(x, 238, pick(cn, zh, en), 7.6, anchor='middle')
    s.text(259.5, 259, pick(cn, '补做来得太晚，不能消除已经发生的逾期。',
                                'Late recovery retains the recorded deadline violation.'), 8, anchor='middle')
    s.end()
    s.save('project_recovery_' + ('cn' if cn else 'en') + '.svg')


def network(cn):
    s = SVG(306, '同一接入点的联合评价框架' if cn else 'Joint assessment at one connection point',
            'Metered electricity and clean-energy attribution are distinct flows. Computing capacity, grid conditions, and hourly CFE are checked together.')
    s.header(pick(cn, '同一智算中心，同时检查计算、网络与小时CFE',
                        'One center: computing, grid and hourly CFE checks'),
             pick(cn, '给定建设与接入计划 · 按实际已投运状态逐小时评价',
                        'Given construction and access plans · hourly checks on commissioned assets'))
    s.group('n:built-network')
    s.rect(18, 61, 126, 134, PALE, LINE)
    s.text(81, 79, pick(cn, '实际建成电网', 'Built network'), 9, True, 'middle')
    for x, y in ((43, 110), (116, 110), (79, 135)):
        s.circle(x, y, 5, 'white', BLUE)
    s.line(48, 110, 111, 110, BLUE, 1.1)
    s.line(47, 113, 75, 132, BLUE, 1.1)
    s.line(111, 113, 83, 132, BLUE, 1.1)
    s.text(81, 157, pick(cn, '正常状态：完整 F+X', 'Normal state: full F+X'), 7.6, anchor='middle')
    s.text(81, 172, pick(cn, '声明故障：F 与 X 调用', 'Declared faults: F + X calls'), 7.6, anchor='middle')
    s.end()
    s.group('e:metered-power')
    s.line(147, 120, 165, 120, INK, 1.5)
    s.line(187, 120, 204, 120, INK, 1.5, True)
    s.circle(176, 120, 10, 'white', BLUE)
    s.text(176, 123, 'P', 8.5, True, 'middle')
    s.text(176, 97, pick(cn, '实际取电', 'Metered power'), 7.6, anchor='middle')
    s.text(176, 145, pick(cn, '固定接入点', 'Fixed connection'), 7.6, anchor='middle')
    s.end()
    s.group('n:data-center')
    s.rect(210, 61, 152, 134, ICE, '#AFC5D6')
    s.text(286, 79, pick(cn, 'AI智算中心', 'AI data center'), 9, True, 'middle')
    rack(s, 223, 92)
    rack(s, 243, 92)
    s.text(270, 102, pick(cn, '已投运设备 K', 'Commissioned K'), 8)
    s.text(270, 117, pick(cn, '外生任务 w', 'External tasks w'), 8)
    s.line(222, 130, 350, 130)
    s.text(286, 146, pick(cn, '当前延期 q · 后续补做 r', 'Defer q now · recover r later'), 7.6, anchor='middle')
    s.text(286, 163, pick(cn, '设备映射至实际取电 P', 'Equipment mapping to power P'), 7.6, anchor='middle')
    s.text(286, 179, pick(cn, '待机、执行、补做与配套用电', 'Idle, execution, recovery, support'), 7.6, anchor='middle')
    s.end()
    s.group('n:cfe-attribution')
    s.rect(399, 61, 102, 134, 'white', LINE)
    s.text(450, 79, pick(cn, '小时CFE归属', 'Hourly CFE'), 8.5, True, 'middle')
    s.rect(429, 92, 38, 32, MINT, TEAL, 2)
    s.text(448, 112, 'Y', 11, True, 'middle')
    s.text(450, 143, pick(cn, '同小时 · 适用区域', 'Same hour + region'), 7.6, anchor='middle')
    s.text(450, 159, pick(cn, '可分配的电量上限', 'Attributable limit'), 7.6, anchor='middle')
    s.text(450, 175, pick(cn, '归属核算', 'Attribute accounting'), 7.6, anchor='middle')
    s.line(396, 111, 366, 111, INK, 1, True)
    s.text(381, 96, 'y', 8, anchor='middle')
    s.end()
    s.group('c:hourly-checks')
    s.line(286, 198, 286, 215, INK, 1.2, True)
    s.rect(18, 220, 483, 69, MINT, '#B7D4CC')
    s.text(259.5, 237, pick(cn, '每小时共同满足，任务债务与预算跨小时延续',
                                'Joint hourly checks; debt and budgets carry between hours'), 8.5, True, 'middle')
    for x in (178, 340):
        s.line(x, 247, x, 280, '#BAD1CA')
    for x, title, detail in (
        (98, pick(cn, '计算与共享调节', 'Computing + adjustment'), '0 ≤ w − q + r ≤ K;  q + r ≤ D'),
        (259, pick(cn, '实际取电与网络', 'Metered power + grid'), pick(cn, 'F/X规则、平衡与声明限额', 'F/X, balances and declared limits')),
        (420, pick(cn, '同小时清洁匹配', 'Hourly clean matching'), 'αPΔt ≤ y ≤ Y'),
    ):
        s.text(x, 258, title, 7.6, anchor='middle')
        s.text(x, 275, detail, 7.6, anchor='middle')
    s.end()
    s.save('project_network_' + ('cn' if cn else 'en') + '.svg')


def workflow(cn):
    s = SVG(264, '研究比较与独立留出检验' if cn else 'Comparisons and independent holdout checks',
            'Given plans are compared using three assessments under common inputs, then frozen with a policy before causal holdout execution.')
    s.header(pick(cn, '用匹配比较解释差异，再检验新路径上的适用性',
                        'Explain assessment differences, then test new paths'),
             pick(cn, '研究设计与预期输出 · 方案判断由实际计算证据确定',
                        'Study design and intended outputs · judgments require computed evidence'))
    cards = [
        ('固定比较条件', 'Fix common conditions',
         ['给定建设与接入计划', '相同外生业务与CFE', '一致的期限与服务规则'],
         ['Given construction', 'and access plans', 'Same tasks + CFE', 'Same deadlines + rules']),
        ('比较三种评价', 'Compare assessments',
         ['瞬时MW', '固定恢复余量', '完整时序评价'],
         ['Instantaneous MW', 'Fixed recovery headroom', 'Full temporal assessment']),
        ('解释阶段性瓶颈', 'Explain bottlenecks',
         ['何时改变方案判断？', '当前响应还是期限内恢复？', '保留无差异与失败区域'],
         ['When do judgments differ?', 'Response or recovery?', 'Retain null + failure regions']),
        ('冻结后独立检验', 'Freeze, then test',
         ['冻结计划与运行策略', '独立留出路径', '按当时信息因果执行'],
         ['Freeze plan + policy', 'Independent holdout paths', 'Causal execution']),
    ]
    for i, (zh, en, body_zh, body_en) in enumerate(cards):
        x = 18 + i * 123
        s.group(f'n:step-{i + 1}')
        s.circle(x + 10, 68, 10, ICE, BLUE)
        s.text(x + 10, 71, str(i + 1), 8.5, True, 'middle')
        s.text(x, 95, pick(cn, zh, en), 8.5, True)
        s.rect(x, 106, 114, 89, MINT if i == 1 else PALE, LINE, 4)
        body = body_zh if cn else body_en
        if i == 1:
            for j, line in enumerate(body):
                yy = 126 + j * 25
                s.line(x + 9, yy - 3, x + 17, yy - 3, TEAL if j == 2 else BLUE, 2)
                s.text(x + 22, yy, line, 7.6)
        else:
            for j, line in enumerate(body):
                s.text(x + 9, 125 + j * (17 if i == 0 and not cn else 24), line, 7.6)
        if i < 3:
            s.line(x + 114, 151, x + 122, 151, INK, 1.2, True)
        s.end()
    s.line(381, 87, 381, 202, BLUE, 0.9, dash='3 3')
    s.text(442, 213, pick(cn, '留出不参与方案选择', 'Holdout excluded from selection'), 7.6, anchor='middle')
    s.rect(18, 229, 483, 24, ICE, ICE)
    s.text(259.5, 245, pick(cn, '预期输出：阶段性瓶颈、方案判断边界与适用范围',
                                'Intended outputs: stage bottlenecks, decision boundaries, applicability'), 8.5, True, 'middle')
    s.save('project_workflow_' + ('cn' if cn else 'en') + '.svg')


if __name__ == '__main__':
    for language in (True, False):
        for drawing in (rampup, recovery, network, workflow):
            drawing(language)
    print('Built 8 bilingual SVGs from the conceptual drawing specification.')
