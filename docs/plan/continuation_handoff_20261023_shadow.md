# C逐调用shadow失败诊断交接

2026-10-23，DRAFT_NONAUTHORITATIVE。目标“推进计划”继续active。接续[plain原型](continuation_handoff_20261023_plain.md)，上一已推送检查点`bd473c907f0d3d8c8bf2a1abd1a91d88eb8dc614`；同期共享论文介绍修订保持。当前本包Git结果以交接后的远端readback与worktree为准。

本轮固定[合同](staged_deliverability_c_shadow_replay_contract_v1.md)、完整DAG/调用量和预算，完成[driver](../../experiments/staged_rts24_shadow_replay_v1.py)、[code级monitor](../../src/staged_rts24_shadow_monitor_v1.py)、[runtime绑定](../../src/staged_rts24_shadow_runtime_v1.py)，并执行唯一保存P1只读诊断。详见[报告](../../results/tables/staged_rts24_shadow_replay_v1_non_authoritative/validation_report.md)。

## 已完成和结论

52项绑定普通检查（9.52s）、57项相关回归（15.41s）及1项失败后保存域回归（2.77s）exit0。PRE_SEAL领域/对抗复审无剩余High/Medium。修复了foreign tool/profile/trace书挡、应用模块实际路径与仓库绑定、父端quiet后实际runtime复核；35个仓库模块/包、20类和211个加载标准库模块身份显式登记。该审阅没有official receipt或运行授权效力。

唯一`shadow_01`：命令exit1，worker exit2/`child_exit_nonzero`，命令wall17.095632s、Job14.313s，RSS151719936B、commit123138048B；2/2 HANDLE归零，active0，未超60s/512MiB。原reopen主体返回后，strict_unsupported使monitor完整性门拒绝；终态8文件284978B。未重试，不得覆盖或改绑定字节。

固定2547次全严格等价命题未建立。最后保存进度2432；没有最终counter、caller或类型。runtime_after/shadow/report/postquiet缺失，后续metrics/runtime/source书挡未执行；不得称本attempt科学metrics相等、monitor_cleaned或其余调用全部等价。quiet是真，采用失败来自非零退出，泛化错误文案不能解释为quiet失败。

确定的保存域反例是child reduction的整数键`generation_bounds`。旧plain转字符串键，严格_walk拒绝；保存ChildLpEvidence对reduction仅保存reduction_sha，未保存临时generation_bounds映射，临时映射不在先前保存根检查中。新[单query回归](../../tests/test_staged_rts24_shadow_saved_domain_v1.py)读取原point_0002，核reduction SHA匹配、strict拒绝和公开helper根级fallback保持旧bytes。它不是本次首caller的直接观察，也不证明unsupported总数为118。

独立[stdlib-only后核验](../../results/tables/staged_rts24_shadow_replay_v1_non_authoritative/postcheck_01/postcheck.py)exit0：50个attempt源、原P1683文件/2950863B、B1–B3保存118文件、685旧路径及前两轮68路径保持；原P1/保存profile的旧postcheck输出精确复现。原科学终态仍missing_input、coveragefalse与双null，五模拟小时不表示完整观察结局。保留units_02/03/07失败日志。

## 后继范围与停止线

下一实质工作是依据已保存的整数键反例定义版本化后继：明确strict与fallback输入域、逐调用分类计数、旧bytes/SHA比较及失败时保存最小诊断信息；先完成静态/单query回归与完整DAG/预算，再谈一次新的保存诊断。当前attempt次数已用，不能在同路径重试、放宽计数/域或调整预算。候选尚未驱动旧科研验收，writer/native未接线；不要将instrumented wall作提速。

主网络仍RTS-24公共方向，两母线机制回归。C整体性能、规模/昂贵失败、139/F-X完整时序及D/E业务/设备/工程数值、D/选择/平局/敏感性/时域和留出来源/split/seed/reveal未闭合。原P1唯一native专项授权已用；没有新native/P2/D/E或长实验权限。

恢复时读AGENTS、agent第7–9节、本页、C计划与blocker并刷新Git/进程。root唯一writer，子代理只读且不分叉。复用保存证据，保留全部失败/冻结工件；后续发布按精确NUL路径清单、raw bytes/index核验、远端hash及clean worktree确认。
