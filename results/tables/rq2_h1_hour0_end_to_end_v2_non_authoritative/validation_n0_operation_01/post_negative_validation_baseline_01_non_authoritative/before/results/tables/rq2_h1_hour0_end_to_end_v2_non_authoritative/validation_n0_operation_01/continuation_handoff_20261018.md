# H1 优化工作交接：2026-10-18

用户要求先完成实质性能优化，再跑真正三 arm → common → Rref → 业务映射 → Actual → paired commit → 全部关闭后重开重放的 hour0 集成。M2 未通过；192h、完整资源/DAG、封存、fresh official review 和正式运行随后推进。真实 native 校准和正式实验没有授权。不要再次用局部测试数量代替整链通过，也不要无预算地重跑长链。

仓库 `D:/CUHKSZ/Research Project/electricity-grid`，Python `D:/Miniconda3/envs/compute/python.exe`。
先按 AGENTS/agent.md、执行计划、blocker 和本交接恢复上下文。主代理唯一 writer，保留 dirty/untracked/failed/unrun 记录。没有 commit/push 请求。工作区 source/文档很多未提交改动，不回滚、不删除。

## 当前进程和保护边界

交接时实测旧 chain07 三个原进程仍在，PID+creation 未变：

- wrapper43640 /1792047790.4886127
- pytest27888 /1792047790.668987
- observer42184 /1792047800.3142161

36 个旧 pinned bytes 交接时全部不变。pins 可从
`fresh_source_reader_plan_04_baseline.json` 的 `old_chain_sha256` 读取。
不停止、重启、恢复或改变它；不对其 active 数据根获取新 share handles。
进程存在不代表进度或通过，重开对话先核 PID+creation、terminal/计时记录，不直接重启。
本轮 source reader 对照和 v2 单元检查均已终态，没有本轮待等待的测量 session。

## 已完成的最新出口

1. `fresh_owned_source_cost_monitor_03/terminal.json`：一次新真实 Bootstrap2 owner、一个合成 Windows N0 Job、登记、关闭，再做一次原 source；outer352.297s/exit0。owner open15.227563s、N0 complete295.572059s、close0.000158s、source17.801640s。没有 common/Parent/Rref/Actual。3 个 owned PID 消失、10锁重获释放、889source/tested copies、171 code paths 写方式重开无写、旧36pins保持。已完成的本任务输入根 `D:/h1_fresh_owned_source_cost_03_non_authoritative` 可按固定计划只读复用；不是旧 active chain07。
2. `parent_common_regression_unit_02`：93 passed、47.02s，outer48.313s/exit0；是 v1 Parent arithmetic witness/common bridge 的 fake transport/arithmetic 回归。
3. `parent_source_scientific_oracle_monitor_03`：outer470.781s/exit0，保存 source 全部 typed fields/decision/audit 相同；host/activation 显式 fake。`parent_source_profile_monitor_03` 严格导入路径后继 source39.006289s（含 profiler），outer50.922s；repo-only path lease。不要回写旧 oracle 的 import-window 证据。
4. reader v3 已停止采用：同输入 original source22.423639→candidate23.217933s，慢3.54%，未达预定5%限。保持 v2，不再调该微观分支。131 reader/monitor 单元通过不改变采用决定。两边12,086次真实 stable reads、科学/audit/全字段相同；134个文件和10锁前后补检通过。复合终态 `fresh_source_reader_pair_postcheck_01_non_authoritative/terminal.json` exit0、decision=`STOP_BRANCH_RETAIN_V2`。两个旧 baseline 失败均在 source prepare 前，candidate未运行；失败/unrun保留。

## 现在正在修的真正瓶颈

原 Handoff4 draft 接入 Parent v1 numerical witness 后，仍静态展开150 Parent validations、4 records rebuild、2408 source prepares、38528 contexts；每 source约18–23s，不能继续靠微观读取 guard 优化。

已新增但**尚未接入 Handoff4**：
`experiments/h1_selector_parent_validation_operation_development_v2.py`。

它在每次 public `validate_bundle`/`validate_pair`/`rebuild` 的同步封闭窗口，入口与出口各执行一次原 source2 公开 `prepare`，完整保留其 source/registry/historical/dispatch guard。窗口内只借用唯一原 `ExactSourceCurrent`；不 deepcopy、不伪造 owned credential，不跨窗口复用。所有 Parent/archive/process/env/executable/sequence/reference 检查保留原函数体的 functional successors。

