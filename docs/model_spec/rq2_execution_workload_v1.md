# 连续任务清单与调用预留核算

状态：DRAFT_NONAUTHORITATIVE，零solver工具。对应`execution_workload.py`，不接入执行入口、不改变现有budget类型或门槛。

## 输入与核算范围

输入是显式的`NormalWork`与`EpisodeWork`元组。每项有唯一task ID、training/holdout split、normal输入SHA256、完整有序UID清单和连续source-hour清单。normal声明一次求解上限；episode声明reference及network-only、CFE-only、joint-correct、joint-B6四臂各自上限。单位为正整数秒，不接受布尔数、隐含默认预算或无穷预算。

每个episode必须引用已列出的normal任务，split、normal输入身份和UID逐项一致，小时落在该normal窗内。工具检查的是声明之间一致性，不读取真实来源文件，也不证明完整UID表、预测信息时刻、跨场景缓存或normal复用合法。共享normal ID只计一次normal；容量搜索的每个评估、每个窗口及每个holdout评估必须独立列项。重复task ID和未被引用的normal被拒绝。没有默认46次、自动重试、免费预计算或并行加速假设。

对n个UID、H小时，每项episode计reference `H*(n+2)`，每臂actual `H*(n+1)`。各部分分别乘其声明上限后求和；normal生成调用另计。即使某臂可能提前停止，完整路径仍全额预留。输出只声称覆盖调用者列出的清单，`formal_ready=false`、`execution_authorized=false`，固定保留清单完整性、来源/复用、normal最优性、wall/内存/磁盘、真实容量和科学注册等未解项。

## H25来源清单核对

实际来源文件位于`results/tables/rq2_source_pairs_v1_non_authoritative/normal_dynamic_verified_non_authoritative.json`，SHA256为`8c9b58ff3de2f37fecddcc283a1950e91c917a0dd0fc3d4c9025c29af317707d`。其initial.commitment、initial.generation_mw与request.initial_commitment的UID集合一致，共158个；request.timestamps长度25。此来源的初态仍是机制假设。

从这些清单构造单个H25示例、假设normal上限15秒和各selector阶段1秒，工具得到normal 1次、reference 4000次、actual每臂3975次，总计19901次和19915秒solver预留。小时采用该25行输入的0起始行序号。该示例不是已注册任务、建议预算或真实耗时，不据此认为1秒可完成任一阶段。

## 执行接口缺口

本节下表为工具首次交付时的历史接口，不能据此推断当前仍缺selector/episode实现。
2026-09-28已有`scale_selector`、`scale_episode`及显式normal source/worker/controller；
normal短合成完整流程见`rq2_scale_normal_controller_v1.md`。当前保留的inner限制是每个selector
子进程的3600秒wall，而不是episode全窗总时限。实际158 UID下，reference每小时160级、
actual每臂159级；15秒/级分别预留2400/2385秒，22秒/级剩余80/102秒容纳非solver成本，
23秒/级则仅solver预留已超上限。余量不证明构模、审计、归档能在其中完成。
最新零solver清单核算见`rq2_current_workload_inventory_v1.md`；需按实际预算决定是否扩接口。

| 层 | 现有代码约束 | 完整H25路径需要 |
|---|---|---|
| normal | `NormalExecutionBudget`短开发30秒/60秒cap；当前声明15秒 | 有效最优赋值、见证及独立完整任务资源 |
| reference | `_admit`只接受`GridDevelopmentBudget`，max_solver_calls最多20 | 每小时160级 |
| actual | `_admit`只接受同一短开发类型 | 每臂每小时159级 |
| episode | `EpisodeBudget`最多120调用/60秒solver预留 | 19900次，加外部normal成本 |

因此本工具不把算术满足解释为执行准入。下一实施项应是独立于旧短开发类型的真实规模selector/episode资源合同；保留request→L1→完整UID、每级锁定/赋值/残差审计和停止语义。完整wall、内存、归档/回放/磁盘预算以及实际任务清单仍须补齐，不能只提高调用上限后运行。

## 验证

测试以现有`episode_coordinator._requirements`及独立逐阶段枚举核对不等臂预算；覆盖共享normal、逐项容量评估计费、split/输入/UID/小时漂移、重复与缺失依赖、非法预算和连续子窗。独立审查发现同规模不同UID/小时/臂预算可产生相同统计行，已在报告中完整回显normal/episode声明，并新增等总量异输入和声明重建反例。主代理26项测试通过（1.53秒）；独立复跑26项通过（1.48秒），修复复核闭合，限定范围无剩余实质finding。git diff --check通过。没有调用solver、下载数据或产生正式工件。
