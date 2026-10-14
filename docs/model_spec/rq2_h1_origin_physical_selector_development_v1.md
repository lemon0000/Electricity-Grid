# H1 chronology-origin physical/selector 后继开发

DRAFT_NONAUTHORITATIVE；承接已批准 A/B/C。实现位于
`experiments/h1_origin_grid_step_development_v1.py` 和
`experiments/h1_origin_selector_replay_development_v1.py`。旧physical/selector、src、封存与旧记录不改。
本单元仍为detached数值开发，不认证来源、N选择、真实执行或持久提交。

## 双时钟与首动作

carry保留completed_hours（动作数）和event_hour_offset：chronology为0，ordinary/generated为1。
TransitionAction(t)要求after.source_hour=t+offset、before.source_hour=after.source_hour-1。
仅chronology t=0允许FirstAction；其before/after均是origin source0，不制造report或trip/repair。
完成k>=1动作后，disclosure.source_hour=k+offset-1；禁止重复raw0、错offset、运行中切换模式。

初始化沿用N normal_before声明generation及初始有效可用性：可用机组继承N初值、initial-down为0，
静态界不通过则拒绝。FirstAction模型使用该lane初始化generation，prior/current availability相同，
cap=None；普通own ramp、startup/shutdown、normal response等照常执行。raw1观察到修复时才进入
repair-return分支。Rref和每个A lane分别保有generation；不可由N或另一lane覆盖。

内部_PhysicalCurrent仅为已验证动作的方程参数视图，不是DisclosureStep或来源凭据。
旧模型从network/generator bounds到response、ramp、balance的完整数学body和Fraction residual
机械保留；没有伪造step以通过旧验证器。repair上升约束沿用已有专用分支，nameplate和其他门不变。

## 科学身份与审计身份

carry.identity用于科学计算：保留完整normal边界、lane own generation/availability/commitment、
completed actions、前一科学identity及规范化披露历史。披露历史含protocol、event count、active
local ordinal/component、first_seen与observed onset的相对动作小时。origin unknown-onset统一
first_seen=0、onset=None；后续事件时间减event_hour_offset。排除raw source clock、offset和审计链。
这样保留已观测历史，且first action与ordinary无新转换的相同可见物理状态具有相同科学键。

carry.audit_identity保留原披露state、offset和previous_audit_identity/step_audit_identity。
selector也拆分scientific/audit身份；stage context显式绑定predecessor_audit_identity与
action_audit_identity。来源时钟不同可产生相同科学模型，但不能把一份saved envelope换给另一
审计历史。真实source receipt、root/head pins和持久owner尚未接入；此处audit identity不等于认证。

共同Rref/A policy绑定已批准93机组exact cap表的semantic identity（UID、分子、分母及规则），
不把路径、authority说明或origin标签作为科学字段。单独的source registry负责固定cap lookup；
本纯physical接口仍可接受合成动作验证数学，不能据此宣称已认证registry输入。N接口、key、
carry与selector保持原样。

## Selector与验收

新schema重新编码saved records，不能沿用旧schema记录。Rref仍为(B-P_ref,L1,sorted UID generation)，
actual仍为(L1,sorted UID generation)。完整stage/frozen locks、recomputed objective、原gap/
residual/strict-lock门保留；失败suffix、缺stage、审计context替换均应拒绝，失败不产candidate。

验证采用ordinary路径对旧模型完整结构/数值审计的oracle，以及独立首动作解析fixture；AST检查
覆盖数学body、Fraction residual和selector stage audit，合成solver-shaped records只验证回放。
所有native_execution_authenticated/source_input_binding_verified/normal_selection_authenticated/
detached_consumer_authenticated/common_publication_verified/reference_or_actual_ready/formal_result
门保持false。后续仍需fresh accepted N与registry的owned联接、各lane持久链与same-key registry、
paired commit、192小时producer、完整资源包、封存及全新official审查；真实native仍单独授权。
