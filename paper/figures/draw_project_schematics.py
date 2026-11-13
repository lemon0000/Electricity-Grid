"""Draw the bilingual project architecture and mechanism schematics as live SVG.

The figures encode study design and model relationships, not numerical results.
All coordinates are illustration geometry. Run with Python 3.12+ and Pillow.
Use --output-dir for an isolated draft; the default is this script's directory.
"""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

from PIL import ImageFont


WIDTH = 183 * 72 / 25.4
INK = '#243442'
EDGE = '#A6B2BD'
PALE = '#F4F6F8'
TEAL = '#237D82'
TEAL_PALE = '#EDF6F5'
BLUE = '#3E7096'
AMBER = '#B1813C'
AMBER_PALE = '#FBF6EA'


class Figure:
    def __init__(self, name: str, lang: str, height: float, title: str):
        self.name, self.lang, self.height = name, lang, height
        self.family = 'Microsoft YaHei' if lang == 'cn' else 'Arial'
        self.font_path = Path('C:/Windows/Fonts') / ('msyh.ttc' if lang == 'cn' else 'arial.ttf')
        self.font = ImageFont.truetype(str(self.font_path), size=1000)
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="183mm" height="{height * 25.4 / 72:.6f}mm" viewBox="0 0 {WIDTH:.6f} {height}">',
            f'<title>{escape(title)}</title>',
            '<desc>Editable scientific schematic of the research design. Geometry is illustrative and carries no experimental values.</desc>',
            '<defs>',
        ]
        for key, color in [('ink', INK), ('teal', TEAL), ('blue', BLUE), ('amber', AMBER)]:
            self.parts.append(f'<marker id="arrow-{key}" viewBox="0 0 8 6" refX="7.4" refY="3" markerWidth="5" markerHeight="4" orient="auto-start-reverse" markerUnits="strokeWidth"><path d="M0,0 L8,3 L0,6 Z" fill="{color}"/></marker>')
        self.parts.extend(['</defs>', f'<rect width="{WIDTH:.6f}" height="{height}" fill="#FFFFFF"/>'])
        self.boxes = []
        self.texts = []
        self.edges = []
        self.sequence = 0

    def tr(self, cn: str, en: str) -> str:
        return cn if self.lang == 'cn' else en

    def uid(self, prefix: str) -> str:
        self.sequence += 1
        return f'{prefix}-{self.sequence}'

    def text(self, x, y, value, size=7, bold=False, anchor='start', key=None):
        size = 6.2 if size < 7 else size
        key = key or self.uid('t')
        width = self.font.getlength(value) * size / 1000
        left = x - width / 2 if anchor == 'middle' else x - width if anchor == 'end' else x
        assert left >= -0.01 and left + width <= WIDTH + 0.01, (self.name, value, left, width)
        assert y - size >= 0 and y + size * 0.25 <= self.height, (self.name, value, y)
        self.texts.append({'id': key, 'text': value, 'bbox': [left, y - size, left + width, y + size * .25], 'font_size': size})
        content = []
        start = 0
        for match in re.finditer(r'_\(([^)]+)\)|_([A-Za-z]+)', value):
            content.append(escape(value[start:match.start()]))
            content.append('<tspan baseline-shift="sub" font-size="6">' + escape(match[1] or match[2]) + '</tspan>')
            start = match.end()
        content.append(escape(value[start:]))
        self.parts.append(f'<text id="{key}" x="{x:.3f}" y="{y:.3f}" font-family="{self.family}, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{anchor}" fill="{INK}">{"".join(content)}</text>')

    def rect(self, x, y, w, h, fill='#FFFFFF', stroke=EDGE, key=None, line_width=.65):
        key = key or self.uid('n')
        assert x >= 0 and y >= 0 and x + w <= WIDTH + .01 and y + h <= self.height + .01
        self.parts.append(f'<rect id="{key}" x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" rx="1.5" fill="{fill}" stroke="{stroke}" stroke-width="{line_width}"/>')
        self.boxes.append({'id': key, 'bbox': [x, y, x + w, y + h]})

    def block(self, x, y, w, h, title, lines=(), fill='#FFFFFF', accent=False, size=6.6):
        size = 6.2
        self.rect(x, y, w, h, fill, TEAL if accent else EDGE, line_width=.9 if accent else .65)
        values = [title, *lines]
        spacing = 10
        start = y + h / 2 - (len(values) - 1) * spacing / 2 + 2.4
        for i, value in enumerate(values):
            actual_size = 7 if i == 0 else size
            assert self.font.getlength(value) * actual_size / 1000 <= w - 10, (self.name, value, w)
            self.text(x + w / 2, start + i * spacing, value, actual_size, anchor='middle')

    def section(self, x, y, value):
        self.text(x, y, value, 8, bold=True)

    def line(self, points, color=INK, width=.75, dash=False, arrow=False, meaning=None):
        key = self.uid('e')
        pts = ' '.join(f'{x:.3f},{y:.3f}' for x, y in points)
        extras = ' stroke-dasharray="3 2"' if dash else ''
        if arrow:
            color_key = {INK: 'ink', TEAL: 'teal', BLUE: 'blue', AMBER: 'amber'}[color]
            extras += f' marker-end="url(#arrow-{color_key})"'
        self.parts.append(f'<polyline id="{key}" points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"{extras}/>')
        self.edges.append({'id': key, 'points': points, 'arrow': arrow, 'dashed': dash, 'meaning': meaning})

    def arrow(self, points, color=INK, dash=False, meaning=None, width=.85):
        self.line(points, color, width, dash, True, meaning)

    def save(self, output):
        self.parts.append('</svg>')
        svg = output / f'project_{self.name}_{self.lang}.svg'
        svg.write_text('\n'.join(self.parts) + '\n', encoding='utf-8', newline='\n')
        overlaps = []
        for i, a in enumerate(self.texts):
            for b in self.texts[i + 1:]:
                aa, bb = a['bbox'], b['bbox']
                dx = min(aa[2], bb[2]) - max(aa[0], bb[0])
                dy = min(aa[3], bb[3]) - max(aa[1], bb[1])
                if dx > .4 and dy > .4:
                    overlaps.append([a['id'], b['id'], round(dx * dy, 2)])
        assert not overlaps, (self.name, self.lang, 'text_overlaps', overlaps)
        return {'file': svg.name, 'width_mm': 183, 'height_pt': self.height, 'font_family': self.family, 'minimum_font_pt': min(t['font_size'] for t in self.texts), 'text_count': len(self.texts), 'text_overlap_findings': overlaps, 'texts': self.texts, 'nodes': self.boxes, 'edges': self.edges, 'data_role': 'Nonquantitative study-design schematic'}


