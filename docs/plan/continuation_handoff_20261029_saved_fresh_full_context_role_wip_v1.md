# F：full-context role 草稿暂停交接

2026-10-29。状态：`DRAFT_NONAUTHORITATIVE`；宽 goal“持续推进”当前为 **paused**。本交接用于切换对话，研究实现、登记和测试继续暂停。完整 F 尚未完成。

## 已完成

1. NFC12 已完成真实同一 LIVE owner 的 binding 消费和资源关闭；其冻结 16 文件及 checkpoint 保持原字节，后续未重跑。
2. 之后完成的局部 producer/bootstrap、Parent40 和 QuietActor2 开发证据，见 [Parent40 检查点交接](continuation_handoff_20261029_saved_fresh_complete_parent_v2.md)。Parent v1 的一次失败和后继 v2 的 23/23 普通测试均保留；这些是局部开发证据。
3. 最后完成并发布的是 [完整工作流成本检查点](continuation_handoff_20261029_saved_fresh_whole_workflow_cost_v1.md)：[静态模型](../../experiments/staged_rts24_saved_fresh_workflow_cost_model_v1.py)、[设计](staged_deliverability_c_saved_fresh_whole_workflow_cost_design_v1.md)、[验证范围](staged_deliverability_c_saved_fresh_whole_workflow_cost_scope_v1.md)及原流/账完成保存，16/16 普通静态测试通过，独立只读 PRE_SEAL findings 已闭合。该包没有 official verdict、review receipt 或 production seal。
4. 上述完成检查点的 Git 提交为 **223e8a31170e76c88cd0635aeb0bf48f12dad62a**。本交接另保存其后的未登记草稿，发布提交用 `git log -1 --format=%H -- docs/plan/continuation_handoff_20261029_saved_fresh_full_context_role_wip_v1.md` 查询。

成本模型的接受范围严格为 `static_source_bound_DAG_and_conditional_arithmetic_only`。它识别了 P1 与 source 两项整链成本缺口；完整 F 的预算准入、真实权限与科学结果均仍未完成。

## 当前草稿与验证状态

草稿：[staged_rts24_saved_fresh_full_context_role_runtime_v1.py](../../experiments/staged_rts24_saved_fresh_full_context_role_runtime_v1.py)。

- 本次暂停保存的原始文件为 **48360 B**，SHA256 **cdfbad787960572c520955bfa8e1187027a2d83d70cf5308050b965ec20ab838**。
- 该版本 **从未登记**；此轮尚未创建对应测试、design、scope、driver 或 result root。按 `full_context|full_role` 命名过滤的可读文件清单未发现配套工件；检查未全面覆盖其他命名及不可读临时目录。未执行语法编译、目标 import 或测试。最后一轮修补也未完成复审。文件名中的 v1 仍是可修改的 provisional draft。
- 本轮没有新的真实项目 Native owner、Source49 目标执行、P1 内容读取、角色、模型或 solver 调用；新增模拟跨度 0h。编辑器 language server 和索引服务为现场观察到的后台进程。
- [交接快照](continuation_handoff_20261029_saved_fresh_full_context_role_wip_state_v1.json)保存该源 pin、原 39 项 dirty 的路径/大小/SHA、预算与门禁。这是交接元数据，不是新的实验登记或账源。

草稿已写入以下机械结构，均等待验证：

- 同一 full context 下的 parent/fresh role binding 和持久 `FullRoleSession`；绑定 context、caller image、owner、源函数元数据、deadline 与实际入口证明的数据结构。
- 互斥操作窗口与固定 CodeType 的窗口执行器：重建读取、一次 launch、quiet 后读取 child 原始输出、retire。
- parent 顺序：重建 replay → G2 提交 → 保持 LIVE 并 suspend → 单次创建 child → quiet → 完整 payload 比较 → 一次晚期 inventory → G3/Parent 独立库存/F.G1 的共同候选 → 关闭。fresh 独立重建并执行自身晚期核验。
- 在 replay、部分 launch、quiet、原始输出与晚期 inventory 返回后保留实际对象或原始字节 pin，再进行验证和阶段提交；失败保留 primary、secondary、已完成物理操作与已提交阶段。
- 单次关闭、精确 registry row、reentry 标志、sticky failure、primitive emergency fallback，以及终态后的大引用释放。

