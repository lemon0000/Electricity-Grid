# C/F：固定64-open前缀已采集，完整import仍待闭合

2026-10-27，DRAFT_NONAUTHORITATIVE。接续[audit census WIP](continuation_handoff_20261027_saved_fresh_audit_census_wip_v1.md)及[终态补充范围](staged_deliverability_c_saved_fresh_audit_census_terminal_scope_v1.md)。本检查点仅接受metadata完整性与有限import诊断；宽goal仍active。root唯一writer，独立代理只读复核，无official verdict/receipt/seal/run authority。

## 已推进到哪里

最初[wire数据WIP](continuation_handoff_20261026_saved_fresh_wire_data_wip.md)中的contract expected-truth根与dependency image语义两项高风险，已在[数据根修复](continuation_handoff_20261026_saved_fresh_wire_data_root_repair.md)规定的声明校验范围闭合；剩余八个data API见[wire completion](continuation_handoff_20261026_saved_fresh_wire_completion.md)。其后已推进到pre-ENTRY持有、真实ENTRY namespace、runtime owner/B_S接线及actual import成本调查。数据对象与有限诊断不授予真实producer、完整runtime或F执行权。

本次完成census后继修复与一次固定前缀诊断。当前BS census4、core19/probe16/parent16为独立后继，Source49未改。四项原finding——计数前核same creator、sentinel严格0→1（含nested replay）、primary不加入自身cause group、精确帧schedule及bucket单调性——已获开发验证；float强持遗漏另行修正。已有14/14单测由AOC4 exact pin复用，新4/4覆盖terminal正反边界、完整fake帧与partial tail、迁移及实际codec。parent15→16只有三处root/version literal迁移，独立raw diff归一相等，旧新pin写入PRE_SEAL。未为机械迁移追加镜像测试。`__kwdefaults__`/`__delattr__`只作静态分类覆盖。

## 所有尝试与费用保留

| 后继 | 已执行终态 | 本scope static / unittest（秒） | 处理 |
|---|---|---:|---|
| AOC1 | register拒绝30049/30000；snapshot已保存 | 1.7074301000029664 / 0 | 已发布冻结，unit/cold 0 |
| AOC2 | size拒绝30013/30000 | 0.45971519999875454 / 0 | 原字节与失败保留，unit/cold 0 |
| AOC3 | size/register通过；14项中13通过、1失败 | 0.9722590000019409 / 5.658402599998226 | 唯一失败为clock的float未进入默认强持根；cold 0 |
| AOC4 | size/register通过；14节点完整运行并通过 | 1.1262846000026911 / 5.798904199997196 | float已强持；cold 0 |
| AOC5 | 新4/4及所有有限阶段通过 | 8.85132899999735 / 1.7885049000033177 | 复用AOC4 exact-pin的14/14，原14未重跑；metadata checkpoint完成 |

AOC2/3/4/5分别为3文件/24172B、10文件/468523B、10文件/471182B、25文件/676543B。各root及已执行输入均冻结；不得原地改源码、覆盖记录或重复调用已完成路由。旧120/540/import8MiB超帽与所有历史失败不变。

AOC5 static帽22s、unit帽3s、总帽25s，已用合计**10.639833900000668s**。实际阶段charge：size 0.5939967999947839、register 0.6622688999996171、unit 1.7885049000033177、PRE_SEAL 0.7583602000013343、startup discovery 1.4833152999999584、profile admission 0.8067809999993187、audit prefix 3.0704693000006955、saved 0.7996796000006725、checkpoint 0.676457900000969。所有阶段accepted，command **29972/30000 UTF16**，root在26文件/4MiB内。

全历史static **231.03523670001164**、pytest **366.48897970000326**、unittest **67.59156209999855**，合计 **665.1157785000134s**；不接受记录 **25条**。本轮未新增意外拒绝；诊断预定的AuditCensusStop不改写成完整import成功。以上为既定capture计费，编辑/审查/Git、Python初始启动及最终JSON写入不计，不是完整wall；无模拟小时推进。新scope余量不是重试或扩张授权。

## 唯一actual import前缀的事实

证据入口为 `results/tables/staged_rts24_saved_fresh_aoc_v5_non_authoritative/checkpoint.json`、`probe_import_discovery.receipt.json`、`saved_report.json`、各exit及原base64 stdout/stderr。PRE_SEAL绑定helper pins和checkpoint脚本pin，checkpoint重开所有前序artifact/input pins，当前payload逐字节（仅注释空格化）、含位置AST与CodeType oracle通过；prefix仅token/AST语义相同，列位置改变，不声称exact prefix CodeType不变。minified prefix就是实际zdict，startup重新发现并准入。

唯一获准的actual adapter import路径（调用上限1次）在固定第64个guard-passed open处主动停止，未观察到adapter return：10帧严格为begin0、progress1/8/16/24/32/40/48/56、prefix_complete64；terminal entered=passed=observed=64、rejected0、diagnostic_error0、inflight=false、active=false。第64物理open未执行，前63个尝试也不宣称I/O完成。所有guard/policy检查顺序和边界维持，census在cleanup前停用；没有watchdog、模型、Highs()/solver、P1或实际F调用。

driver audit阶段 **3.0704693000006955/8s**；其中parent capture **2.2772331000014674/7.487963599996874s**。子进程exit1，primary为`AuditCensusStop: diagnostic_prefix_complete_64`；这是预定诊断停止，child status仍failed、runtime UNRESOLVED、boundary FAULTED，adapter_import_return_observed=false。完整secondary链保留`LocalRuntimeUnresolved → BootstrapImportUnresolved → ValueError(policy_terminal)`未完成原因，import_profile=null、runtime_was_live=false。child self HANDLE各close一次，DLL directory close返回，resource CLOSED；父端HANDLE/pipe/stdin均关闭，reader/writer threads终态，无cleanup错误、kill或截断。stdout4438B、stderr10069B，non-stage residual0B。父端接受的是有限诊断与终态收尾。

末帧snapshot−start为 **0.17515070000081323s**；audit body inclusive累计 **0.05754760002309922s**，其中entry total **0.05621660000178963s**；image digest **0.0284852999902796s**，cache **0.01403599999321159s**，identity **0.0056057999972836114s**，ownership **0.005590799992205575s**。cache从11到20项，新增9。inclusive包含entry，entry又包含各分段，不能相加；剩余时间包含观测/路径等未分解工作，不能当作I/O时间。一次前缀不能推断全import耗时、旧8s超时根因或cold提速。

## 后续第一步与边界

从当前checkpoint、原stdout/stderr和helper pins恢复，先核Git/process。优先用已有前缀对`image_digest`与cache的重复工作提出最小等价性/成本方案，并写清依赖变化、DAG、调用量、有限预算和反例；只有新scope明确准入后，才执行独立后继，不沿本冻结root重跑或直接加大前缀/时间帽。完整B_S profile、OBSERVED/LIVE、actual producer及F仍需独立闭合；不得用prefix64替代完整import证据。

Source49 epoch **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**及49份raw不变。39项并行文稿/图件/文献dirty保留；四导航只提交新增前置段，正文并行修改不纳入本发布。E/U、独立TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false，cache_candidate_adopted=false。目标仍active。