def framework(lang, output):
    f = Figure('framework', lang, 370, 'Research architecture for staged interconnection deliverability')
    t = f.tr
    f.section(12, 15, t('a  三条给定进度与共同条件', 'a  Given progress paths and common conditions'))
    inputs = [
        (t('业务达产', 'Business ramp-up'), [t('任务到达 A_j、原期限 d_j', 'Task arrivals A_j; deadlines d_j'), t('当期基准工作 w_t', 'Current baseline work w_t')]),
        (t('设备投运', 'Equipment commissioning'), [t('实际投运状态 → K_t', 'Observed commissioning → K_t'), t('待机与活动功耗参数', 'Idle and active-power parameters')]),
        (t('电网建设', 'Grid construction'), [t('建成网络 N_t；接入 F_t、X_t', 'Built network N_t; access F_t, X_t'), t('实际完工与已揭示故障', 'Observed completion and outages')]),
    ]
    xs = [12, 183, 354]
    for x, (title, lines) in zip(xs, inputs):
        f.block(x, 26, 152, 42, title, lines, PALE)
        f.arrow([(x + 76, 68), (x + 76, 78)], meaning='Observed path inputs')
    f.block(12, 78, 494, 26, t('共同任务、合同与外部资源', 'Common tasks, contracts and external resources'), [t('D、π、α、Y_t；服务规则与设备—功耗映射', 'D, π, α, Y_t; service rules and equipment-to-power mapping')], PALE, size=6.4)
    f.section(25, 121, t('b  三种并列评价', 'b  Parallel assessments'))
    methods = [
        (131, t('瞬时 MW', 'Instantaneous MW'), t('当期必要检查', 'Current-hour necessary checks')),
        (176, t('固定恢复余量', 'Fixed recovery headroom'), t('R_fix 与同批次账本', 'R_fix and the same task cohorts')),
        (221, t('完整时序', 'Full temporal assessment'), t('真实资源与固定因果策略', 'Actual resources; causal policy')),
    ]
    f.line([(16, 104), (8, 104), (8, 237)], meaning='Shared exogenous inputs; alternatives are not sequential')
    for y, title, subtitle in methods:
        f.block(25, y, 122, 32, title, [subtitle], TEAL_PALE if y == 221 else '#FFFFFF', accent=y == 221, size=6.2)
        f.arrow([(8, y + 16), (25, y + 16)], meaning='Same common inputs')
        f.line([(147, y + 16), (164, y + 16)], meaning='Each method supplies its own schedule and history')
    f.line([(164, 147), (164, 237)], meaning='Alternative schedules')
    f.section(177, 121, t('c  实际路径的时序核验', 'c  Temporal checks on the actual path'))
    f.rect(176, 130, 330, 124, TEAL_PALE, TEAL, line_width=.9)
    f.arrow([(164, 164), (187, 164)], meaning='Each method replays from its own history')
    f.block(187, 146, 94, 39, t('观测与完整请求', 'Observe; derive requests'), [t('w_t、K_t、N_t、Y_t', 'w_t, K_t, N_t, Y_t'), t('参考 P⁰_t → g_t、h_t', 'Reference P⁰_t → g_t, h_t')], size=6.2)
    f.block(295, 146, 94, 39, t('动作与共享资源', 'Actions and shared limits'), [t('本方法的 q_t 或 r_t', 'Own q_t or r_t'), 'q + r ≤ D;  w − q + r ≤ K'], size=6.2)
    f.block(403, 146, 92, 39, t('实际取电与检查', 'Power and service checks'), [t('P_t；网络；小时 CFE', 'P_t; network; hourly CFE'), t('响应、任务与原期限', 'Response; tasks; deadlines')], size=6.1)
    f.arrow([(281, 165.5), (295, 165.5)], meaning='Complete requests; no prior clipping')
    f.arrow([(389, 165.5), (403, 165.5)], meaning='Map execution to metered power')
    f.block(187, 214, 308, 26, t('更新逐批债务、预算与运行状态', 'Update cohort debt, budgets and operating state'), ['b_(j,t+1) = b_(j,t) + q_(j,t) Δt − η_j r_(j,t) Δt'], size=6.4)
    f.arrow([(450, 185), (450, 214)], meaning='Observed checks and task execution update the state')
    f.arrow([(226, 214), (226, 185)], TEAL, dash=True, meaning='Accepted state carried to the next hour')
    f.text(214, 202, 't + 1', 6.2, anchor='end')
    f.text(341, 250, t('各方法安排分别重放并延续状态；完整 F/X 另核', 'Replay states remain separate; full F/X checked separately'), 6.1, anchor='middle')
    f.section(12, 275, t('d  候选贡献对应的比较证据', 'd  Evidence for the proposed contributions'))
    f.text(25, 260, t('方法自身判断', 'Own assessment judgments'), 6.2)
    f.arrow([(164, 237), (164, 263), (8, 263), (8, 279), (85, 279)], meaning='Method judgments enter comparison independently of full replay')
    f.arrow([(342, 254), (342, 279)], meaning='Actual-path task and service outcomes')
    f.line([(85, 279), (430, 279)], meaning='Combine method judgments and actual-path checks')
    for x, title, line in [
        (12, t('阶段瓶颈转换', 'Stage bottleneck transitions'), t('即时工作 / 设备 / 供电 / 清洁', 'Work / equipment / power / CFE')),
        (183, t('匹配恢复时段', 'Matched recovery timing'), t('同请求、清洁总量与峰值；债务分层', 'Match requests, CFE total and peak')),
        (354, t('两轴评价判断差异', 'Two comparison axes'), t('自身 × 重放；自身 × 完整策略', 'Own vs replay; own vs full policy')),
    ]:
        f.block(x, 286, 152, 30, title, [line], size=6.1)
        f.arrow([(x + 76, 279), (x + 76, 286)], meaning='Evidence, not a demonstrated empirical result')
    f.text(12, 332, t('三值定值；债务按结果分层', 'Three values; stratify by debt'), 6.2)
    f.rect(183, 322, 152, 12, PALE)
    f.text(259, 330.5, t('未参与选择的新路径', 'New paths held out from selection'), 6.3, anchor='middle')
    f.arrow([(259, 334), (259, 340)], meaning='Independent new paths feed causal holdout execution')
    f.block(12, 340, 135, 24, t('冻结计划、D 与 π', 'Freeze plan, D and π'))
    f.block(183, 340, 152, 24, t('按当时信息因果执行', 'Execute with information available then'))
    f.block(370, 340, 136, 24, t('可交付 / 不可交付 / 未决', 'Deliverable / failed / unresolved'))
    f.arrow([(147, 352), (183, 352)], meaning='Frozen policy, no holdout-driven reselection')
    f.arrow([(335, 352), (370, 352)], meaning='Holdout task and service outcomes')
    return f.save(output)


