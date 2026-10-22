# 168h / ≤24h 整链预算审计

2026-10-20，DRAFT_NONAUTHORITATIVE。本轮形成了可复算的整链工作量及启动阻断记录；**整体性能预算仍未闭合，长连接包不准启动**。依据为原执行代码、[机器审计](budget_audit_v1.json)、[审计脚本](../../../experiments/h1_phase_boundary_budget_development_v1.py)、三小时原终态和本轮只读 SHA 核对。这里的 hour 均为模拟时域；没有192h墙钟预测。

## 一个 episode 的实际 DAG

| 阶段 | 真实依赖与重复工作 | 目前可用依据 |
|---|---|---|
| 全 enrollment 输入预验证、registry/config/依赖身份 | 先核完整168h支持；后续只在确有需要时读当小时，不能把未来数组交给策略 | 冻结合同、原 source coverage；current/freshness仍须按原操作执行 |
| fresh normal N0、owner/holder genesis | 原controller只从N0 attach；关闭后的writer不可adopt旧root | 旧hour0/2h/3h主体与current pins复用；不重跑它们取得已有结论 |
| 每小时ready full replay | 读取全部owner/ticket events、全部N prefix、每次旧outcome的Rref/Actual/business | batch v2及原科学transition；业务嵌套历史验证形成更高阶成本 |
| h>0 durable attempt → normal Job | exact expected heads、时钟/obligation/parent terminal及source binding先后固定 | 缺源/Job失败保留原attempt，不能自动重试或补造N |
| 独立current → 共同Rref → 各active Actual | source batch读两次；Rref共用，已completed/halted lane跳过 | 三小时13/11/10 fake captures及原stage inventory；新终结case不能沿用固定34次 |
| intent/ticket → 原transition → paired前独立fresh → outcome/ticket | 原model/数值门/业务预算、完整DB/holder/head及科学等价不减 | 保留callback失败、source drift、未确认ticket和失败incumbent语义 |
| post-paired full replay | 再次重建全部N/source/Rref/Actual/business，非一次增量append | 原v2运行路径，不能只计新增小时solver |
| 额外terminal operation | 无active lane再需下一小时，ready replay、append terminal、post replay | 不启动下一N/selector；技术terminal可含halted U，不能推定科学成功 |
| 外部checkpoint → close → fresh constructor → public inspect | 关闭前留存独立heads/科学对照；constructor自动完整重放，public inspect又一次 | 旧3h提供同进程clean-close证据；不是writer重建/crash认证 |
| 独立historical、parent snapshot、anchor/Job核对及报告 | 还有额外全历史、文件/源SHA、句柄、PID和失败原件检查 | 原3h终态可复用；新时域的时间/内存/存储尚无代表性证据 |

## 精确的条件性调用量

下表固定为原v2一个成功T小时episode、无alternate/recovery ticket、额外terminal一次、fresh reopen constructor和public inspect各一次。lane提前停止会减少部分业务/Actual工作，但源prefix仍由最长活跃lane决定。单一N/Rref/owner链串行执行。

| 工作量 | T=168 | T=170 | T=192 |
|---|---:|---:|---:|
| 成功paired outer outcomes | 168 | 170 | 192 |
| 最低owner/ticket事件（含terminal） | 504 | 510 | 576 |
| Reader observations | 1354 | 1370 | 1546 |
| Reader prefix-hour权重 | 114580 | 117304 | 149380 |
| parent inspect遍历 | 2708 | 2740 | 3092 |
| parent inspect prefix-hour权重 | 229160 | 234608 | 298760 |
| source current materializations | 29234 | 29922 | 38018 |
| 3条lane始终paired/active时，仅ready/post的业务校验历史长度下界 | 18966864 | 19652340 | 28311936 |

Reader=`8T+10`，Reader权重=`4T²+10T+4`。每Reader两次parent inspect。materialization的registry.prepare每current至少两次；这些计数不是全部I/O，不能把独立historical/snapshot/anchor或normal内部遍历漏掉后称总调用量。三小时实际32/64、64/128已从原32条observations重新计数一致；其缺h3分支和显式inspect与本表终结分支不同。

业务下界固定L=3且始终活跃：`2L*Σ[h²+(h+1)²]`，h=0..T-1。单次h-prefix replay中的传入_validate历史长度为每lane `2h²`；cursor自身的完整检查、历史序列化、live branch、terminal和重开还会增加工作。该值是工作量下界，不是wall下界或上界。三小时只有7个paired lane-hour，不能据此声称三条lane全程活跃的实测。

toy normal为5 stages/h；最大三active lane的selector inventory为13/h。T=192时分别为960个fake normal stages和最多2496个fake captures；normal每Job240s、selector每小时13s的额度和分别46080s与2496s，只用于阶段停止额度，不能相加充当整链ETA。真实RTS正常232 stages/h对应44544个normal slots，未由toy测量覆盖。

## 启动阻断与优化次序

1. **资源结构不容纳边界。** 原toy `max_events=32`，10小时后rows=29；再执行一小时需预留四事件，29+4>32，原gate将拒绝。168/192h至少504/576个事件。只增事件数仍不足：单event bytes、DB/holder总量、normal档案、scratch、checkpoint和报告字节都需登记。新包未建立这些上限。
2. **全流程仍有实质重复成本。** source遍历累计二次、业务嵌套历史校验至少三次增长。原batch v2已复用，可继续复用纯静态identity的已验测试设置；未证明可变依赖闭包的跨operation缓存不能采用。先设计versioned operation内业务fold/assessment复用，保留original oracle、外部freshness/head bookends及最终完整审计，再有界对照。
3. **目标整链wall/RSS/storage没有依据。** 旧3h外层1314.969s、sampled RSS403148800B、logical23223898B；single Reader33.283s、完整batch65.255s。不同规模的非线性重复及新terminal/失败路径使其不能线性外推。本表未覆盖的昂贵normal内部、序列化、失败/回调和收尾必须显式补证。
4. **所有边界case的任务/reuse DAG未冻结。** 当前下表是每个episode的成本。成功终结、恢复提前终结、最后due失败及缺必要follow-up source能否共用同一完整N/Rref初态和允许source，需逐case证明；不能在总包中先按一个episode省略成本，也不能从旧三小时root接写至168h。
5. **缺必要follow-up的terminal表示仍OPEN。** 当前v2只有durable pending attempt/poison/重开拒绝重试；不是正式右删失终结。诚实保留U及已有同维度F，不能补未来数据或以terminal替代科学结局。

目标长连接包的 `total_wall_admission_seconds`、peak RSS、总storage保持null；`overall_performance_review_complete=false`、`long_connected_launch_admitted=false`。只有目标调用路径、合法复用、性能瓶颈、完整实测和资源上限都有依据后才重审。完成上述性能门也不替代seal、fresh official review或具体native/正式运行授权。

本轮可独立推进的是原合同下的短业务/phase-body边界核对，结果见[验收矩阵](boundary_acceptance_matrix.md)。它不构造N/Rref/Actual凭据，也不关闭完整192h、writer重建、persisted atomic-live或crash-durability。
