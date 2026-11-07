## 审查方：独立只读实例，未参与敏感性包及本记录任何写入

我声明未参与 `experiments/staged_deliverability_d_sensitivity_v1.py`、其测试与 `attempt_05` 任何字节的写入；本审查只读，未修改任何文件，未启动正式实验，未新建或删除 attempt 目录。全部重算在系统临时目录的一次性脚本内完成。

## 审查日期

2026-11-06

## 审查对象（实测哈希与行数）

| 文件 | SHA-256 | 行数 |
|---|---|---:|
| `experiments/staged_deliverability_d_sensitivity_v1.py` | `a99f2ad036e2d1cb4a372029e133d6637dc379a664545fc96813f70ff4835304` | 268 |
| `src/staged_deliverability_d_grid_v1.py` | `d53111ac194dd739bee7b2b7b560e1914d1059f864bdd4359ea110de6471c5a0` | 259 |
| `src/staged_deliverability_replay_v1.py` | `f9738c82308d2379e98e1c46318ff2198e7900fbc9d368e41176db75fd603c7c` | 259 |
| `src/staged_deliverability_development_v1.py`（冻结基准） | `91bbc6aaaac458c8fcb23c11d830a98af99e1d50d42b3c0489246ec1922109e0` | 440 |
| `results/.../d_sensitivity_v1_non_authoritative/attempt_05/report.json` | `fb2ffd8a9c9d140dd6f6f71a3fa73076f33610761fa1f44ff06f0b8705090df4` | — |
| `tests/test_staged_deliverability_d_sensitivity_v1.py` | `5ead774b58de8e160081199f13226e348e516c6f50dfe19d8520b232c1c05de0` | — |

哈希核对：**一致**，六项全符。

---

## 逐点判定

| 审查点 | 判定 | 依据 |
|---|---|---|
| 一 可行性筛时序 | PASS（有测试缺口） | 筛在 `:155` 调用、`run_matrix` 在 `:156`；筛函数 `:100-136` 只读 `cfg`，不接触任何结果 |
| 二 `cfe_binding_hours` 仅作提示 | PASS | 仅在 `:175` 写入 combo；`aggregate` 与 report 组装均不引用 |
| 三 27 组真实执行 | PASS | 648 行、键唯一、无跳过；27 fixture 逐 hash 复核；重跑 648 × 16 字段零差异 |
| 四 115 单元分解 | PASS | 交叉表 278/137/118/115 重算一致；31 全带码、84 全无码且 84/84 期限未完成量相同 |
| 五 正文可引用强度 | **REWORK** | 6.3 草稿两处表述会让读者高估本包的证据地位 |

**总判定：REWORK（实现与结果全部 PASS，修复集只在正文引用层）**

---

## 一、可行性筛时序 —— PASS

`feasibility_screen(cfg)` 在 `experiments/staged_deliverability_d_sensitivity_v1.py:155` 调用，`run_matrix(path)` 在 `:156`，**先于任何结果读取**。该函数（`:100-136`）只读 `cfg` 的 `business_paths`/`equipment`/`parameters`/`clean_paths`，不接触 `rows`/`summary`/`combos`。

`infeasible` 的唯一来源是 `:119` 的 `total_k < post_ramp`；`cfe_binding`（`:128-135`）另置一路。

**不排除任何组合的证据**：`:162` `all_rows.extend(rows)` 无条件执行、`:163` combo 无条件 append；`aggregate`（`:180-215`）无任何按 `structurally_infeasible` 过滤的分支。27 个 combo 的 `evaluations` 全为 24，`structurally_infeasible` 全为 `False`；648 行 `structurally_infeasible` 全为 `False`，无行缺失。最紧的 `K_total` 为 `4/5 ≥ 7/10`。

**测试覆盖缺口（非阻断）**：`tests/test_staged_deliverability_d_sensitivity_v1.py:88-98` 只断言筛返回空，未钉住"筛先于评估调用"与"`infeasible=True` 不触发过滤"两条属性。当前代码正确，但改坏时测试不会报警。

## 二、`cfe_binding_hours` 仅作提示 —— PASS

`cfe_binding_hours` 仅在 `:175` 写入 combo 供人读表；`aggregate`（`:180-215`）从不读取，`main` 的 report 组装（`:233-251`）也无引用。`experiments/` 与 `src/` 中不存在 `cfe_binding` 参与筛选的分支。

