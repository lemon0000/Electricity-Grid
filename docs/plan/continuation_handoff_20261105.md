# 新对话交接：D 阶段比较主线（2026-11-05）

本文件是 D 线的当前交接。`docs/plan/continuation_handoff_20261022.md` 是滚动索引，本文件已挂到其顶部。截至本文件，HEAD 为 `4fd0d436`（工作区另有未提交的敏感性包，见 §6）。

## 1. 一句话状态

论文题目已定（`agent.md` §2），可交付性三值判据已入 `agent.md` §4。**D 阶段比较已跑出阳性结果，主线可用；唯一硬阻塞是两包均待独立 R3 审查。**

## 2. 主线是什么

给固定接入点的 AI 智算中心，三条进度（业务达产、设备投运、电网扩建）不同步时，**评价用的简化检查会在哪些阶段判错**。

三种评价：瞬时可调 MW、固定恢复余量、完整时序。按**两条轴**判定：

- **轴一**：简化方法自己的安排，放到完整时序约束下重放，还站得住吗？
- **轴二**：简化方法是否拒绝了完整时序策略能完成的计划？

三值定值：可交付／不可交付／未决（右删失与证据缺失不计入成败）。

## 3. 已有结果

### 主网格 `staged_deliverability_d_v1_non_authoritative/attempt_01`

24 次评估（2 业务进度 × 2 电网进度 × 2 清洁路径 × 3 方法），零求解器，1.12 秒。

| 轴 | D1 假通过 | D3 一致通过 | D4 一致失败 |
|---|---:|---:|---:|
| 轴一（重放） | 11 | 3 | 10 |
| 轴二（完整策略） | 8 | 6 | 10 |

### 敏感性 `staged_deliverability_d_sensitivity_v1_non_authoritative/attempt_05`

27 组合 × 24 评估 = 648 次评估，5.311 秒，零求解器。轴为 f ∈ {1/5, 2/5, 1/2}、K ∈ {2/3, 4/5, 1}、alpha ∈ {3/5, 7/10, 4/5}，全部落在可行区内。

**23/27 组合出现假通过；f ≥ 2/5 的 18 组全部出现。**

### 关键科学结论

1. **假通过在可行区内稳健。** 但受可延期比例约束：f=1/5 且 alpha ≥ 4/5 时延期空间不足以形成恢复债务，三种方法趋于一致判断。这是唯一稳定的失效边界，可由参数直接读出。
2. **D2 假拒绝结构上不可达。** 两种简化都放宽约束而非收紧，已由测试 `test_approximations_are_structurally_permissive` 固定。C3 只主张 D1 方向。
3. **两轴不一致的 115 个单元是两种现象，不能合并。** 固定余量 31 个有真实物理违约（小时 2 的 `recovery_headroom` 31、`hourly_cfe` 19、`scalar_supply` 12）；瞬时 84 个重放无任何违约码，差异源于瞬时判据本身不读期限未完成量。后者应归入"简化规则省略了什么"，不是执行不可行。

## 4. 立即可接续的产物

| 用途 | 路径 |
|---|---|
| 论文骨架 + D 配置 | `docs/plan/thesis_outline_and_d_config_20261103.md` |
| D 执行契约 | `docs/plan/staged_deliverability_d_development_contract_v1.md` |
| 动作外置与重放实现 | `src/staged_deliverability_replay_v1.py` |
| D 网格 | `src/staged_deliverability_d_grid_v1.py` |
| 敏感性扫描器 | `experiments/staged_deliverability_d_sensitivity_v1.py` |
| 主网格报告 | `results/.../staged_deliverability_d_v1_non_authoritative/attempt_01/` |
| 敏感性报告 | `results/.../staged_deliverability_d_sensitivity_v1_non_authoritative/attempt_05/` |

测试：`tests/test_staged_deliverability_replay_v1.py`（20 项）、`tests/test_staged_deliverability_d_grid_v1.py`（19 项），共 39 项通过。解释器用 `D:\Miniconda3\envs\rq2-executor\python.exe`（compute 环境缺 pygments，pytest 无法启动）。

## 5. 下一步计划（按依赖顺序）

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | **R3 独立审查**动作外置与重放语义 | **未开始，唯一硬阻塞** |
| 2 | 敏感性已补完（性能审查 + 违约码分解） | 完成 |
| 3 | C2 收缩为外生层面结论 | 已完成（文字层） |
| 4 | E 独立留出：冻结计划/D/策略，在新路径执行 | **未开始** |
| 5 | RTS-24 公共算例（可降级为附录） | 未开始 |
| 6 | 写作：第2节 → 第4节 → 6.3 → 6.4 → 6.1/6.2 → 1/7/8 | 未开始 |

未扫描的维度：期限滞后、事件包络参数（`max_events`/`max_duration`/`minimum_rest`/`call_ramp`）、清洁路径形状、故障集合。

## 6. 本文件写就时的 Git 状态

- 分支 `experiment`，HEAD `4fd0d436`
- 已推送至 `e72e4ebb` 之后有 5 笔未推送
- 工作区未提交：敏感性扫描器与 5 个 attempt 目录
- 另有 40 项 10 月遗留（图件、PDF、文献表），与本线无关

## 7. 已降级的两条旧线

- **RQ2 联合服务前沿**：70-cell 结果 `R1=0, R2=0, R3=69, mixed=1`，正向 H2 不支持，卡死。保留为历史资产，不是首篇主线。
- **F 可复现执行链**：79 份交接、1584 秒受控费用、Win32 Job 成员观测。对 IEEE 审稿人加分是零，已建议降为论文"适用边界"里的一句话。`agent.md` §6 已改为不把 C 的整链预算作为 D 的前置。

## 8. 阅读顺序建议

1. `agent.md` §2（题目）、§4（三值判据与双轴）、§6（工作顺序）、§7（分级与委派）
2. 本文件 §3 的结果
3. `docs/plan/thesis_outline_and_d_config_20261103.md` 的章节结构与贡献绑定
4. 需要复现时再读两份 `validation_report.md` 与 `performance_review.md`

## 9. 已知的文档滞后

- `project_introduction.pdf`、`project_introduction_en.pdf`、`project_abstracts.pdf` 均滞后于对应 Markdown，按用户 11-03 指示未重建。重建前以 MD 为权威正文。
- 该状态已记入 `docs/model_spec/blocker_register.md`。