这些结构尚未连接真实来源授权、审计 hook 或原生 launcher/quiet 程序。宏操作计数不能用作 P1 物理读量或资源证明。

### 结构性关闭入口

当前源文件在以下六个内部函数开头无条件抛出 `FullRoleUnavailable`：

| 函数 | 当前行号 |
|---|---:|
| `_invoke` | 137 |
| `_mechanical_binding` | 212 |
| `_cleanup_call` | 445 |
| `_new_session` | 504 |
| `_time` | 527 |
| `_entry` | 535 |

另有 public `bind_full_role` 在第 258 行永久拒绝。它们使当前源无法构造 LIVE role、调用时钟/目标或清理真实 owner；门禁不取决于可填入的 None/bool。

`current()`（第 907 行起）明确报告：

- `external_root_available=false`
- `live_effect_invocation_available=false`
- `actual_entry_factory_implemented=false`
- `actual_audit_hook_integrated=false`
- `source_specific_launcher_and_quiet_binding_available=false`
- `activation_requires_source_successor=true`

恢复时保留这些门禁。若为普通机械测试建立私有 AST 副本，应先限定精确 synthetic fixture 与 stdlib-only 程序，限制副本只能执行合成目标；原文件继续关闭。此测试方案也尚未实现。

### 上轮 PRE_SEAL findings 的处理位置与未决项

先前只读 reviewer 提出八组 must-fix；随后 root 已在草稿写入处理，但 **八组均未通过修补后测试和复审**：

| Finding | 已写入草稿的处理 | 恢复时要核验 |
|---|---|---|
| 私有构造可绕过 authority | 六处无条件内部关闭门禁，public binding 继续拒绝 | 所有可达调用均不能触及真实 owner；私有测试副本限定合成目标 |
| role/context/launch 关联不足 | typed entry binding、receipt/image、闭合 launch 字段和 parent child-template | 数据一致性与真实 argv/channel/role 认证边界 |
| 部分 launch 泄漏、primary 被覆盖 | 先保留 create 返回与原错误，独立 capture_failed，累积 pre-errors | create/capture 各失败窗口只关闭实际 child，并保留原 primary |
| metadata 漂移妨碍清理、关闭 carrier 误判 | 独立 held cleanup packet；识别 Core44 预期 carrier；terminal probe 失败仍 abort/recheck | 原 owner 关闭独立执行；真实 class/helper/global roots 的等价性仍未证明 |
| swallowed reentry 仍可成功 | dispatch 与关闭后检查 pending reentry | callback 吞下递归错误后最终仍拒绝 |
| 物理返回后证据丢失 | 保留 replay/quiet/output/G3 实际结果、raw pins 与 terminal references | JSON、比较、候选提交失败后事实仍可重开 |
| failure publish/registry 错误破坏 sticky | 精确 registry row、failure fingerprint、primitive emergency fallback | registry 漂移和记录构造/发布自身失败的保留性 |
| 动态窗口方法替换先执行 | 隔离 globals 的固定 CodeType 窗口执行器 | 替换类方法不能先获得 effect，窗口转换不越序 |

还要核查 `_close_once` 中“Native runtime 已关闭”与“child/secondary 仍未闭合”的命名和终态关系。当前 cleanup packet 的 globals 浅拷贝尚不构成真实 Native 清理根的等价证明。

## 预算与继承输入

唯一最新完成账源：

[checkpoint.json](../../results/tables/staged_rts24_saved_fresh_whole_workflow_cost_v1_non_authoritative/checkpoint.json)