def recovery(lang, output):
    f = Figure('recovery', lang, 262, 'Task-cohort debt, recovery resources and deadline outcomes')
    t = f.tr
    f.section(12, 15, t('a  同一任务批次的连续账本', 'a  Continuous accounting for the same task cohort'))
    for x, title, detail in [
        (12, t('到达与当期延期', 'Arrival and current deferral'), 'A_j;  q_(j,t) Δt'),
        (183, t('未完成延期工作', 'Unfinished deferred work'), 'b_(j,t)  [MWh_c]'),
        (354, t('合法补做', 'Admissible recovery'), 'η_j r_(j,t) Δt'),
    ]:
        f.block(x, 29, 152, 38, title, [detail], TEAL_PALE if x == 183 else '#FFFFFF', accent=x == 183)
    f.arrow([(164, 48), (183, 48)], meaning='Only eligible current tasks create debt')
    f.arrow([(335, 48), (354, 48)], meaning='Recovery consumes the same cohort debt')
    f.text(WIDTH / 2, 87, 'b_(j,t+1) = b_(j,t) + q_(j,t) Δt − η_j r_(j,t) Δt', 7, anchor='middle')
    f.section(12, 112, t('b  补做小时的共同资源约束', 'b  Resources must align in the recovery hour'))
    resources = [
        (12, t('已投运设备', 'Commissioned equipment'), 'r ≤ K − w'),
        (140, t('当前网络供电', 'Built-network supply'), t('P(r) 在可供范围内', 'P(r) within feasible supply')),
        (268, t('同小时清洁额度', 'Same-hour clean allocation'), 'α P(r) Δt ≤ Y'),
        (396, t('业务与动作限制', 'Work and action limits'), 'r ≤ D;  η r Δt ≤ b'),
    ]
    for x, title, detail in resources:
        f.block(x, 124, 110, 34, title, [detail], PALE, size=6.1)
        f.line([(x + 55, 158), (x + 55, 165)], meaning='Concurrent constraints')
    f.line([(67, 165), (451, 165)], meaning='All recovery restrictions are checked jointly')
    f.arrow([(259, 165), (259, 173)], meaning='Jointly admissible recovery and original deadline')
    f.block(188, 173, 142, 22, t('原期限时点已观察？', 'Deadline time observed?'))
    f.text(25, 194, t('是：核对到期债务', 'Yes: check debt at the deadline'), 6.2)
    f.text(439, 194, t('否', 'No'), 6.2)
    outcomes = [
        (12, t('期限到且债务为零', 'Deadline observed; debt = 0'), t('按期完成', 'Completed on time'), TEAL_PALE),
        (183, t('期限到仍有债务', 'Deadline observed; debt > 0'), t('记录逾期；晚补做仍保留', 'Record overdue; retain after late recovery'), AMBER_PALE),
        (354, t('期限在观察窗之外', 'Deadline outside observation'), t('右删失', 'Right-censored'), PALE),
    ]
    for x, title, detail, fill in outcomes:
        f.block(x, 204, 152, 31, title, [detail], fill, size=6.1)
    f.line([(259, 195), (259, 199), (88, 199)], meaning='Observed deadline permits debt assessment')
    f.arrow([(88, 199), (88, 204)], meaning='Debt zero at the original deadline')
    f.arrow([(259, 199), (259, 204)], meaning='Debt positive at the original deadline')
    f.arrow([(330, 184), (430, 184), (430, 204)], meaning='Original deadline not observed: right-censored')
    f.text(12, 247, t('求解或核查结果缺失另记为未决；不将其判为数学不可行。', 'Missing solve/check results are unresolved; they do not establish mathematical infeasibility.'), 6.1)
    f.text(12, 260, t('补做小时 q = 0；α = 0 时无清洁恢复上限。图为机制示意。', 'Recovery hours have q = 0; α = 0 removes the CFE cap. Mechanism schematic.'), 6.1)
    return f.save(output)


