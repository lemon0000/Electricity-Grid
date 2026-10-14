# H1 source-bound persistent owner 开发规格

2026-10-09，DRAFT_NONAUTHORITATIVE。根代理唯一 writer；当前实现与测试仍在验证，尚无闭合审查。

本单元把已闭合的 historical N/exact source、origin selector replay、exact business 接入一个本地持久 owner。
每个 enrollment owner 保存一个共同 Rref，以及 canonical ordered roster 中每个 lane 自己的完整 business/A carry。
API 接收固定 typed manifest、source root/binding/registry/genesis terminal pins；后续每小时接收 terminal pin
和不可变 saved-record bytes。公开入口不接受调用方构造的 source current、业务状态或物理状态。

## 合同与来源

Manifest 绑定 E=168、F≤24、due offset=24、single nonrolling period、followup birth/debt 保留规则，
各 lane 的 policy、D、alpha、flexible fraction、recovery headroom、七字段 hourly envelope，
Rref/A selector、solver spec、replay limits 和显式 event/count/archive byte bounds。
accounting period label、capacity declaration label 和 journal 存储容量只留在 audit manifest；
它们不进入 scientific request key。完整审计 header 在每次操作中重新构造核对。
当前 source producer 仅支持第 1–168 小时；不能把协议的 192 小时上限当成已实现的 producer。

Owner 内部 fresh 调用 exact_source_current.prepare。业务 workload 与 N 的 12 位 half-even 投影一致，
CFE 为当前 power row 的 exact Fraction；Rref request 是 B−P_ref 的 exact ratio。
Anchor 从当前一行 power/workload window 重新核对 row、window identity、chain identity、package SHA；
normalization 逐字段采用 source_pair 的既有六字段 recipe。业务 clocks=(0,0) 表示相对初态，
第 t 个 source action 对应 business hour=t+1，不表示 raw−1 存在。
后续 action 要保持相同 chain、normalization、seed 和 provenance。
Outage 的 chronology origin/入窗事故独立由已闭合 registry 与 origin selector 处理。

## 写入顺序与重开

本地固定 NTFS、单进程/OS execution lease、regular single-link 文件、固定 schema、SQLite DELETE/FULL。
数据库保存 canonical primitives 与 base64 编码的完整 raw records，不保存 pickle 或可直接消费的 carry。
重开要求提供相同 typed configuration 和外部保存的 outcome_head/registry_head，逐项核对 header，
随后从 fresh genesis 重新执行所有历史 source admission、Rref replay、exact business 和 actual replay。

每次操作先保存 intent，包含 source audit、before heads、request key、全部 saved records。
Rref 不完整/失败或之后发生异常均保留 bare intent，禁止自动重试或追加下一小时。
Rref 完整后各 active lane 消费同一个 g。只有 business candidate 与 actual replay 均成功，
才以 paired_committed 同时推进该 lane 的 business/A。确定的业务输入未决、业务未决或 actual 未决
保留双 before carry 并 sticky halted；已经 halted 的 lane 只记 skipped_halted。
共同 Rref 在一个完整 outer outcome 中只推进一次。最后一个 active lane 失败后 owner 停止推进。
服务计数必须只使用 paired_committed；未发布的业务候选动作不是已服务，CFE-only 的 grid metric 保留 None。

Commit 前重读当前 source，并核对 implementation。单次 BEGIN IMMEDIATE 将完整 outer outcome
作为一个 event 发布；该 event 同时是第一份 key/projection witness。commit 后完整 replay readback。
任何 commit/return 不确定性使句柄 poisoned；本单元不提供故障后猜测 head 或自动补写功能。
每次 BEGIN 前先向外部 retain_prepared callback 交付 AppendTicket：store identity、seq、
before 双 heads、kind、完整 canonical event bytes，以及由此唯一计算的 event digest/after 双 heads。
只有收到该 ticket 的准确 digest 确认才允许事务写入。callback 是独立持有者的信任边界；
callback 后再次核对 genesis/header、完整 rows 和 exact ticket；事务直接插入 ticket.event，
提交后 readback 也必须与该同一个 event 逐字段相等。
其确认不证明 fsync、crash durability 或独立介质持久化。调用方负责在确认前独立保留 ticket。
重开提供原 before heads 与该 ticket 时，只接受 DB 精确停在 before 或恰好多出该完整 event 的 after；
其余 suffix、替换 event、错误 store/seq/heads 均拒绝。before 分支重放验证拟追加 event 但不写入。
outcome ticket 的 before 通常已有 bare intent，恢复仍不可自动重试。
Owner 禁止 copy/deepcopy/pickle，公开操作使用立即拒绝重入/并发的 guard。
business.current 仅把四种已定义阈值/表示失败记为 business_input_unresolved 并保存原因；未知 ValueError 传播，保留 intent。

## 科学键与冲突

Request key 在 Rref 输出之前构造，含固定科学合同、relative hour、当前 N/outage/exact source projection、
共同 Rref before、各 lane business/A before 与 halted flags；不含 g、求解输出、raw SHA 或 audit heads。
Projection 则含共同 g/Rref after、每个 lane 的候选业务结果、实际 prescribed power、配对状态及科学 after。

Alternate witness 必须针对已有小时的同一 request key。相同 projection 只追加审计 witness；
不同 projection 永久形成 conflict，保留第一 witness 和已有后续 outcome。
registry head 覆盖每个 event；outcome head 只跟踪完整 outer outcome，两个 token 都必须匹配。
这里 outcome_head 是完整 outcome 的审计 event head，不是纯科学投影链；它可以间接绑定先前 witness。
科学状态/下一小时 request key 独立于该审计链；相同 projection 的额外 witness 不改变科学 carry。
冲突祖先使 continuation_available=false，公开 inspect 不返回任何可执行 carry，
并标记 orphaned_after_conflicted_ancestor。该 registry 的范围仅为当前 owner；不是跨 owner 合法复用 DAG。

## 验收与仍未实现的门禁

要求验证：两小时配对/重开、独立 Rref/A carry、exact debt、失败 intent、actual failure 双侧不推进、
同 projection 不同辅助 flow、不同 projection 的祖先冲突、stale heads、lease、source/manifest drift、
commit 前 source drift、篡改投影重放拒绝，以及显式 archive bounds。
还需补充审查要求的故障窗口与多 lane 覆盖，最终测试状态以 machine-readable development checks 为准。

测试使用 synthetic source/controller seam 和 fabricated solver-shaped records；真实 selector/business replay
保持原数学逻辑。Owner 单元测试对已闭合 numerical modules 的实际 implementation identity
采用测试内缓存；source implementation identity 随 synthetic source seam 替换。
闭合依赖的文件 pins 单独重验，owner 的依赖 identity 漂移拒绝另有定向测试。
这些单元测试
不构成真实 native 执行证明或 RTS integration 证明。raw ingress owner、Job/分段计时、完整 192 小时 producer、
完整 task manifest、跨 owner reuse DAG、同合同 LB/UB、资源准入、successor seal、全新 official review 均另有门禁。
formal_result、formal_execution_ready、resource_admission、native_execution_authenticated 均为 false。