- **10299 B / SHA256 0ece179a28a3442e9406d1d3c372ea1e27f1376baf5608c734b41aafefc6a11a**
- `accepted=true`、`accounting_complete=true`、`diagnostic_accepted=true`，仅接受前述静态范围。
- root 为 **6 文件 / 835940 B**。原包耗费 **11.247852400003467/40 s**；余量不退款、不转给新包。

| 累计项目 | 已计受控费用（秒） |
|---|---:|
| static | 643.0030709000232 |
| pytest | 366.48897970000326 |
| unittest | 332.2220266999684 |
| 总计 | **1341.7140772999949** |

**52 条不接受记录全部保留。** 新 full-context role WIP 尚无已登记预算，新增受控费用 **0 秒**；新的 40 秒机械验证包仅为待设计方案，尚无 scope 或 driver。交接时的只读文件/哈希检查不执行受控实验阶段，也不改写已有账。

后继必须先继承当前 expanded **1420 inputs / 75167353 B**，加本 root 6 文件扣已重叠 driver 1 文件，得到 **1425 个继承输入**；archive 为 **271 文件 / 31028013 B**。再与实际新 own 集合做精确 union，核完整旧失败、charged/known pins。下一 own 数量尚未冻结，不能先把某个拟定总数当作登记事实。

当前成本模型、测试、设计、scope、registration 和 unit exit 的 SHA 均在本次只读核对中与上一交接相符。此轮没有重新验证全部 1712 次历史 pin 比较；该数字属于上一完成检查点。

Source49 epoch 保持 **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**。NFC12 checkpoint SHA 为 **bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de**。B1–B3、原 P2 七输入及所有旧失败、冻结工件继续保留。

## 完整 F 的目标与成本缺口

恢复时先读 [原 adoption 范围预算](staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)、[invocation 合同](staged_deliverability_c_saved_fresh_invocation_development_contract_v1.md)与最新成本设计，再依赖实际源代码确认：

- parent 与 fresh 各自独立完整 B/C/E，覆盖原 21 个点、5 个 accepted 小时（h=-2..2）、130 CAS；P1 为 683 文件/2950863 B，journal 为 137 文件/427629 B。双侧不得传递重建结果或查询缓存代替独立重建。
- F0 的外部 Host/broker context ACK 先于 controller/capture/release；F1 一次 fresh reservation；F2 inner Job quiet 后才可消费原内容；F3 完整比较、F.G1 与父端候选退出；F4 outer quiet；F5 supervisor 对实际 owner/candidate/full metrics/F.G2 检查；F6 create-only readback、F.G3 和终账。
- 比较完整 19 metrics，加 21 ordinal/role/query/evidence refs、genesis、5 accepted states 与 6 prefix bindings。保持两层 quiet、17 targets、四份 128KiB 记录预留和单一 180s 绝对时钟。
- 保留终态 `missing_input/committed/known`、5 小时、last=2、entries=6、CAS=130、next=3、balance=0、resume=false、coverage=false 与原双 null。

原两侧 E 加四次 F 库存为 P1 11370；独立叠加 LC6 与 Parent 库存时，一个 LC 场景为 14155、两个 LC 为 16257，均超过原 **12500** 帽。两侧各自真实同 owner 持有复用、E final→LC.G2，以及 Parent 晚期 LC.G3 同次读履行 Parent inventory/F.G1，才可能形成合法减少重复读取的方案。

当前草稿考虑让 **两侧实际 session 均保持 LIVE**；若上述同窗口义务共享全部成立，保留每侧 53 expectation 成本时条件算术为 `2*5055+3*683=12159`；仅在真实外部 full context 合法替代每侧 53 成本后才是 `2*5002+3*683=12053`。两者均为待证明条件，未实现预算准入。

source/exe/runtime 原帽 **6500** 也未闭合：未整合的原两侧 4176 路径加一个 LC 与 Parent 严格子集为 **6543+7D**，两个 LC 为 **7719+7D**；另有 source-control、anchor 与其他未知费用。D 为 startup disk 文件数，不是 P1 文件数。这些条件叠加不能作为未来整合实现的绝对下界；必须按真实后继重新计量。

