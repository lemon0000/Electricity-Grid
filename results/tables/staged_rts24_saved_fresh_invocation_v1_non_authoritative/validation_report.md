# F 外部调用能力普通开发验证

2026-10-25，DRAFT_NONAUTHORITATIVE。起始 HEAD 为 `e83575923318fe09836c09cc164eea722bf2b341`。范围见[开发合同](../../../docs/plan/staged_deliverability_c_saved_fresh_invocation_development_contract_v1.md)，后续见[交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_invocation.md)。本轮实现 ordinary 外部调用层；actual saved F 尚未接通或执行，没有新增模拟小时，solver 调用为零。

host 先建立真实 broker Job/ready capability；invoke 在 START 前固定绝对时钟。broker 在 Job 中创建、独占发布 context，host 依据独立持有的 source/exe/environment/fixture 核 exact context、发布回执与目录身份后 ACK，broker 才构造 controller。controller 接原 parent/fresh 流程及 G0–G3 调用，独立 RAM relay 覆盖最终检查和发布；外层 broker Job 包含全部后代。controller return、broker return 分别在对应实际完整 quiet/close 后读取。Arming 本身仍是外部前置能力，未证明自举硬中断。

## 最终源码与终态

最终 ENTRY SHA `0ab79ed2487be43551bf09c004142fbb1254fc17022dceb6243189da9055f118`；tests SHA `67f926eeb225a305942e1b708d41a683582f51a205447e76d12f4ad985ed64af`。原 scientific adapter SHA `26b919e385f9d7042587db490dab694fc5bf1643665ab4bf94a1c9bac8087396` 保持。

| 最终 epoch 检查 | 唯一 nodeids | 实际 wall / 单组 cap |
|---|---:|---:|
| invocation_units_20 | 27 | 6.187 / 12s |
| invocation_graph_21 | 6 | 19.922 / 25s |
| invocation_edges_22 | 6 | 10.187 / 15s |
| stages_23（含原 guard） | 87 | 16.484 / 25s |
| bootstrap_24 | 1 | 2.750 / 7s |

五组互斥共 **127** 项，均 exit0、未超时、SF49 首尾一致且 snapshot 与当前源码一致。包含所有失败开发 attempt 的 pytest 累计 **220.750s＜240s**；collection、复用、派生和保存核验单列于 60s 静态预算，普通开发总帽 300s。保存清单见 [summary](checks_01/ordinary_check_summary.json)。单组先登记 nodeids/上限，未自动重试 actor、延长阶段或启动 solver。

原 adapter17 历史组在依赖 47 个来源字节、科学 src、bootstrap 函数/常量、顶层 import、disabled main 与对应测试 AST 相同的域内复用。本轮早一 epoch 的 role_units_16 共26项在17.719s内通过；角色定义 AST 相同，shared watch 的唯一后续差异为 invocation 非空时强持监测原错的 guard。两者只作[冻结域证据](checks_01/historical_reuse.json)，不计入当前127。旧 role graph 历史记录保持，未重跑其全部10节点。

## 实际路径与失败事实

| 最终 graph_21 场景 | 外层 stage observation | 终态事实 |
|---|---:|---|
| normal | 3.063s | 唯一 ordinary completion；8个外层成员，controller/parent/fresh 严格嵌套为6/4/2；16个 O 文件共33,846B |
| prepare_wait | 2.984s | prepare phase_limit，完整 quiet，无 context |
| constructor_wait | 3.000s | host 已持 context/ACK；构造函数内 native-wait marker 存在，尚无 controller binding；phase_limit，完整 quiet |
| publication_wait | 4.625s | final_publish phase_limit；pending 保留；杀死持锁 broker 导致 abandoned，强持未决 capability，拒绝返回消费 |
| wrong_ack_nonce | 0.250s | ACK 原错诊断，未构造 controller，完整 quiet |
| wrong_ack_receipt_sha | 0.297s | ACK 原错诊断，未构造 controller，完整 quiet |

故障注入的 Win32 Sleep 为20s，均受更早阶段截止停止；不是 solver 调用。publication 的节点检查通过表示观察到了所要求的拒绝及保留事实；其 `retained_unresolved_capability` snapshot 是异常后的监督者记录，不是函数成功返回。普通 root 的系统 conhost 收尾仅在精确 kernel image、retained PID/creation 满足合同条件时进入原完整 quiet/close；其他后代仍失败。

normal arming 观测为0.234s，另于 invoke 前完成；这不属于上述 stage observation，也不是 arming 硬中断证明。host+broker Job 的采样 RSS 峰为310,071,296B，保守 commit 上界为1,225,879,552B，其中 host lifetime peak pagefile 为1,143,644,160B；嵌套 Job 没有重复加总。最后 mailbox 关闭、完整 payload 试编码后有 resource-only 采样，最终 envelope 编码/保存计入末次 deadline 检查。最终 host 分配的瞬时 RAM/硬中断仍 OPEN，不能把这些观测外推为 F 的资源准入。

edges_22 核 standby 自过期、preflight 跨越 expiry 不发 START、busy 不证明空值、quiet 未知不消费 return，以及 normal/constructor 两种前置资源失败。两种资源失败的外层 primary 和冻结 stage.monitor_error 都是 `ValueError: combined host and owned Job resource limit`；没有消费 broker return。源码强持同一 exception object；日志独立证明错误像一致，不重建对象 identity，也不冻结异常 args/自定义属性。

## 保存与边界

初始 syntax 重复 main guard、busy 被误判 missing、构造故障过早报错、quiet 尚未进入 watch、root exit/conhost 收尾、publication abandoned 及资源 primary 被后发错误覆盖等开发窗口，其原始日志和已测试 snapshot 全部保留。早一 epoch 即使节点 exit0，也不替代最终 epoch；edges_15 的 resource-primary 缺口在最终 edges_22 修复后单独闭合。一次 regression caps 总和超出剩余预算的登记被拒绝，dependent helper 也未启动 pytest；随后按剩余预算重新登记。

[原始派生 oracle](checks_01/verify_invocation_derivation.py)从所有相关 stdout 原字节产生31图、205个 archive entries：149个原文件字节、25份 context projection、31份 result/监督者事实。projection 省略 environment，仅保留原 context pin 与 environment SHA，不能消费或重建原 context。CLI 实际 exit1，保存输入/源码的机械核验不授予采用或执行权限。

1315条旧路径、三导航全部旧 body、P1 全683文件/2,950,863B、原 scope/budget 与47个未变来源保持；SF49未扩大，原17 targets/5,537,792B总预留、四记录各128KiB/原8MiB与64文件帽保持。独立 PRE_SEAL 仅给非正式 findings，无 official verdict、receipt、seal。

仍开放：actual saved context 的 parent/fresh/最终父端完整入口与一次真实 F；完整调用计数、最大合法 record/context 编码及成功/昂贵失败成本；180s整体、arming/host 最终分配与发布硬中断；整包科学采用、资源准入、完整319/139/F-X、C整体、D/E现实输入/有限比较/敏感性/留出与正式门禁。`F_launch_admitted`、两局部 saved verified、science/resource/formal 全部 false。
