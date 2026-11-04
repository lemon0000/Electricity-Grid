# D 有限阶段方案比较：attempt_01 开发验证

2026-11-04，`DRAFT_NONAUTHORITATIVE`。按[合同](../../../../docs/plan/staged_deliverability_d_development_contract_v1.md)执行的有界开发诊断。零 solver 调用、零外部下载、零付费查询。不构成正式结果、资源准入、seal 或论文结论。

`report.json` 26423 B，SHA-256 `4c8efd01138fd815b21814b741508e3386f1fc83060049a51e1f5fc47f8a52b9`，与同目录 `report.sha256` 独立读回一致。

## 1. 与合同 §4 网格的偏差（必须先读）

**2026-11-04 复核更正。** 本节初版写作时把两处登记为"偏差"，经核对既有配置与介绍稿后确认**二者均非偏差，而是初版合同写错**。原文保留于下供追溯，更正结论见本节末。

原始记录（已被取代）：

> 合同 §4 登记的是"3 个给定计划 × 2 业务进度 = 6 单元，每单元 3 方法 × 2 定值 = 36 次评估"。实际执行为 8 单元 × 3 方法 = 24 次评估，原因有二：……（1）"3 个给定计划"未实现为独立维度；（2）清洁路径被用作第五个维度，主网格与匹配臂未分离。

更正后的事实：

1. **给定计划本就应为 2 个，不是 3 个。** 介绍稿第 6 节明确把核心对照定为"业务快慢达产×电网按期或延期"，第 5.1 节写"业务快慢达产与电网按期或延期投运交叉形成机制情景"。"基线 / 电网加速 / 电网延期"三个计划是初版契约自行添加的，不与任何既有规格对应。且"电网加速"在本构型中**结构上不可实现**：`delay ≥ 0` 在三处加载器中为硬约束（`src/staged_deliverability_d_grid_v1.py:129`、`src/staged_deliverability_development_v1.py:417`、`src/staged_network_development_v1.py:93`），加速只能通过减小 `lead`/`start` 表达，而二者是全局单值字段，改动会破坏与 B1 冻结 fixture 的加载器等价性（`tests/test_staged_deliverability_d_grid_v1.py:28-33` 固定该等价）。
2. **清洁早/晚路径构成合法匹配对照，不是"未分离的第五维度"。** 独立验算：`early = [.60,.50,.84,.84,.84,1.04,.84,.84]`、`late = [.60,.50,.64,.84,1.04,1.04,.84,.84]`，两者总量同为 `317/50`、峰值同为 `26/25`，仅在 h2/h4 两小时上互换取值。这正是合同 §4 匹配臂要求的"保持清洁额度总量与峰值一致，只改到达时段"，且在外生输入层面严格成立。
3. **24 次评估即本网格的完整计数**：2 业务进度 × 2 电网进度 × 2 清洁路径 × 3 方法 = 24。P1 的计数要求应按 24 判定，而非初版契约写的 36；契约 §4 与骨架文档已同步更正。

仍未实现的是**加强型匹配**：即刻已兑现延期与恢复起点债务的匹配。这两者是策略运行的结果而非外生输入，无法通过输入设计固定，只能在分析中条件化。合同 §4 曾把它们与总量/峰值并列要求，属口径混淆；该项作为未闭合项保留于 §7。

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

1. **加强型恢复时段匹配未做**。清洁早/晚路径已构成外生输入层的合法匹配对照（总量与峰值相同，只改到达时段，见 §1 更正），但"已兑现延期与恢复起点债务一致"是策略运行的结果而非外生输入，无法通过输入设计固定，本轮未做任何条件化分析。C2 的结论须限定为"外生清洁额度时序一致、已实现延期与起点债务未匹配"，不得主张完整匹配条件下的恢复时段作用。
2. 全部结果来自单一 10 小时合成 fixture，仅 `change_hour` 在两条业务路径间变化。**样本极薄**，不得据此估计任何比例；分布数字只描述这 24 个单元。
3. 未做敏感性分支（f ∈ {5%,20%,50%}、K 两水平、alpha 三水平），合同 §4 登记但本轮未执行。
4. `full_temporal` 在 `fast/delayed` 两个单元于 h2 因阻塞违约提前停止，其后 8 小时未执行；重放按前缀语义镜像该停止（见 §6），但这两个单元的覆盖不完整，其 D4 标签的依据是"提前停止即未履约"，与"跑满窗口后判定失败"不是同一证据强度。
5. 整体性能审查已在执行后补做并单独成文（`performance_review.md`），但顺序为先跑后审，偏差已在该文件 §7 记录；wall 由事后重测得到，非执行当时观测。

本合同 §2 的动作外置与重放属 `agent.md` §7 的 R3 类（涉及恢复语义与非预见性），**须经 `sol_reviewer` 独立审查**方能作为 D/E 后续的证据基础。本轮为写入者自测，不构成独立审查结论。
