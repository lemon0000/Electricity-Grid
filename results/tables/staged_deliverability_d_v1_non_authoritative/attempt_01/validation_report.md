# D 有限阶段方案比较：attempt_01 开发验证

2026-11-04，`DRAFT_NONAUTHORITATIVE`。按[合同](../../../../docs/plan/staged_deliverability_d_development_contract_v1.md)执行的有界开发诊断。零 solver 调用、零外部下载、零付费查询。不构成正式结果、资源准入、seal 或论文结论。

`report.json` 26423 B，SHA-256 `4c8efd01138fd815b21814b741508e3386f1fc83060049a51e1f5fc47f8a52b9`，与同目录 `report.sha256` 独立读回一致。

## 1. 与合同 §4 网格的偏差（必须先读）

合同 §4 登记的是"3 个给定计划 × 2 业务进度 = 6 单元，每单元 3 方法 × 2 定值 = 36 次评估"。**实际执行为 8 单元 × 3 方法 = 24 次评估**，原因有二：

1. **"3 个给定计划"未实现为独立维度。** B1 冻结 fixture 的 plan 维度就是电网工期（`delays: {on_time, delayed}`），没有第三个可区分计划。要实现三计划需新增构造输入，本轮未做——这属于合同 §4 未闭合项，不是已完成项。
2. **清洁路径（early/late）被用作第五个维度。** 合同 §4 把"恢复时段匹配臂"登记为独立的 36 次评估；本轮把它实现为 `clean` 维度参与主网格，因此主网格与匹配臂**未分离**。这削弱了 C2 的匹配论证：本轮尚无"只改到达时段、其余全部固定"的独立对照臂。

因此**合同 §8 的 P1（网格完整性：6 单元 × 3 方法 × 2 定值 = 36）未满足**。本轮满足的是"24 次评估全部报告、D3/D4/D5 均披露"，不满足的是"36 次评估"这一计数要求。后续 attempt 需补齐第三计划与独立匹配臂，不得沿用本轮计数。

## 2. 判断差异矩阵

`method` 为方法自身定值，`replay` 为其安排在实际路径完整时序约束下的重放定值，`strategy` 为完整时序策略对同一计划的定值。`True` = 可交付，`False` = 不可交付。

| business | grid | clean | method | method | replay | strategy | replay 轴 | strategy 轴 |
|---|---|---|---|---|---|---|---|---|
| fast | on_time | early | instantaneous | True | False | False | D1_false_pass | D1_false_pass |
| fast | on_time | early | fixed_headroom | True | False | False | D1_false_pass | D1_false_pass |
| fast | on_time | early | full_temporal | False | False | False | D4_agree_fail | D4_agree_fail |
| fast | on_time | late | instantaneous | True | False | False | D1_false_pass | D1_false_pass |
| fast | on_time | late | fixed_headroom | False | False | False | D4_agree_fail | D4_agree_fail |
| fast | on_time | late | full_temporal | False | False | False | D4_agree_fail | D4_agree_fail |
| fast | delayed | early | instantaneous | True | False | False | D1_false_pass | D1_false_pass |
| fast | delayed | early | fixed_headroom | False | False | False | D4_agree_fail | D4_agree_fail |
| fast | delayed | early | full_temporal | False | False | False | D4_agree_fail | D4_agree_fail |
| fast | delayed | late | instantaneous | False | False | False | D4_agree_fail | D4_agree_fail |
| fast | delayed | late | fixed_headroom | False | False | False | D4_agree_fail | D4_agree_fail |
| fast | delayed | late | full_temporal | False | False | False | D4_agree_fail | D4_agree_fail |
| slow | on_time | early | instantaneous | True | False | True | D1_false_pass | D3_agree_pass |
| slow | on_time | early | fixed_headroom | True | True | True | D3_agree_pass | D3_agree_pass |
| slow | on_time | early | full_temporal | True | True | True | D3_agree_pass | D3_agree_pass |
| slow | on_time | late | instantaneous | True | False | True | D1_false_pass | D3_agree_pass |
| slow | on_time | late | fixed_headroom | True | False | True | D1_false_pass | D3_agree_pass |
| slow | on_time | late | full_temporal | True | True | True | D3_agree_pass | D3_agree_pass |
| slow | delayed | early | instantaneous | True | False | False | D1_false_pass | D1_false_pass |
| slow | delayed | early | fixed_headroom | True | False | False | D1_false_pass | D1_false_pass |
| slow | delayed | early | full_temporal | False | False | False | D4_agree_fail | D4_agree_fail |
| slow | delayed | late | instantaneous | True | False | False | D1_false_pass | D1_false_pass |
| slow | delayed | late | fixed_headroom | True | False | False | D1_false_pass | D1_false_pass |
| slow | delayed | late | full_temporal | False | False | False | D4_agree_fail | D4_agree_fail |

分布：