def rampup(lang, output):
    f = Figure('rampup', lang, 256, 'Independent progress paths enter current operating and recovery constraints')
    t = f.tr
    f.section(12, 15, t('a  三条路径分别给定，实际状态逐小时揭示', 'a  Separate paths; actual states revealed hour by hour'))
    for x, value in [(132, t('早期运行', 'Early operation')), (273, t('工程在建', 'Reinforcement pending')), (420, t('工程投运后', 'After commissioning'))]:
        f.text(x, 35, value, 7, anchor='middle')
    f.rect(230, 43, 140, 105, PALE, '#FFFFFF')
    for y, value in [(64, t('业务 w_t', 'Work w_t')), (101, t('设备 K_t', 'Equipment K_t')), (138, t('电网 N_t', 'Grid N_t'))]:
        f.text(12, y, value, 7)
    f.line([(105, 68), (160, 68), (160, 60), (230, 60), (230, 54), (310, 54), (310, 49), (495, 49)], BLUE, 1.3, meaning='Qualitative workload ramp-up, no numeric scale')
    f.line([(105, 106), (190, 106), (190, 96), (325, 96), (325, 86), (495, 86)], INK, 1.3, meaning='Only observed equipment commissioning adds capacity')
    f.line([(105, 141), (370, 141), (370, 125), (495, 125)], TEAL, 1.3, meaning='Built network changes only at actual commissioning')
    f.line([(230, 43), (230, 148)], EDGE, .65)
    f.line([(370, 43), (370, 148)], EDGE, .65)
    f.arrow([(105, 156), (498, 156)], meaning='Continuous physical time')
    f.text(498, 167, t('时间 t', 'Time t'), 6.5, anchor='end')
    f.text(12, 167, t('路径仅示意相对时序，无数值尺度', 'Illustrative relative timing; no numerical scale'), 6.1)
    f.section(12, 189, t('b  当期请求与恢复条件随已投运状态重算', 'b  Recompute calls and recovery limits on commissioned resources'))
    items = [
        (12, t('可延期工作', 'Deferrable current work'), 'q ≤ f w'),
        (140, t('设备恢复余量', 'Equipment headroom'), 'r ≤ K − w'),
        (268, t('网络供电范围', 'Network supply range'), t('当前 N_t 下核查 P', 'Check P on current N_t')),
        (396, t('清洁恢复空间', 'Clean recovery room'), t('α > 0：P⁰ + a r ≤ Y/(αΔt)', 'α > 0: P⁰ + a r ≤ Y/(αΔt)')),
    ]
    for x, title, detail in items:
        f.block(x, 201, 110, 34, title, [detail], PALE, size=6.0)
    f.text(WIDTH / 2, 252, t('债务、期限与预算跨阶段延续；恢复条件取 q = 0，a = γβ。', 'Debt, deadlines and budgets carry across stages; recovery limits use q = 0, a = γβ.'), 6.1, anchor='middle')
    return f.save(output)