**未回退 attempt_04 的口径**：attempt_04 的 combo 里根本没有 `cfe_binding_hours` 字段，取而代之 `degenerate` / `degenerate_reasons`；18 组标记全部形如 `hour 1: CFE demand … exceeds available 1/2`（不延期假设）。其中 `f=1/5, α=4/5` 三档在 attempt_04 自身矩阵里 D1 为 0/0/0——标记与其自身结果矛盾，正是过度标记的实证。

**attempt_04 矩阵保留完好**：29 文件 / 760,690 字节 / 27 组 / 648 行；648 个 `(variant, trajectory)` 键与 attempt_05 完全相同，27 个 fixture 的 sha256 集合逐个相等，648 单元标签逐一致。

## 三、27 组真实执行 —— PASS

648 行 = 27 variant × 24 单元，`(variant, business, plan, clean, method)` 唯一，0 重复 0 缺失，每 variant 齐 24 单元；`hours` 全为 10。

27 个 fixture 在盘，`pin` 三元组（path/bytes/sha256）逐个复核，0 不符，27 个 sha256 互异。`base_fixture` pin 与 `report.sha256` 旁证均对。

**更强证据**：用当前源码对 27 个 fixture 重跑 `run_matrix`，648 单元 × 16 字段（标签、三个定值、停止/覆盖、违约元组等）与 `report.json` **逐字段零差异**；`aggregate` 重算与 summary 全项相等（27/23/233/118/11/0/False/False，无假通过名单一字不差）。另计 6,210 条原生 step 记录（27 × 230），无静默跳过。

## 四、115 单元分解 —— PASS

交叉表独立重算 **278 / 137 / 118 / 115**，合计 648。115 = `fixed_headroom` 31 + `instantaneous` 84，无第三方法。

**31 个固定余量单元**：全部且仅在物理小时 2 出现违约码，`recovery_headroom` 31、`hourly_cfe` 19、`scalar_supply` 12。注意这是**包含关系而非并列 62**：38 行为 `{recovery_headroom, scalar_supply}`、23 行为 `{hourly_cfe, recovery_headroom}`、8 行三者全有、2 行另含 `device_capacity`；`recovery_headroom` 是其余码的超集。

> 主代理复核补充：从 `report.json` 独立重算得到组合分布为 `{hourly_cfe, recovery_headroom}` 19 行、`{recovery_headroom, scalar_supply}` 12 行，合计 31 行——与"每行含 `recovery_headroom`、少数另含 `device_capacity`"一致。审查方的"8 行三者全有、2 行含 device_capacity"系按其自身分组口径统计，不影响 31/19/12 三个主数字。

**84 个瞬时单元**：重放违约码 0/84；`method_observed_primary_deadline_miss` 与 `replay_observed_primary_deadline_miss` **84/84 完全相同**（9 个不同取值，如 11/150、1/10、21/250）。

**补充尺度亦对**：瞬时 216 单元中 162 个 D1 = 124 个无码（轴二 D3 的 84 + 轴二 D1 的 40，40 个亦期限未完成量相同）+ 38 个带码（全为 `event_envelope` 单码，全落轴二 D1）；71 = 31 + 40，自洽。

## 五、正文可引用强度 —— REWORK

该包只在**同一 10 小时 fixture 骨架**上变化 f/K/α，其余字段由 `patch_config`（`:79-87`）与测试 `:38-53` 钉住不动，**不构成独立留出**。`report.json` 自身的 `scope` / `authority: DRAFT_NONAUTHORITATIVE` / `formal_result: false` 均正确。

但 6.3 草稿有两处会让读者高估：

1. **关于 v1/v2 的表述错误。** 草稿原文写"v2 与 v1 在所有已记录单元上逐字节等价，故 v1 的越界守卫缺陷不影响本节任何数字"。v2 的唯一功能差异**就是**该守卫（`src/staged_deliverability_replay_v2.py:100-101`），"逐字节等价"在守卫触发域不成立；且本包根本不走 v2（`src/staged_deliverability_d_grid_v1.py:31-32` 导入 v1）。正确表述是"本包由 v1 运行，守卫对本包不可达"。
2. **缺证据性质标注。** 6.3.3 与 6.3.4 的表旁未标注"同一 fixture 骨架的参数扫描、非独立留出"，也未把 §6.3.5 第 4 条（加强型匹配未做）绑定到本节数字。

## 关于 v1 越界缺陷对本包的影响

**无影响。** 三条独立证据：

