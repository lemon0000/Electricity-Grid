# H1 hour-0 完整集成与 bounded verifier 路由

状态：DRAFT_NONAUTHORITATIVE。完整链以本单元保存的 terminal 与集成报告为准。
本规格不关闭 formal/resource/native gate；科学合同及旧实现、封存配置、失败记录保持原字节。

## 实现边界

静态 successor 清单位于
`results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/successor_origin.json`。
13 个文件的边界由既有 exact-type、局部 import 和 worker launch 路径决定：
manifest、bootstrap、owned bootstrap controller、roster、common binding、common genesis；
selector snapshot、released worker、Job lifecycle、output inspection、launch preparation、parent、handoff。
每个 successor 使用自己的模块/schema/file identity；closed predecessor 不改动。
source、historical、业务、phase owner、ticket holder、selector 数学模型与重放继续复用原实现。

两项行为改动：

1. v2 manifest 对请求的真实 family/ordinal 调用已审查的 bounded verifier，保留原 group 的
   完整科学投影和 identity。以原 proof 再独立投影比较，并在返回前再次完整 fresh verifier
   调用，比较完整 envelope。audit 中保留完整 group、verifier implementation、计数与 flags；
   dependency inventory 通过 canonical SHA256 绑定，避免在每个有上限的 journal header 内
   重复千条路径。group SHA 也单独保留，能够从 audit 独立复算。既有大小上限不变。
2. v2 bootstrap 每个原有 fingerprint 边界使用 fresh bounded verifier。ordinal 0 仅用于获得
   dependency closure，与候选实际 ordinal 无关。候选仍通过 manifest 按真实 ordinal 构造，
   并比较 group implementation、manifest implementation、verifier implementation 和
   dependency inventory SHA。verifier 的 dispatch scope 在入口和返回再次检查。

没有跨 operation 的新缓存，也没有全局替换 reader。原 bootstrap 自带的候选缓存仍受每次
fresh fingerprint 约束。完整 common 的两轮 source/registry/historical/current 重建和
所有 durable journal 读取保留。

## 合成整链及计时

入口：`tests/test_h1_hour0_end_to_end_development_v2.py`。
该入口复用原先未完成的三 arm fixture，明确转接测试 fixture 的 module globals 到 v2；
这些替身只位于测试层。三条独立 N0 使用 bounded Windows Jobs，子进程先安装 native denial，
再用保存的合成 reports 与明确的 fake direct objects。每条 Job 都必须 exit0、whole-job
quiescent，捕获的 cleanup lease stream 必须释放。

selector helper 运行 Rref 的三个 stage 和三个 Actual 各两个 stage，共九个 fabricated
adapter 实例。source/workload/outage 为显式合成输入；独立解析 oracle 为零 workload、
无事故、G1 供固定 20 MW demand，Rref locks `(0,0,20)`，Actual locks `(0,20)`。
每条 Actual 缺失均须被拒绝；成功分支检查完整 takeover packet、五个外部 retention
transitions、holder tickets、paired SQLite rows、projection 和 after carry。

全部原 owner 关闭后，从保存的 holder head 和 phase heads 重开 holder/phase owner，
从保存 records 重放，比较完整 projection、state.scientific、tickets、heads，并拒绝任何
新增 retention。bootstrap/roster/common 也独立重开并比对原 common report。

`timing.jsonl` 按连续 monotonic intervals 记录 setup、逐 arm open/N0/roster/close、common、
Rref、逐 Actual、缺 Actual 拒绝、paired commit/readback、重开重放和报告保存。
terminal 记录整个 pytest subprocess wall time；collection/其余 teardown 是与 interval 总和
之间的剩余项。失败尝试照常保留已完成分段，不给缺失阶段填零或推算成功。

selector fixture 仍沿用已披露的 immutable implementation-identity bookend cache；
完整测试还为 bootstrap 与 declared Gurobi adapter 的纯代码 identity 设置入口/出口
bookend cache，并保存原函数、入口/出口 SHA 与实际调用次数；作用域内瞬时代码/包版本
ABA 不在本集成测试的覆盖内。安装前要求 handoff/helper 尚未导入，恢复发生在全部
consume/reopen 结束后，避免破坏既有 callable identity guard。子进程不继承该缓存。
phase dependency fingerprint/manifest verifier 在完整链中不做测试缓存。
synthetic lifecycle 不是 canonical selector Job，合成 wall time 不是真实 native 校准、
正式非 solver overhead 或资源准入上限。未覆盖的 ABA 与 Python reflection 限制沿用各前身。

补充入口 `tests/h1_hour0_saved_replay_v2.py` 在独立进程中读取已完成整链的
`takeover_packet.json` 和 retained report，并按其 hash 重建 manifest、binding、tickets。
它仅恢复同一显式合成 source/registry fixture，禁止 solver 和新增 retention，再读取
holder/SQLite 保存记录并比较 carry、projection 与 heads。该补测也须实际完成后才能计入验收。

## 验收与后续边界

