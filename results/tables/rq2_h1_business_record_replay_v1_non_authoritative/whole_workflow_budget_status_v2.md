# 整链预算后继：排除record数值重放复用点

2026-10-20，DRAFT_NONAUTHORITATIVE。本后继复用[原整链工作量审计](../rq2_h1_phase_boundary_v1_non_authoritative/whole_workflow_budget.md)，没有改变当前owner、科学模型、源、阈值或原执行路径。目标完整168h/≤24h包的wall/RSS/storage准入仍为null，overall_performance_review_complete=false、long_connected_launch_admitted=false。

| 完整DAG部分 | 当前证据与预算状态 |
|---|---|
| genesis/create、每小时ready/post、terminal、重开与public inspect | batch v2完整调用量已列清；192h为1546 Reader observations/149380 prefix-hour，parent inspect3092/298760；不含独立historical/snapshot/anchor |
| 每小时N、Rref/Actual、paired outcome、holder持久化 | 复用3h、7个paired lane-hour的原件；现toy max_events32在第11小时预留分支拒绝，168/192h至少504/576events，不能直接扩跑 |
| history/business重放 | 3条lane始终活跃时，仅ready/post原_validate传入history长度下界28311936（T192）；本次record复用只减少数值求值且总路径更慢，未接线，不改变这个下界 |
| source与normal完整路径 | 已保存3h全部32个Reader observation elapsed合计655.226238s，最大33.282640s；完整双Reader batch最大65.255048s。normal stage wrapper累计412.519432s。它们与其他owner stage存在嵌套，禁止把所有stage合计当作总wall或相加外推 |
| 旧连接成功、缺源停止、收尾和重开 | 非重叠trace从start到reopen_verified合计1254.890731s；pytest1307.07s，外层1314.969s。旧case无真正168h边界/episode terminal；normal内部、serialization、failure窗口和目标规模未具代表性预算 |
| 新业务detached诊断 | 22-case unit和固定4/16/32h原/后继对照已终态；后继各block均慢，保留负结果。0 Job/native，不能代替整链测量 |

优化决策：不采用当前record操作内数值复用。它不能消除history/snapshot重复遍历，也没有完整动态依赖隔离证明。本包不通过减少guard、忽略可变字段或放宽科学门获得提速。

下一项优先核对source/normal路径：沿已保存3h实际调用DAG定位同一public operation内重复N prefix/parent检查，逐一给出外部expected heads、root/terminal/registry/source和implementation的freshness边界，区分合法纯静态复用与必须fresh的动态观测。只有独立DRAFT提出可证明的合法减少方案后，才固定一个必要的保存记录/短诊断包及资源上限；已有32次source观测不因换对话而重跑。当前没有新native校准或长连接launch。

原E=168/F<=24、deadline和恢复债务语义保持。phase-body事实不能代替真实N0→Rref/Actual→paired commit→episode_terminal→close/reopen连接；缺必要followup的typed unresolved/right-censor终结、writer可写重建、persisted atomic-live和crash durability仍开放。预算门、科学门、seal/official review与具体运行授权继续分别处理。