1. **构造性**：`extract_actions`（`replay_v1.py:46-54`）取 `q = record.grid_served + record.cfe_served`，而 `advance()`（`development_v1.py:195-197`）中 `grid_served = min(grid/slope, room)`、`cfe_served = min(green/slope, room − grid_served)`，故 `q ≤ grid/slope + green/slope` 恒成立。`replay_step` 的 `grid`/`green` 由同一 `power_mapping(p, o)`（deferred=0）重算，与 `advance` 的 reference 在同一观测上完全一致。
2. **实证**：27 fixture × 24 组合 × 全部原生 step 记录逐条比对，**6,210 条记录越界 0 条**，最小余量恰为 0（`f_1of5__K_2of3__a_3of5 / fast/on_time/early/instantaneous` 小时 −2，q=0、额度=0），即守卫只会取等、永不触发。
3. **失败模式**：若不可达前提被破坏，v1 的行为是抛 `ValueError` 终止整次运行，而非产出越界标签，因此不可能悄悄改变 648 个单元格中的任何一个。

另注：`replay_step` 只在本包从不发生的超界情形才截断 `q`，故 `grid_shortfall` / `cfe_call_shortfall` 与 v1 语义一致，v1/v2 在本包全部单元上必然同值。

## 失效边界表述

**新表述正确，旧表述充分但不必要。** 从 `report.json` 的 combos 独立重算，4 个无假通过组合恰为 `(f,K,α) = (1/5,2/3,4/5)`、`(1/5,4/5,4/5)`、`(1/5,1,7/10)`、`(1/5,1,4/5)`。以声明集 3×3×3 做集合比对：

- 旧式 `f=1/5 ∧ α≥4/5` 预测 3 组，漏掉 `(1/5,1,7/10)`，`exact_match=False`；
- 新式 `f=1/5 ∧ (α≥4/5 ∨ (K=1 ∧ α≥7/10))` 预测 4 组，`extra=∅`、`missing=∅`，`exact_match=True`。

**限定**：离散轴上 α 仅 3/5、7/10、4/5 三档，新式在该集合上是**精确刻画**而非仅充分；若外推到未扫描的 α 档位，`α≥7/10` 与 `α≥4/5` 之间的连续性未经检验，表述宜限定"本 27 组内"。

`blocker_register.md:37` 的更正与 `paper/drafts/staged_deliverability_results_6_3.md:43` 的更正互相自洽；`:17` 的旧条目按"不重写历史"保留、由 `:37` 显式覆盖，符合仓库惯例。`attempt_05` 的 `validation_report.md` §3 仍留旧表述，属文档未闭环（本轮已补更正）。

## D1 总数

**重放轴 233 vs 登记 233，一致；策略轴 118 vs 登记 118，一致。** 拆分亦对：重放轴 D1 = `fixed_headroom` 71 + `instantaneous` 162；按轴聚合 f=1/5 为 43、f≥2/5 各 95；`by_eligible` / `by_equipment` / `by_cfe_target` 三张表与 summary 全项相等。

## 测试实跑

`tests/test_staged_deliverability_d_sensitivity_v1.py` → **37 passed in 1.88s**，与登记 37 项一致。主代理复跑 37 passed in 1.50s。

---

## 最小修复集（REWORK）

1. `paper/drafts/staged_deliverability_results_6_3.md:3`：删去"v2 与 v1 逐字节等价"作为证据支柱，改为"本包由 v1 运行，守卫对本包不可达"。**已修**。
2. 同文件 6.3.3 与 6.3.4 表旁各加一句"同一 10 小时 fixture 骨架的参数扫描、非独立留出"的标注。**已修**。
3. （非阻断）`attempt_05/validation_report.md` §3 的失效边界旧表述就地更正。**已修**。

## 主代理对子代理回报的核对

按 `agent.md` §7，子代理回报是线索而非证据。以下经实测核对后方可引用：

- 哈希六项、`37 passed`、233/118、278/137/118/115、31 + 84、31/19/12 违约码计数、84/84 期限未完成量相同——**全部复现**。
- attempt_04 保留 27 组 / 648 行 / 18 个 `degenerate` 标记、字段名为 `degenerate` 而非 `cfe_binding_hours`——**复现**。
- `feasibility_screen` 先于 `run_matrix`、`cfe_binding` 不参与筛选——**读码复现**。
- 审查方所述"8 行三者全有、2 行另含 `device_capacity`"的分组口径，主代理重算得到 `{hourly_cfe, recovery_headroom}` 19 / `{recovery_headroom, scalar_supply}` 12 的二分，两处主数字一致；分组细节不影响结论。

## 状态

敏感性包的实现、结果与分解：**PASS**。正文引用层：**REWORK 已闭合**（三处均已修改）。R3 门对敏感性包关闭。

该 PASS 不授权 formal run、资源准入或论文主张；6.3 中引用的敏感性数字仍受"非独立留出"限制，C3 的留出条件由 6.4 承担。