除完整成功链之外，需要范围相称的 cross-generation type refusal、真实 ordinal 投影一致性、
fingerprint drift、retention/commit failure 和 predecessor hash 检查，以及独立只读 PRE_SEAL
审查。仅局部检查通过不能把本单元标注为整链已通过。

hour1+/完整 192h producer、事故延续/修复、非零恢复债务的整链覆盖、typed failed Actual、
实际 task/reuse DAG、同合同 LB/UB、完整资源准入、封存与全新 official review 仍各自需要证据。
新的真实 native 校准必须先提交具体包、次数、预算和验收问题并取得专项授权；旧 v3 授权不复用。

## 运行中定位到的重复验证放大

2026-10-13 的 `chain_02` 在 6123.6224825 s 到达第三个 arm 的 roster attach；
此时三个独立 N0 已完成，完整 common、selector、paired commit 和重开验收尚未完成。
这个 checkpoint 不是整链成功。运行日志仍以实际 terminal 为最终状态依据。

独立只读 PRE_SEAL 调用图检查发现：三 arm 已齐时，单次
`h1_group_n0_common_input_binding_development_v2._prepare_locked` 至少展开
30 次 `historical.prepare`、60 轮 prefix replay 和 156 次 dependency verifier 扫描。
从第三次 attach 后到成功 handoff 的当前测试路径至少调用 68 次完整 common prepare，
对应至少 2040 次 historical prepare、4080 轮 prefix replay 和 10608 次 verifier 扫描。
这些是静态调用下界，不能换算成未经观测的墙钟预算。

因此 bounded verifier 的接入并未消除 downstream 的重复科学重建。
若实测证实它阻塞整链，后续修复必须直接面向这一链路：在同一组 guard 持有期间，
研究以完整输入 witness 做精确 fresh revalidation，并在操作入口和最终交接仍保留全量重建。
这只是待验证方向，当前实现没有该 witness 或新缓存；不得提前声称性能问题已闭合。
任何此类修复都须证明完整输入 closure、fast/full 等价、逐类输入漂移 fail-closed，
并禁止 witness 跨 lock release、close 或 reopen 使用。

2026-10-14：用户选择先做保持原合同的校验优化再重跑。对保存 N0 的独立只读剖析
`historical_profile_04` 已 exit 0，369 个保存文件前后 SHA256 一致；一次 prepare 实际有
8 次完整 Job 数值审计。该次带 profiler，且未启用主链 identity bookend cache，不能作为资源预算。
优化边界见 `rq2_h1_hour0_validation_optimization_design_v1.md`：旧 timed Job 规格要求
每次 restore 完整重放，省略重复数值审计需要明确的新验证合同与等价证据。
用户随后要求继续开发；已在未封存 draft 接入单个 prefix/Reader 范围的 witness，新 envelope 和 N0 terminal 单独绑定 verifier identity 与 4 次完整重算/4 次 byte-context revalidation。原 v1 和 src 不改，chain_02 仍为中断诊断。

`witness_profile_04` 终态 exit0，33.5170197s；`witness_equivalence_03.json` 证明当前候选与 predecessor 的 decision/audit exact-byte 相等，实际完整 hour.inspect 为 4 次，369 个工件 hashes 不变。`witness_routing_02` 的 62 项 witness 检查全部通过；另有一个接线测试的作用域 NameError，修复后 `witness_routing_03` 的 9 项 routing 全部通过，固定字节前后相同。`witness_routing_01` 测试期间接线文件发生追加修改，不能作为最终候选 byte-pinned 证据。所有失败尝试保留。

新完整链仍须独立取得终态；局部等价不证明端到端加速比例。第三方任意反射和不可观察 ABA 不在动态闭包证明范围，机器记录维持 `complete_dynamic_input_closure_proved=false`。

## 2026-10-14：零负载 Rref oracle 修复

`chain_04` 在 common/genesis、reference snapshot 和 Rref parent 返回后，因测试 oracle 的
首个 lock hex 预期错误而 exit 1，总墙钟 28600.9704561s。canonical selector 的首目标为
`B-P_ref`；本例 B=0，实际模型表达式化为 `-P_ref`，重算得到 `-0.0`。selector 合同保留
重算值的原始 `float.hex()`，不使用 N0 `H1StageRequest` 的另一套负零拒绝规则。

仅修正 v2 helper 的 `ZERO_WORKLOAD_REFERENCE_LOCKS=(-0.,0.,20.)`，继续严格比较 hex。
生产模型、replay、阈值和已保存记录保持原字节。新测试以真实 origin model/capture/replay
和 fabricated SolverResults 在小例中复现：旧预期 1 failed/3 passed；修复后 4 passed，
pytest 22.97s，exit0、before/after pins 相同；Rref/Actual 两种零符号的篡改仍被拒绝。
独立只读 PRE_SEAL 复核未发现剩余修复问题；不构成 official verdict。

`signed_zero_repair_01.json` 绑定修复字节、保存 Rref terminal 与前后验证记录。
`chain_04/artifact_inventory.json` 对 461 个失败工件逐 hash 归档，原目录保留。
完整 hour-0 出口仍 OPEN，须用新目录完成 Actual、paired commit 和重开重放。
