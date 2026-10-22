# C：保存证据后继的有界集成合同

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。本合同仅登记一次无solver开发诊断，遵守agent.md第7–9节和[C总计划](staged_deliverability_c_scope_and_budget_plan_v1.md)。根代理唯一writer，sol_reviewer只读PRE_SEAL；旧B1–B3、C和public build、causal检查点原样保留。公共网络方向不变。

## 问题、规模与准入

问题是：请求构造优化是否保持科学身份；CAS是否无损去重完整网络/父证据；三种方法的五小时执行是否经写入、关闭和fresh进程保存重放得到同一完整state/audit；缺证据、发布前失败和提交未知是否保留正确前缀。实际网络为显式解析三母线/一机组/一selected事故，h1事故、h2投运标志、h0…4观察、登记结束3、晚Y路径。物理网络不随标志改变，不作为公共工程变化结果。

只执行`attempt_01`一次；不重启、扩时或覆盖。三方法各一遍内存baseline、一遍journal、一个fresh child；另reference=None、actual=None、entry rename前/后失败、两步后缺输入各一个case并同进程reopen一次。所有actual与父/child证据为解析手给点，journal/fresh复用baseline，0 solver/native/下载/付费调用。测试矩阵通过、PRE_SEAL findings闭合并核源字节后才能启动。

## 完整DAG及会计

| 顺序 | 实际依赖与工作 |
|---|---|
| 0 | 独占目录/外部watchdog → interpreter/import →当前源码/版本/输入SHA →旧B1–B3及C/build/causal保存核对 |
| 1 | 显式解析Fixture → 三方法各5个旧full编译请求及手给父/child证据 → v2 prepare →固定策略→解析actual→accept →summary/独立audit；保存packet供后继复用 |
| 2 | 相同fixture/packet →genesis/CAS →逐小时begin →actual消费→accept完整前缀重审→额外candidate独立audit→CAS纯编码/预算→write/flush/fsync/publish/readback→采用state→finish检查点/终态 |
| 3 | 外部trusted binding →3个顺序fresh child →导入/版本及源码核验→CAS只读重建→逐小时同样prepare/accept/candidate audit→终态summary/audit→完整state科学/typed SHA与baseline核对→fresh退出 |
| 4 | 五个失败/缺输入case →保存attempt或pending/failure→只读重开裁决→当前未接受输入、旧前缀、永久期限/右删失检查 |
| 5 | 当前/旧字节末端核对→分阶段时间/调用数/存储/子进程报告→completion目录清单→退出→watchdog记录outer/RSS→保存读回/postcheck |

令T=5，R_i=1+I_fault+2I_noninstantaneous。baseline包含summary及末audit，编译数T(T+3)=40/方法，小时权重`2(T-i)+2`。journal每小时另审candidate，finish再summary+audit，编译数`3T(T+1)/2+2T=55/方法`，权重`3(T-i)+2`；fresh相同，终态summary/audit在同操作返回时复用，不再重复。完整prefix、cohort和state hash仍按Σt增长，没有T192预算。

| 路径 | selective编译 | selective列表描述 |
|---|---:|---:|
| 三baseline | 120 | 310 |
| 三journal | 165 | 427 |
| 三fresh | 165 | 427 |
| 五failure含各一次reopen | 50 | 160 |
| 合计 | **500** | **1324** |

五failure分别4/6/6/8/26次，描述12/18/18/24/88。角色总数P0=500、raw=124、恢复min/max各350。外部baseline证据生成另有15次旧full compiler、83描述（normal/F/fault_raw各15，P0=15、reference_raw=3、恢复各10）。计数仅为返回列表描述，未把accept/audit中replace构造的actual预期副本当新query，也不等同于solver或独立样本。解码重新构造PointRequest的验证、state hash、I/O/文件首尾核验、环境扫描、报告成本由完整wall及I/O计数另列。

## 优化决定与未采用项

采用actual子集编译；保留完整合同层单独实现。采用typed CAS去重frame/父证据及同一次ReadView解码缓存，并在同操作末重读所有已用文件/全inventory/目录身份/runtime。仅复用当前已重审terminal的summary/audit返回值。所有额外独立审计和数值阈值保留。

不跨小时缓存依赖或前缀验证；目前没有可证明的增量账本/数值审计合同，先保留完整重审。历史引用列表/state digest仍有O(T²)成本。当前规模顺序执行，避免并发内存、I/O及单writer歧义；无GC或失败目录清理。该解析诊断没有公共矩阵/69事故求解，不能关闭C整体审查。

## 资源与失败收尾

[launcher](../../experiments/staged_rts24_journal_launcher_v1.py)执行[runner](../../experiments/staged_rts24_journal_diagnostic_v1.py)。总wall硬上限180s，30s无事件进展停止；单fresh child45s；进程树采样RSS512MiB、输出64MiB/5000文件，0.2s采样，子进程顺序、最多父+一fresh。预计为几十秒至约两分钟，依据普通临时目录路径观察而非公共性能数据；未知import/I/O/资源尾部由硬停止覆盖，不延时重试。心跳逐小时和每阶段写events；导入和单CAS操作不能保证实时心跳，由外部watchdog停止。

外部watchdog仅终止本次启动的进程树，保存stdout/stderr/launcher终态。任何源漂移、科学不等价、异常超限、child非零或调用计数不闭合均失败并保留原件，后续另用successor合同；不重试当前attempt。writer I/O失败保留CAS orphan/pending和旧state；failure自身写入失败可能没有可重放诊断，必须保持未决。本包不测试真实坏盘/掉电/阻塞I/O或生产耐久性。

记录绑定本轮五src、两runner、两test、本规格/合同、解析helper及实际执行的旧build诊断helper，共13个直接文件；另有genesis所列28仓库源/配置、十个外部入口、Python/版本。启动前记录Git/process；进程只保存PID、名称、argv SHA与仓库相关布尔值，原始参数不落盘。结束时核旧118保存/42repo/7external、旧C三源、build源/核心及旧causal八源/保存记录。completion只绑定静止核心，活跃stdout/watchdog文件另作结束后核验。不生成official receipt、seal或formal结果。

## 验收与下一门

成功case以完整state科学/typed SHA、summary和独立audit与baseline逐值相同为准；三fresh不调用旧编译/证据生成或solver。failure以保存前缀长度、publication_outcome、trusted head/failure、未接受输入及右删失为准。普通针对和相关回归、反例、hash/diff/进程与只读PRE_SEAL完成后保存检查报告。

无论本诊断结果如何，公共数值点/g、normal C/69事故合同层、完整反事实F/X业务时序、长时域成本、native失败收尾和D/E资源准入仍OPEN。此包不授予长实验或native执行权。
