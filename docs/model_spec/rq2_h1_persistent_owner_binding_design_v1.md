# H1 persistent owner 接线补充设计

2026-10-09，DRAFT_NONAUTHORITATIVE；根代理唯一writer。
保留此前persistent owner design原字节。本文记录 `/root/outage_preseal_review` 的只读API/科学状态核查，
不是owner实现完成、封存或official审查。fresh exact source join正单独接受PRE_SEAL审查。

## 输入与manifest

owner必须内部fresh调用N/outage/exact source join，只接受root与外部retained pins。
业务w复用N的12位half-even/250MW投影，`Q(str(B))=w*250`；CFE取当前power row的cfe_call_fraction。
共同Rref request由candidate_request_exact的numerator/denominator构造g，检查0≤g≤B。
每lane调用exact_business.current，任何域或阈值表示不一致显式business_input_unresolved。
不clamp、不扩大只批准给N generation的转换；raw workload>1的原六条来源保持unresolved。

science manifest必须绑定：E168/F≤24、due offset24、single nonrolling period、follow-up birth/debt保留，
canonical ordered lane roster及独立lane_id、physical Lane、Mechanism、BidirectionalPolicy，
workload/CFE规则、selector specs/limits/policy identities、repair mechanism、saved-record模式与record/byte bounds。
Mechanism包括alpha、flexible_fraction、recovery_headroom_fraction、unit250；policy保留D、minimum event、
ramp、response time、max recovery、recovery decimal places、rule/evidence class。
envelope七字段为recovery_efficiency、time_step_hours=1、maximum_event_duration_hours、maximum_event_count、
normalized_energy_budget、normalized_debt_limit、minimum_recovery_hours。

audit manifest绑定BoundaryAnchor的split、trajectory/trace、normalization SHA、seed、provenance SHA，
accounting_period_id、真实source clock对应和所有外部pins。
业务genesis hour0是相对边界，raw0 action映射business hour1；不伪造raw-1或观测来源。

## 重放、配对与失败

OwnerState保留completed_outer_hours、唯一共同Rref carry、每lane完整business/A carry和sticky halted信息，
以及outcome_head和registry_head。可执行carry不pickle；从canonical primitive records、exact ratios与
完整selector saved raw records逐小时重新构造和零solver replay。

intent前fresh admission，stable-read全部saved records并将其完整字节复制进intent archive。
intent后任何异常留下bare intent且禁止自动retry。共同Rref失败不发布任何lane。
Rref成功后所有active lanes消费同一g；business candidate成功再重放该lane自己的actual carry。
只有actual accepted才配对推进business/A。确定性unresolved时两边保留before并sticky halted。
先前halted lane记录skipped_halted；服务统计只读paired_committed，CFE-only grid指标保持None。
完整outer outcome中共同Rref只推进一次；最后active lane也失败时该小时仍可完整记录，然后owner terminal。
outer commit前重新验证N/source/registry/implementation。一次BEGIN IMMEDIATE发布claim、witness、
全部lane outcome与新heads；提交后完整replay再返回。commit/return模糊时owner poisoned。

## Same-key sticky conflict

request_key必须在Rref输出前构造，包含合同、relative hour、N/outage科学投影、Rref before、
ordered lane business/A before与halted状态、exact外生w/CFE、fixed science manifest identity。
g、business action、A generation、raw SHA、source labels与audit head均不得进入request_key。
projection digest才包含Rref g/after、每lane status/action/exact power/before或after/halt、
service applicability/None与outer scientific after。

key_claims保留首projection与status；key_witnesses保留每个完整独立witness；conflicts追加首/替代projection和head。
same key/same projection只增加witness；different projection永久conflict，保留两份原字节且不产生替代outcome。
外部retained token同时含outcome_head、registry_head；每次witness追加也推进registry_head，使旧handle失效。
fresh inspect检查完整outcome祖先key；若任一已conflict，continuation_available=false且不返回carry，
保留后继原字节并标记orphaned_after_conflicted_ancestor；不回滚、不重跑。
每次commit事务内再次核对两个heads与全部祖先claim。

## 仍开放

具体task manifest需列出每lane/cell/D、records、合法reuse DAG、完整同合同LB/UB。
当前exact source/historical controller支持至168小时；169..192必须由后继producer接续接受的N状态，
不能重置N、业务或评分窗口。真实raw ingress/Jobs、资源、successor seal、全新official review仍独立开放。
本设计不提供新的真实native运行授权。