def network(lang, output):
    f = Figure('network', lang, 264, 'Computing effort, metered power and separate network/CFE checks')
    t = f.tr
    f.section(12, 15, t('a  从业务动作到计量点实际取电', 'a  From workload actions to metered electrical power'))
    f.block(12, 30, 142, 45, t('任务与共享调节资源', 'Tasks and shared flexibility'), ['q = c_grid + c_cfe', 'q + r ≤ D;  q r = 0'], size=6.6)
    f.block(188, 30, 142, 45, t('实际计算资源占用', 'Active computing effort'), ['z = w − q + r', '0 ≤ z ≤ K  [MW_c]'], TEAL_PALE, accent=True)
    f.block(364, 30, 142, 45, t('计量点电功率', 'Metered electrical power'), ['P = γ(P_idle + βz) + P_aux', 'P  [MW];  E = P Δt  [MWh]'], size=6.2)
    f.arrow([(154, 52), (188, 52)], meaning='The same physical workload population')
    f.arrow([(330, 52), (364, 52)], meaning='Equipment-to-power mapping')
    f.section(12, 104, t('b  同一实际取电接受两类检查', 'b  The same metered consumption enters two checks'))
    f.block(12, 119, 142, 42, t('当前建成电网', 'Currently built grid'), ['N_t;  F_t, X_t', t('实际功率平衡与限额', 'Actual balances and limits')], PALE)
    f.block(188, 119, 142, 42, t('固定接入点计量', 'Fixed point of interconnection'), ['P_t  [MW]', 'P_t Δt  [MWh]'])
    f.block(364, 119, 142, 42, t('同小时属性归属', 'Same-hour attribution'), ['0 ≤ y ≤ min(Y, P Δt)', 'α P Δt ≤ y'], PALE)
    f.arrow([(154, 140), (188, 140)], BLUE, meaning='Physical electricity supply', width=1.35)
    f.arrow([(435, 75), (435, 90), (259, 90), (259, 119)], meaning='Metered P comes from the full equipment-to-power mapping')
    f.arrow([(330, 140), (364, 140)], TEAL, dash=True, meaning='Metered consumption record; not physical clean-electron flow')
    f.text(435, 181, t('外部同小时额度 Y；0 ≤ α ≤ 1', 'External same-hour quota Y; 0 ≤ α ≤ 1'), 6.4, anchor='middle')
    f.arrow([(435, 174), (435, 161)], TEAL, dash=True, meaning='External attributable clean allocation')
    f.text(12, 181, t('蓝实线：物理供电', 'Blue solid: physical supply'), 6.4)
    f.text(188, 181, t('青虚线：记录与属性核算', 'Teal dashed: records and attributes'), 6.4)
    f.section(12, 209, t('c  服务承诺与接入合同分别保留', 'c  Retain service promises and access-contract checks'))
    f.block(12, 220, 242, 30, t('网侧与 CFE 的延期承诺独立分配', 'Allocate grid and CFE deferral promises separately'), [t('每单位 q 分配一次；实际 P 只计一次', 'Allocate each unit of q once; count physical P once')], size=6.2)
    f.block(268, 220, 238, 30, t('完整 F/X 接入合同另核', 'Check the full F/X access contract separately'), [t('正常/故障网络、业务必要条件与时序证据', 'Normal/outage network, business and temporal evidence')], PALE, size=6.1)
    f.text(12, 259, t('P 包含已投运设备待机、执行、补做与配套耗能。网络边界为声明的 DC 模型与故障集合。', 'P includes commissioned idle, execution, recovery and support loads; network scope is the declared DC model and contingencies.'), 6.0)
    return f.save(output)


