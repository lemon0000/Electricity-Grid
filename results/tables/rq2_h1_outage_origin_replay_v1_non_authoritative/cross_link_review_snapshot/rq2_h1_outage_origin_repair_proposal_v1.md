# H1 outage 初态来源与 repair cap 后继提案

2026-10-08，DRAFT_NONAUTHORITATIVE。本页是待用户科学批准的具体规则，不是已批准v2协议的
补记，也不是执行配置。现有6个边界输入继续unresolved，全部原始窗口/权重/义务保留。
本页不修改旧src、冻结package、封存协议、旧结果或numeric门。

## 可重建来源与仍缺失的量

冻结生成配置SHA256 cefec120fb77990a47fe7e89a77e4df8be00bde5bf7e4cd4c5ca047d52934688；
power package manifest SHA256 28bc2c3c1ee3ba0ef6c940aec56f66d49587b5f2895d0e6b0b83fb0b6360cc63。
`experiments/audit_h1_outage_origin_replay_development_v1.py` 验证冻结builder/chronology及
grid/CFE upstream manifests；重放211个components、8784小时、439个events，与25704条可见
power rows的三字段逐项一致。full-event table只用于离线provenance oracle，不生成边界输入。
holdout边界另用horizon=boundary+1单独重放，核验延长horizon不改变已揭示component prefix。

| split/seed | 缺失的raw boundary | prefix重放证据 |
|---|---:|---|
| training/20260822 | -1 | generator无负时间；hour0无事故不能推导hour-1 |
| training/20260823 | -1 | hour0 stationary-down branch B14；仍不能推导hour-1 |
| training/20260824 | -1 | hour0 stationary-down branch A15；仍不能推导hour-1 |
| holdout/20260822 | 4439 | generator 202_CT_2在该小时active |
| holdout/20260823 | 4559 | 在该小时无事故 |
| holdout/20260824 | 4631 | 在该小时无事故 |

split hour=4392。holdout前置小时属于同split；缺行源于整块剔除规则。生成receipt仅为机制
派生证据，不是已有power row，不得冒充旧同chain窗口检查成功。3个training初态无法通过
技术重放恢复；要覆盖它们必须明确改变chronology-origin规则。

## 提请批准A：独立的 chronology-origin 规则

仅适用于raw_start=0。将冻结生成机制在hour0的stationary初始抽样明确注册为“首动作前已
揭示的初始outage overlay”。新类型须明确 `kind=chronology_origin`、`source_hour=0`、
`predecessor_source_hour=null`，不得伪造hour-1。保留initial-down component，未知onset为None，
不声明事故年龄、既往trip/repair或剩余持续时间，不增加故障前历史。

首小时动作在该初始overlay上执行；首动作前没有可观察的事故转换，不能把initial-down
计为新trip或创造repair cap。后续小时恢复普通current-only disclosure转移。后继kernel/owner
须使用显式首动作路径及类型，不把首行同时伪装为两个时间点的source row。
Rref/A初始generation继续采用已批准N初值与初始有效可用性，按原静态界验收；失败unresolved。
这是一项合成benchmark初始化机制，而不是对真实入窗前历史的推断。

## 提请批准B：同split生成边界来源

仅对catalog中缺行的3个holdout窗口，允许固定source owner按冻结seed、211个components、
算法与upstream pins，从生成过程起点内部重放到raw_start-1。生产边界路径只生成该截止前缀，
不读取full-event table的未来end，不读取training power rows，不把pre-split状态交给策略。
输出独立 `kind=generated_same_split_boundary` receipt；真实source_hour、seed、event ID、
源hash与重放身份只留审计，decision只含component/无事故及unknown-onset状态。
同split含义依据原split cut和目标raw hour，不声称原chain存在被剔除的raw row。

普通窗口继续优先使用既有same-chain predecessor，不扩大支持、改权重或重建冻结package。
三种origin来源类型须进入审计合同；类型/标签不允许改变相同可见物理状态下的policy动作。
预注册后需全catalog验证所有义务均取得适用初态且obligations_removed=0；audit-only receipt
本身不能打开full_boundary_coverage_verified门。

## 提请批准C：固定逐机组 repair-return 机制表

建议事先注册一张按generator UID排序的固定MW参数表：

`repair_cap_g = min(source_Pmax_g, source_ramp_mw_per_hour_g * 1 hour)`。

这是新提出的机制规则，尚未批准。它不声称识别了真实修后启动曲线，不根据某次event未来
结束、调度结果或成功率选择cap。来源字段、原始值、单位、exact decimal投影及结果表必须
在运行前pin并独立审查，数值不可为通过测试而调大。若原始ramp无有效有限非负数值则unresolved。

仅在当前disclosure观察到某generator从outage返回时，按ended UID取已注册cap；否则cap=None。
该值限制从该lane此前实际generation至本小时的return增量，不替代source_Pmax、当前
normal commitment、Pmin、普通ramp或其他物理约束；仍执行原physical kernel所有门。
若cap与Pmin或其他条件不相容，则该小时无可接受见证，保留诊断，不能自动增大cap。

表由N/Rref/A共用同一注册mechanism identity，逐小时报告绑定表hash、UID和当前揭示转换；
不得让调用方在同一历史上自由替换cap，也不得把repair cap当作真实工程认证。

## 批准后的验收顺序

1. 新version/type及独立origin/cap registry；保留现有来源adapter和全部失败记录。
2. 覆盖initial-up/down、first action、continuation、repair、prefix extension、缺pin/漂移、
   全catalog与三链隔离反例；保持source labels和未来suffix不进入decision identity。
3. 接入persistent lane owner及same-key registry，再做N→Rref→业务/A→actual→paired commit。
4. 完整192小时producer、任务DAG/LB/UB及resource gates、封存、全新official独立审查。
5. 新native运行仍需具体包上的单独明确授权。

在A/B/C获得科学批准并完成实现验收前，origin/cap接入门保持关闭；当前允许的工作仅为
来源核验、可逆开发及安全短测试。批准本提案也不等于批准真实native或正式实验。