| 轴 | D1 假通过 | D2 假拒绝 | D3 一致通过 | D4 一致失败 | D5 未决 |
|---|---:|---:|---:|---:|---:|
| replay | 11 | 0 | 3 | 10 | 0 |
| strategy | 8 | 0 | 6 | 10 | 0 |

## 3. D2 恒为零是结构性的，不是经验发现

两种简化都**放宽**约束而非收紧：`instantaneous` 从调用额度中省略整个事件包络；`fixed_headroom` 用常数 `fixed_headroom` 替代实际恢复余量。因此二者都不可能比完整时序评价更保守，D2（简化拒绝而完整策略接受）在当前方法集下不可达。

这一点已固化为测试 `test_approximations_are_structurally_permissive`：若将来引入收紧型简化，该测试必须显式失败。论文 C3 因而只能主张假通过方向；介绍稿第 3 节已按此改写，不再承诺两个方向。

## 4. 机制观察

`fast` 路径上 `instantaneous` 与 `fixed_headroom` 在多数单元判通过而重放判失败，机制可逐小时追溯：物理小时 2 起业务从 1/2 升至 7/10，参考取电升至 21/20，而此时 CFE 余量 `cfe=0`（清洁额度 21/25 只能覆盖 80% 目标）；恢复到物理小时 5 才出现 `cfe=1/5`，而相关任务期限为小时 3。**恢复窗口被推到期限之后**。

该任务的账本同时显示 `remaining=0` 与 `missed=1/5`，这不是缺陷：工作已补足，但逾期记录按 `agent.md` §8 保留。这正是"简化评价只看当期、完整时序看期限前可用窗口"产生分歧的具体路径。

`slow` 路径上业务推迟到小时 5 才上升，恢复窗口落在期限内，因此 `fixed_headroom` 与 `full_temporal` 判通过，`instantaneous` 仍因不检查恢复而定值为通过但重放失败（其安排从未补做）。

## 5. 覆盖与未决

本轮 `D5_undetermined` 为 0，因为 24 个单元窗口覆盖均完整（`hours=10`，`coverage_complete=True`）。这不是"没有未决"的一般结论，只是"本网格未触发右删失"。合同 §3 要求未决单列的口径已在代码中实现（`label_from` 对 `None` 优先返回 D5），未被本轮触发。

## 6. 实现与检查

新增文件：

- `src/staged_deliverability_replay_v1.py`：动作外置 `extract_actions`、完整时序重放 `replay_step`/`replay_full_temporal`、三值定值映射 `label_from`/`verdicts`。
- `src/staged_deliverability_d_grid_v1.py`：D 网格加载、单元评估（双轴）、分布汇总。
- `configs/staged_deliverability_d_v1.DRAFT.yaml`：网格 fixture，`baseline` 路径用于加载器等价性证明。
- `experiments/staged_deliverability_d_v1.py`：一次性 attempt 运行器，拒绝覆盖既有目录。
- `tests/test_staged_deliverability_replay_v1.py`（20 项）、`tests/test_staged_deliverability_d_grid_v1.py`（19 项）。

实测检查：

- `pytest tests/test_staged_deliverability_replay_v1.py tests/test_staged_deliverability_d_grid_v1.py` → **39 passed**。
- 关联回归 `tests/test_staged_deliverability_development_v1.py` + `evaluation_records_v1` + 新增两套 → **137 passed, 4 failed**。4 项失败均为 `ModuleNotFoundError: No module named 'psutil'`（`experiments/staged_deliverability_b1_development_v1.py:14`），属环境缺依赖；本包未修改该文件任何字节。
- P4 恒等检验：`full_temporal` 自身动作喂回重放，4/4 情景 `records_identical=True`。
- 加载器等价：`baseline` 业务路径与 B1 冻结 fixture 的 `params` 与全部 10 个观测逐字段相等，4 个 (plan, clean) 组合全覆盖。

## 7. 未闭合与下一步

1. **第三给定计划缺失**（§1 偏差 1），需新增构造输入并重新登记预算。
2. **恢复时段匹配臂未独立实现**（§1 偏差 2），C2 目前无匹配对照证据，不得据本轮结果主张恢复时段作用。
3. 全部结果来自单一 10 小时合成 fixture，仅 `change_hour` 在两条业务路径间变化。**样本极薄**，不得据此估计任何比例；分布数字只描述这 24 个单元。
4. 未做敏感性分支（f ∈ {5%,20%,50%}、K 两水平、alpha 三水平），合同 §4 登记但本轮未执行。
5. 未做整体性能审查（合同 §9 第 1 项）的独立复核；本轮 wall 未单独记录，只有 `created_utc` 时间戳。

本合同 §2 的动作外置与重放属 `agent.md` §7 的 R3 类（涉及恢复语义与非预见性），**须经 `sol_reviewer` 独立审查**方能作为 D/E 后续的证据基础。本轮为写入者自测，不构成独立审查结论。
