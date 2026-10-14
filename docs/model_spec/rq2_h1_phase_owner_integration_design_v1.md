# H1 phase owner / N producer 接线设计

2026-10-09，DRAFT_NONAUTHORITATIVE，设计定位；尚未实现、验证或封存。
基于现有 persistent_owner、finite_followup_assessment 与独立只读设计核查。
本文件不改变科学合同，也不提供执行权限。

## 所需调用顺序

后继 owner 的 run_next 从入口到返回持续持有唯一 operation guard；锁序固定为 owner →
obligation controller → clock → parent，controller 的回调不能重新获取 owner lock。
在持久数据库逐条重放后核对外部留存的 outcome/registry 双 heads，检查 pending/conflict/terminal，
只从内部重放得到的 business carry 重新计算所有 active lane 的 followup need。

无需下一小时：追加 episode terminal，绑定 hour、state、双 heads 与各 lane assessment；不读取下一
source row、不创建下一 clock/job 目录，不把192h底层 parent 的 ready prefix 写成 complete。
仍需下一小时：先追加 pre-N attempt intent，再调用 controller；N terminal 被核实后才进行当前小时
source join、Rref → business → A → paired outcome；最后再重放完整 owner 记录确认返回状态。

pre-N attempt intent 必須包括 hour/phase、before 双 heads、owner state、active lane carry/assessment
identities、need digest、相同 family/ordinal/obligation，以及 controller parent/clock predecessor。
它不得依赖尚未生产的当前 N，也不得读取当前或未来 source row 以决定是否需要这一小时。
当前旧 intent 含 N terminal 与 saved records，必须保留历史语义；后继不能冒充已经覆盖 pre-N 窗口。

## 接口与凭据边界

允许 owner 向 controller 提供仅在本次 guard 内有效的一次性闭包，以避免循环 import。
闭包需核对 owner/process/thread、implementation、rows、heads、pre-N intent、hour/phase 和 controller
predecessor；controller 需在任何 source 读取、headroom 或 intent 写入前调用并复核交叉引用。
其结果及 owner intent identity 进入 controller 的持久记录和返回 observation。

**尚待实现并审查的关键点：**任意调用方传入的 callback、字符串 digest、布尔值、Assessment 或
Python 类型本身都不能成为认证凭据。controller 与 live owner 的附着关系、一次性有效期、失效和
重复调用拒绝必须由受控实现建立并测试。不能只检查“callback返回了预期字符串”便声称 authenticated。
开发回调、真实 native ingress 与正式运行授权仍是不同边界。

## 状态与停止

每 lane 持久状态使用 active / completed / halted_unresolved。active business clock 必须等于共同
outer clock；completed/halted carry 可以更早停止，之后 business 和 A 必须同时保持原值。
paired commit 后重新评估 primary cohorts；完整 E 后无需下一小时即转 completed。
business/A 未决转 halted_unresolved，保留该 lane 的 before carry。其他合法 lane 可同小时提交。
只对本小时合法执行的 active lanes 使用共同 Rref；停止 lane 必须提供空 actual records。
不能因一个 primary cohort 已失败而忽略另一个 pending cohort。

新 N chain 从 genesis 声明192h；168/169边界沿用相同 source origin、family、ordinal、obligation、
budget、parent/clock predecessors、N/Rref/business/A carry，不重置债务或新增预算。
旧168h root只作为历史证据保留。当前 binding 仍只覆盖 training_ub；其他已登记家族不可删去或借名替代。

owner genesis 依赖第一个 accepted N hour，因此 hour0 enrollment bootstrap 必须单独记录与绑定。
其 terminal 固定后 owner 消费 hour0；hour1 起必须经 live need gate。该特例不能推广到任意后续小时。
bootstrap失败保留失败 N root，不创建或虚构成功 owner，不自动重试。

## 故障窗口与验收反例

- stale heads、pending/conflict、错误 phase/hour：在 pre-N intent 与 source 读取前拒绝。
- pre-N intent 后 N 失败：不得自动重试；确定失败与提交未知必须分别记录，未知保持 pending。
- N 成功但 owner 交叉引用错误或 Rref/A producer 异常：停止，保留已推进 N 与未推进 paired carry。
- source 必需但缺失或映射未决：只在 need 已确定后分类；保留 carry 和已知请求分项，记录受影响右删失。
  不把任意 ValueError 都当作来源缺失，不读取更远未来或跨 split 补行。
- outcome/terminal 写后确认模糊：沿用外部留存 AppendTicket 的 exact-before/exact-after 恢复；不重新执行 producer。
- completed lane 出现 records、carry变化或重新 active：重放拒绝。
- global need=false 后仍读 source、创建 clock/job 或调用 producer：必须由故障注入测试证明拒绝。
- guard退出后重用回调、伪造回调、重复回调或 controller 绕过 owner：必须拒绝。
- episode terminal 后的任何 suffix：拒绝并保留原记录；不得自动清理。

完整接线仍须真实 accepted root 集成、192h phase/producer 覆盖、raw ingress、Job/完整计时、资源准入、
全部任务家族与合法 reuse DAG、同合同 LB/UB、successor seal、全新 official reviewer 及具体 native 授权。
本设计不关闭上述门禁。

## 2026-10-09 追加：prepared-before 与写入容量

独立设计核查、根代码核对及零 solver probe 确认：旧 saved-record owner 在外部已留存 intent ticket、
SQLite 尚未提交该 intent 时，重开无论显式提供 ticket 还是省略 ticket，都会报告 pending_intent=false、
continuation_available=true。诊断位于 phase_binding 单元的 test_prepared_before_recovery_probe.py 与
prepared_before_recovery_probe_02.json（2 passed / 5.73s / exit0，仅复现现状，不是修复通过）。
最初因 tests import path 缺失的 collection error 原样保留。
旧 owner 仍只是 saved-record API，构造函数没有自动写入或启动 producer；不能据此宣称已经重复 native。
但后继 run_next 不能直接采用该 continuation：必须进入 recovery_required 并拒绝 producer。

后继需向独立 ticket holder 查询 store identity / before heads 对应的未决准备记录；省略 recovery_ticket
不能被当成“没有未决写入”。存在 exact-before ticket 时禁止重新生产；exact-after 只能采用那一个已提交
event。该 holder 本身的查询、持久保留与独立性仍需具体实现和验证，普通 callback 不是 crash durability 证明。

新 event kinds 必须统一进入 recovery、_rows、_append 的前置白名单，_restore 用显式状态机处理。
只有 paired outcome 推进 outcome head；attempt、intent、witness、episode terminal 只推进 registry head。
terminal 后禁止 suffix；pending attempt 后不得再接第二个 attempt。

若保留旧 science intent，每小时成功路径为 attempt + intent + outcome，192h 至少576个 events，
另需 terminal 与显式 witness 预算。调用 N 前必须为整条成功或失败分支预留 event 数与 canonical body
字节；仅容得下 attempt 不足以准入。SQLite/索引/文件系统开销还需单独资源预算，不能用 body 合计替代。
该恢复与容量 gate 是下一 owner successor 的优先验收项，当前仍未闭合。