现有 LC6 使用 expectation-only context，要求输出 O 不存在；完整 F 使用已由 broker 发布的 full context，包含 caller_core/caller_sha。两者不能互换。Source49 `check_context` 只核数据 freshness，真实 role 还需绑定实际 entry/argv/channel。Permission1 的全局 hook 禁止 process/write/saved-output 且 sticky deny，不能直接承担新的互斥窗口；真实 Guard2/Permission2、source-specific launcher/quiet、actual-entry factory、profile/exact graph/external anchor 仍需后继实现。

`saved_P1_fresh_process_verified`、`saved_P1_parent_adoption_verified`、`actual_F`、完整性能审查、资源/科学/formal/run gates 当前均为 false。

## 下一步

用户明确恢复后，按以下顺序推进：

1. 读取本交接、上一成本交接、`agent.md` 第 7–9 节；核 Git/process、交接快照、草稿 pin 与最新 checkpoint。root 保持唯一 writer，独立代理只读。
2. 先明确 synthetic-only 副本的 effect 限制，把八组未决 findings 转成可核验条目，检查失败路径与物理结果保留，再编写普通测试、design、scope 与 driver。当前源继续关闭真实 effect。
3. 运行新验证前，固定次数、阶段前置、失败记账、完整输入 union、独立 PRE_SEAL 和上限。首次 register 后冻结全部 own 字节，再依 scope 执行测试和复审；失败原流和费用完整保存，通过独立 successor 修复，不覆盖旧登记。
4. 继续真实 full-context 授权与 Native entry/hook/launcher/quiet 整合，证明同一实际 held owner 的窗口与合法库存复用；把 source 与 P1 成本、昂贵失败和关闭费用纳入完整 DAG。
5. 在具体代码、问题、次数、资源上限与停止条件可审查后，按 `agent.md` 第 9 节准备有界真实诊断包并申请专项运行授权。当前交接和普通开发授权不启动 Native、P1、Source49 目标、长实验或完整 F。NFC12 继续复用既有证据。

## 工作区与本次保存范围

交接开始时 HEAD 为 `223e8a31`，index 为空，工作区是原 **39 项并行 dirty** 加本次 **1 个未登记 WIP 源文件**。原 39 项为 35 tracked + 4 untracked，其字节 pins 全部记录在交接快照。

四个导航 worktree 文件仍包含保留中的 10 月 28 日旧前置段和 1088.9927 秒/39 条旧账：

- `docs/model_spec/blocker_register.md`
- `docs/plan/continuation_handoff_20261022.md`
- `docs/plan/科研项目执行步骤.md`
- `paper/drafts/README.md`

这些原工作区字节继续保留。新对话使用本交接、最新成本 checkpoint 和相应已发布源/证据确定当前 F 状态，不能因旧导航回退累计账。

本次限定保存 **三份文件**：上述未登记 Python 草稿、本交接、交接快照；不改四个导航、不修改任何既有研究源/结果/登记字节。保存的是可恢复草稿，不产生 production seal、review receipt 或运行权限。实际发布 hash 与原 39 项保持情况在本轮最终回复中报告。

## 新对话直接粘贴

> 恢复推进 F，先读 docs/plan/continuation_handoff_20261029_saved_fresh_full_context_role_wip_v1.md 和其交接快照，再核 Git/process。最后完成检查点是 223e8a31 的完整工作流静态成本模型；当前 full-context role v1 是未登记、未测试、修补后未复审的关闭入口草稿。先处理八组 findings 的验证与真实授权/窗口连接，保留累计 1341.7140772999949 秒、52 条不接受记录、1425 个继承输入和原 39 项并行改动。新 WIP 受控费用 0；不重跑 NFC12。真实 Native/P1/Source49 目标及完整 F 仍须具体包和专项授权。