def export_figures(output: Path, records: list[dict], chrome_executable: str | None) -> dict:
    try:
        import pymupdf
    except ImportError as exc:
        raise RuntimeError('PDF/PNG export requires PyMuPDF (pip install pymupdf). SVG sources were generated.') from exc
    chrome = chrome_executable or shutil.which('chrome') or 'C:/Program Files/Google/Chrome/Application/chrome.exe'
    if not Path(chrome).is_file():
        raise FileNotFoundError('Use --chrome-executable to select an installed Chromium/Chrome executable.')
    scratch = Path(tempfile.mkdtemp(prefix='project-schematic-export-'))
    exports = []
    for language in ('cn', 'en'):
        selected = [r for r in records if r['file'].endswith('_' + language + '.svg')]
        styles, sections = [], []
        for i, record in enumerate(selected):
            styles.append(f'@page panel{i} {{size:183mm {record["height_pt"] * 25.4 / 72:.9f}mm;margin:0;}} section.panel{i} {{page:panel{i};break-after:page;}}')
            sections.append(f'<section class="panel{i}">' + (output / record['file']).read_text(encoding='utf-8') + '</section>')
        html = '<!doctype html><html><head><meta charset="utf-8"><style>html,body,section{margin:0;padding:0;}svg{display:block;}' + ''.join(styles) + '</style></head><body>' + ''.join(sections) + '</body></html>'
        html_path = scratch / (language + '.html')
        combined = scratch / (language + '.pdf')
        html_path.write_text(html, encoding='utf-8')
        command = [chrome, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-pdf-header-footer', '--run-all-compositor-stages-before-draw', '--timeout=45000', '--user-data-dir=' + str(scratch / ('chrome_' + language)), '--print-to-pdf=' + str(combined), html_path.as_uri()]
        with (scratch / (language + '.log')).open('wb') as log:
            done = subprocess.run(command, stdout=log, stderr=log, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if done.returncode:
            raise RuntimeError(f'Chromium export failed for {language}; log: {scratch / (language + ".log")}')
        document = pymupdf.open(combined)
        assert len(document) == len(selected), (language, len(document))
        for page, record in zip(document, selected):
            stem = Path(record['file']).stem
            single = pymupdf.open()
            single.insert_pdf(document, from_page=page.number, to_page=page.number)
            single.save(output / (stem + '.pdf'), garbage=3, deflate=True)
            assert not page.get_images(), (stem, 'unexpected rasterized SVG content')
            preview = page.get_pixmap(matrix=pymupdf.Matrix(300 / 72, 300 / 72), alpha=False)
            preview.set_dpi(300, 300)
            preview.save(output / (stem + '.png'))
            exports.append({'stem': stem, 'pdf_width_pt': page.rect.width, 'pdf_height_pt': page.rect.height, 'png_pixels': [preview.width, preview.height], 'raster_images_in_pdf': 0, 'native_text_characters': len(page.get_text())})
    return {'python': platform.python_version(), 'pymupdf': pymupdf.VersionBind, 'renderer': 'Chromium headless/Skia', 'canonical_format': 'SVG with live text', 'preview_dpi': 300, 'files': exports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--export', action='store_true', help='Export native vector PDF and 300-dpi PNG using installed Chromium and PyMuPDF')
    parser.add_argument('--chrome-executable', help='Installed Chrome/Chromium executable')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {'role': 'Nonquantitative study-design schematics', 'generator': Path(__file__).name, 'figures': []}
    for language in ('cn', 'en'):
        for draw in (framework, recovery, rampup, network):
            report['figures'].append(draw(language, args.output_dir))
    if args.export:
        report['export'] = export_figures(args.output_dir, report['figures'], args.chrome_executable)
    (args.output_dir / 'project_vector_geometry.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'figures': len(report['figures']), 'text_overlap_findings': 0, 'output': str(args.output_dir)}, ensure_ascii=True))


if __name__ == '__main__':
    main()