attach 要求4个 Parent declaration.source_binding逐值一致；每个请求再次核 exact root/pins/registry、原 Parent raw/issued/guard/marks、creator、token、private route。source 全递归 typed signature + exact class-object type vector在各site及tail核对。body/tail错误poison、无fallback；窗口缓存在finally清理；pending只能在全部出口及外层清理完成后commit。

这是**新 validation 身份**：科学输入/目标/阈值/投影不变，但不保持旧2408个逐site source IO观察或首错顺序。规格/receipt必须明确 endpoint freshness、窗口内未观察到的ABA不在证明范围，不能说旧验证身份逐条等价。`complete_dynamic_input_closure_proved=False`、`unobserved_between_bookends_ABA_covered=False` 已明确登记。

条件调用量：13 bundle×160 logical、2 ref pair×16、6 Actual pair×48、4 records×2=2408 logical。25窗口×2=50原完整source kernel calls；全部2408 logical returns借用窗口结果（bookends发生在yield外），因此receipt字段为`borrowed_source_returns=2408`；不要误写2358实际borrowed returns。50 full source对应200 full hour、200 within-prefix、800 contexts。这不是已测全链提速。

针对测试新增 `tests/test_h1_selector_parent_validation_operation_development_v2.py`。
`parent_source_window_v2_unit_01/terminal.json` exit0，**20 passed/9.01s**、outer10.406s；当前v2源未变。测试真实Parent方法code+明确fake host/transport/full source，含所有计数、源字段突变、tail字段/IO失败、body失败、root/pin/对象漂移、wrong pair先拒绝、route漂移、跨线程、caught重入sticky poison、outer abort及nested same-name class type vector。它不是 genuine Parent/Handoff 科学验收。

## 下一步直接做

1. 只读 reviewer `/root/restart_review` 正在审 v2实际字节；若新对话无法复用实例，可按 agent.md §7重新做窄 PRE_SEAL review。其早期“多个Parent必有多个source key”疑虑已用 attach完整相等与逐request检查应对；需明确核对当前实现，不能盲从旧结论。`/root/fast_witness_design` 已静态确认单canonical source方案与计数可行，提醒 owned不支持deepcopy（已修）、nested exact type vector（已加），并明确新的观察合同。所有是 PRE_SEAL，不是 official PASS。
2. 核对 v2剩余finding和测试缺口，补必要故障检查；有变动只重跑受影响窄回归，不重复无关全部测试。通用有界unit runner `run_unit_bounded_v8.py`：label/120秒/768MiB/128MiB/`-- -m pytest ...`，新输出和basetemp必须未用。
3. **接线**：当前 `h1_selector_phase_handoff_development_v4.py` line20仍import Parent helper v1。这是未sealed draft，可以换成v2，更新 `tests/h1_group_selector_integration_helpers_v4.py` 的真实receipt断言（150 validations、2408 logical、50full、800context等），并检查旧 v1专属cleanup AST测试。common/source/preparation/snapshot/Parent predecessor无需改或alias。
4. 用已完成 own-root 的真实 source做一个有界窗口科学/耗时 differential，固定输入/closure/次数/预算，比较全部typed fields，记录真实完整窗口耗时与cleanup；明确fake host范围，不能称 M2。必要时可复用 unit fixture的实际 Parent method-code，但必须标识fake transport，禁止发 live Parent credential。
5. 然后形成具体完整 target的阶段/DAG/预算与停止条件，闭合性能准入后跑真正完整Handoff4。原测试 v4已包含三arm N0→common→Rref/Actual→paired→全部关闭后重开重放；仅collection过，没通过。优先完成这一出口，不继续堆未接通模块。
6. Bootstrap4仍未接入整链（需roster/common transport/genesis successors）；目前维持已连接Bootstrap2，不能称Bootstrap4集成通过。只有代表性证据支持其必要收益时再扩大这个版本图。

## 文档状态

本目录 `performance_report.md` 以及 blocker、M2里程碑、执行计划、Handoff4规格、path performance report 顶部已更新至reader04停止分支与fresh-owned03。v2窗口方案刚实现，**尚未同步为已采用/已接线**，接线和review后再更新，保留旧attempt历史。

所有正式状态仍false；禁止将局部 oracle/unit、旧活进程或PRE_SEAL结论写成M2通过、official PASS或正式实验结果。
