# H1 fresh exact source/current join 开发规格

2026-10-09，DRAFT_NONAUTHORITATIVE，R3；根代理唯一写入。
实现：`experiments/h1_exact_source_current_development_v1.py`。
本组件为后继 persistent owner 提供 fresh exact 外生输入，尚不持有 lane 或执行 paired commit。

## 来源与时序

公开prepare只接受N root、外部N binding/terminal pins、completed_hours与registry identity。
内部用已开发的historical controller重验全部obligation/Job/clock/parent前缀，从真实重放的packet/after
构造current-only N视图；再按N source declaration推导registry坐标，加载当前H1PinnedObservation，
调用已开发origin join核对raw power row、N before/after、component inventory和repair cap/nameplate。
没有caller-built envelope、Prefix、source row、float workload或业务输入入口。

返回前再次用相同pins重放N并共享同一filesystem observation；重验registry prefix、source observation、
来源文件视图与实现identity。这个类型本身不是认证凭据，后继owner必须在事务时重新调用prepare。
completed_hours仍限定1..168；本组件不补造follow-up N producer。

## Exact 规则

workload调用与N相同的 `project_workload_power(raw,'250',decimal_places=12)`。
保留raw decimal、half-even投影、精确误差和所有unresolved原因。投影payload必须逐字节等于accepted N packet，
并检查 `Q(str(B)) == workload_exact*250 == Q(str(projected_dc_baseline_mw))`。
该合法域等式来自既有str-float exact接口规则，不追加舍入、clip或clamp。
raw>1和正输入投影为零仍unresolved，保留全部来源义务。

`source_cfe_at_alpha_one_exact`只取当前fresh power row的`cfe_call_fraction`原始字符串，
用Fraction解析并要求[0,1]。其机制含义和CFE preallocation保持既有合同；不是经验联合观测。
本组件尚不接受Rref request或调用business adapter；后继owner应把唯一共同Rref的exact g
与这里的w/CFE输入按各lane固定Mechanism送入exact_business.current，阈值/表示不一致保持unresolved。

## Identity 和审计

scientific payload包括relative hour、current decision identity（含当前N和规范化outage投影）、
exact w/CFE ratio、固定workload/power投影规则、12位/250MW与CFE字段映射规则。
raw字符串不同但投影相同应科学identity相同；真实CFE数值改变必须改变scientific identity，
即使其不改变N numerical decision。
source坐标、timestamp、package/window/source identity、registry audit、原始投影/误差、N证据仅在audit。
audit保存完整normal envelope、当前source observation audit及已揭示registry prefix audit，并保留各自摘要。
返回audit沿用historical binding的128KiB record cap；超限显式拒绝，不丢弃字段，也不构成完整资源准入。
split/seed、绝对clock、raw report或inode不进入scientific payload。

shared_observed_clock、accepted_real_RTS_root_integration_verified、detached_consumer_authenticated、
persistent_lane_owner_implemented、common_publication_verified、full_192_hour_execution_verified、
resource_admission、formal_execution_ready、formal_result、native_execution_authorized全部false。

## 验证边界

单元测试显式替换historical controller和来源/catalog seams，以验证exact投影、时序、identity与拒绝路径；
它们不是完整真实N root或RTS/native producer集成证据。完整historical controller的独立证据另见其879pins。
仍需本单元独立PRE_SEAL审查、完整source-bound owner接线与后续实际任务/资源/封存/official门。
