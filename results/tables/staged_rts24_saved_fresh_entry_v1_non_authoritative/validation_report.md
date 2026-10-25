# F ordinary actor 文件入口开发验证

2026-10-25，DRAFT_NONAUTHORITATIVE。起始 HEAD `eb770f276e6b8c3bd0fc293b6deca8a13b933269`；接续[外部调用交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_invocation.md)和[本轮合同](../../../docs/plan/staged_deliverability_c_saved_fresh_entry_development_contract_v1.md)。root 唯一 writer，独立只读 PRE_SEAL，无 official verdict、receipt、seal 或运行授权。

本轮完成 ordinary controller、parent、fresh 的直接文件入口与应用自检，并保留原外部 Job、阶段、发布及完整 quiet/close 路径。实际 saved F 的入口/owner 分支尚未接通；未执行保存 P1 的真实 fresh 或最终科学采用。新增模拟小时为 0，新增 solver/native 求解调用为 0。

## 实现与绑定

三个 ordinary actor 使用 `EXE -B -s ENTRY --ordinary-entry` 和固定角色参数。broker 及独立通用 stage probe 沿用原闭集 `-c` 启动。参数数量、顺序、角色、绝对 context path、SHA、nonce 与 transport 名称严格重建；入口在项目/科学 import 和 stage attach 前核 source/executable/environment、实际 main/file/spec、argv/orig_argv、cwd、flags、search path 与已有项目 module。

初始 script 搜索项经验证后替换为唯一 ROOT；canonical module alias 与同一 `__main__` 对象绑定。后续漂移在下一次受保护 RoleStore 操作或 proof 书挡拒绝。preimport 检查覆盖可观察的 module file 路径及项目/科学 namespace，未声称无 file 元数据的动态代码闭包。proof 写入原 events/return target，明确 `independent_OS_commandline_verified=false`、`full_runtime_closure_verified=false`。同用户主动改写不在此应用自检的认证范围。

ordinary 四个内部 label 在未注入 factory 时使用原 OwnedChild 的私有 subclass。live sample 先保留原 PID/RSS/commit 数据，再按 retained PID/creation/HANDLE 采集一次 image cache；只接受精确 SystemDirectory/conhost。negative/unresolved 保持，terminal 仍需唯一 identity、相同 HANDLE、合法 wait，当前 image 冲突会降为 unresolved。缓存不新增 HANDLE，原 watch、阶段时钟、record 字段及原 guard 保持。分类仍须完整 quiet、all-signaled、active=0 和 close；`observed_at` 是 terminal 分类时刻，记录不能独立证明 live image 的采集时间。

## 检查结果与有限预算

新 successor 开发预算为 pytest 240s、collection/静态保存核验 60s，共 300s；所有 pytest attempt 累计 **236.781s**，包括失败和超时，按各次固定 cap 执行。没有 actor 自动重试或放宽 F 的阶段/输出帽。

| 当前相同三源码 epoch 的终态组 | 节点 | wall s | 结果 |
|---|---:|---:|---|
| console_units_12 | 15 | 4.484 | 通过 |
| file_smoke_13 | 1 | 6.516 | 通过 |
| invocation_units_15 | 27 | 6.515 | 通过 |
| late_payload_16 | 1 | 6.140 | 通过 |
| invocation_graph_17 | 5 | 16.813 | 通过 |
| invocation_edges_18 | 6 | 11.016 | 通过 |
| adapter_19 | 17 | 34.203 | 通过 |

上述 **72 个唯一节点**均有 exit 0、完整原始 stdout/stderr、三源码 snapshot 和 SF49 首尾一致记录。早 epoch 的 file_units_04 54 项和 role_units_06 26 项终态通过，仅记录其冻结源码上的事实，未计入当前 72，也未宣称其在当前 source 上整组重跑通过。

保留两项非通过组：

- role_graph_07：14 pass/1 fail，40.781s。late payload 场景在预期 G3 注入之前因后代分类未决停止；其原输出 15 文件另存。旧记录不能认定该成员为 conhost，也不能反推具体 API 失败原因。
- role_graph_14：45s 组帽触发，含终止等待实际 45.031s；整组未取得终态，**不记通过**。stdout 中 13 个角色图已派生保存，不能替代整组终态。late_payload_16 是随后独立预登记的短测试调用，原超时保持。

原 standalone stage/guard 87 项只在闭集 generic probe/注入 owner 域按冻结记录、AST 和 factory 选择证明复用；不计当前 72，不扩展到改变后的 role/invocation cache 路径。首次复用核验因 guard-test pin 查找位置错误退出 1，原日志保留；修正为读取起始 commit 的 guard test 原字节后，stage_reuse_02 终态通过。旧保存检查在本轮改 canonical 前已通过；本轮保存检查直接核旧 snapshots、输入 pins 与原字节，不以当前 canonical 替代旧 epoch。

正常 external fixture 中，arming 0.219s，outer stage observation 3.297s；嵌套完整成员数为 8/6/4/2，输出 16 文件、38,090B。该小例的采样及输出不构成 F 180s、合计资源或正式准入。5 个新增 entry fault 在 attach/frame 前拒绝的原始图保留，但其所在 role_graph_14 整组仍超时。

35 个 role/invocation 图从原始 stdout 精确派生为 451 个 archive entries，包括 382 个原文件字节与 34 个 context projections；projection 省略 environment，仅保存原 context pin 和 environment SHA，不能作为原 context 消费。cache native 正例仅证明 live conhost 分类、注入 image 查询 OSError 后同 retained identity 的 cache 使用及实际 close/quiet，明确 `stage_success_claimed=false`。实际 live Python 后代负例仍失败并完成完整 quiet。

## 保全与尚未闭合项

1,724 个旧路径、三导航全部旧正文、P1 全 683 文件/2,950,863B、科学 adapter、原 scope-budget、原 guard、SF49 集合、17 targets 和四份 128KiB 记录帽保持。直接 saved CLI 仍 exit 1，真实 F 输出目录未创建。

只读复核未发现必须修复的代码缺陷，以下证据边界仍 OPEN：真实 root 已退出且 conhost 残留时的完整 `_watch_stage` 成功窗口；terminal 当前 image 成功但冲突后 sticky unresolved 的直接分支测试；完整 role 组在当前 epoch 的终态。busy_prestart 检查覆盖了错误 SystemDirectory，不能等同于 image 冲突分支。

真实 saved context 的 owner/entry、完整调用清单、context/四 record 最大合法编码、昂贵失败与发布成本、整链 180s、arming 和 host 最终分配/同步 I/O 的硬中断、整体 wall/RAM/storage 继续 OPEN。kernel image/SystemDirectory API 的调用次数有界不证明调用时间可强制。局部 saved verified、F_launch_admitted、整包 science、resource、formal 和 public P2 全为 false。

恢复入口为[新交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_entry.md)。使用 compute Python 加 `-B` 运行 [saved_checks.py](checks_01/saved_checks.py)；它只检查保存完整性，不能启动或授权真实 F。
