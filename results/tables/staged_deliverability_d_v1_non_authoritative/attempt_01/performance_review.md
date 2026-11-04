# D attempt_01 的整体性能审查记录

2026-11-04，`DRAFT_NONAUTHORITATIVE`。按 `agent.md` §9 对 D 有限阶段比较包（`attempt_01`）登记的启动前整体性能审查。本文件是补记：该 attempt 已于 2026-11-04 执行完毕，审查证据为执行后对同一冻结字节的实测，**不是**执行前的预估。顺序偏差如实记录于 §7。

绑定对象：`results/tables/staged_deliverability_d_v1_non_authoritative/attempt_01/`，`report.json` SHA-256 `4c8efd01138fd815b21814b741508e3386f1fc83060049a51e1f5fc47f8a52b9`。

## 1. 完整路径与调用量

`experiments/staged_deliverability_d_v1.py` 的 DAG，无分支、无递归、无回调、无子进程：

| 阶段 | 实际调用量 |
|---|---|
| 导入与路径校验 | 4 个源文件 SHA 计算，1 次 |
| fixture 装载与校验 | `load_grid_config` 1 次；`load_grid_case` 每单元 1 次，共 8 次 |
| 方法原生执行 | `execute` 24 次（8 单元 × 3 方法） |
| 动作外置 | `extract_actions` 24 次 |
| 完整时序重放 | `replay_full_temporal` 24 次 |
| 完整策略参考执行 | `execute(full_temporal)` 24 次 |
| 定值计算 | `assessment` 48 次（每单元方法与重放各 1） |
| 汇总 | `summarize` 1 次 |
| 持久化 | `report.json` 1 次写入 + 1 次 SHA 读回 + 1 次 `report.sha256` 写入 |

逐小时步数：8 单元 × 3 方法 × 10 小时 × 3 条执行路径（原生／重放／参考）= **720 个模型小时步**。

**求解器调用 0，PYPOWER 潮流点 0，子进程 0，外部下载 0，付费查询 0。** 该包不触及任何求解器、任何外部数据源；历史重放无随规模增长的嵌套重放（无 journal 重放、无 checkpoint 重开、无 fresh 子进程）。

增长关系：调用量对单元数与小时数均为线性，`O(cells × methods × hours)`；每单元 `assessment` 以 task cohort 数线性遍历，无跨小时缓存，无 `O(T²)` 状态摘要遍历（该问题只在 B3 的 journal 保存重开路径上出现，本包不经过）。

## 2. 整体优化空间

| 候选 | 结论 |
|---|---|
| 参考执行与原生执行去重 | **不采纳**。`full_temporal` 单元的原生执行与参考执行参数完全相同，可复用一次；但当前实现为每单元—方法各执行一次 `full_temporal`，存在 8 次冗余。保留理由：复用会让"参考定值"与"方法定值"共享同一对象，削弱两轴独立性这一本文主张；成本仅约 1/3 秒。**作为已知冗余登记，不改。** |
| 跨单元缓存 fixture | **不采纳**。8 次装载合计约 64 ms，缓存会引入输入新鲜度判断，收益远小于风险。 |
| 观测复用 | 不适用：8 单元各自有不同观测序列，无重复可用。 |
| 并行 | 不适用：wall 已低于 2 秒，并发只会增加失败面。 |

结论：本包无实质性能瓶颈，无需优化即可进入下一步。

## 3. 有界代表性实测

同一冻结字节下分段实测（`rq2-executor` 环境，单进程）：

| 阶段 | 实测 |
|---|---:|
| 导入 | 132.39 ms |
| 单单元装载（10 小时） | 8.03 ms |
| `run_matrix` 全网格 | 1119.12 ms |
| 其中 `summarize` | 0.09 ms |
| 每单元—方法平均 | 46.6 ms |
| traced 峰值内存 | 0.141 MiB |

成功路径已全覆盖（24/24 单元均执行完成）。**昂贵失败路径未覆盖**：本包无 solver 失败、无超时、无 checkpoint 重开、无 I/O 注入。合同 §7 登记的失败处置（求解未决、超限停止、`full_temporal` 非平凡不等）在本轮均未触发，因此其实际成本为 UNKNOWN。

RSS 观测为 Python `tracemalloc` 追踪值，**不是**进程级 RSS；解释器与第三方依赖基线未计入。

## 4. 科学与校验等价

- 本包未做优化，不存在"优化后是否等价"的问题；上述唯一候选（参考执行去重）已明确不采纳。
- 加载器等价已独立证明：`baseline` 业务路径与 B1 冻结 fixture 的 `params` 及全部 10 个观测逐字段相等，4 个 (plan, clean) 组合全覆盖，有测试固定。
- 重放语义等价已独立证明：`full_temporal` 自身动作喂回重放，4/4 情景 `records_identical=True`、`stop_identical=True`、`verdict_identical=True`。
- 输入与源字节均有 SHA 绑定并写入 `report.json`，读回一致。
- 未放宽任何验收阈值；本轮不涉及 gap、残差、LB/UB 或对偶界。

## 5. 预算与停止条件

登记上限（合同 §6）：总 wall ≤ 4 小时；单进程 RSS ≤ 512 MiB；全部产物 ≤ 32 MiB；并发 1。

实测对照：wall 1.12 s（占上限 0.008%）；traced peak 0.141 MiB；产物 `report.json` 26423 B + `report.sha256` 66 B + 本报告与验证报告。**全部远低于登记上限。**

停止条件（合同 §7）已实现：`D5` 单列不追平；超限停止保留已接受单元；`full_temporal` 非平凡不等即停并作为 finding 登记；attempt 目录独占创建、拒绝覆盖。本轮无需触发任何一条。

**未做**：心跳、无进展判据、超时中断。理由：单进程 1.12 秒的纯内存包，此类机制无操作意义；若后续网格扩至合同 §4 的 36 次评估或接入 RTS-24，须补齐。

## 6. 绑定与结论

| 绑定项 | 值 |
|---|---|
| fixture | `configs/staged_deliverability_d_v1.DRAFT.yaml`（SHA 见 report.json `inputs`） |
| 冻结 B1 fixture | `configs/staged_deliverability_small_case_v1.DRAFT.yaml`（同上） |
| 源 | `src/staged_deliverability_d_grid_v1.py`、`src/staged_deliverability_replay_v1.py`、`src/staged_deliverability_development_v1.py`、`experiments/staged_deliverability_d_v1.py`（SHA 见 report.json `sources`） |
| 环境 | `D:\Miniconda3\envs\rq2-executor\python.exe`，pytest 9.0.2 |
| 规模 | 8 单元 × 3 方法 = 24 次评估，10 小时/单元 |

**整体性能审查：本包范围内完成。** 覆盖范围为本包声明的合成网格与上述字节。代码、fixture、环境或规模超出该范围时须重新审查；覆盖不变且 SHA 匹配时可复用本记录。

完成本审查**仅**解除 `agent.md` §9 的启动前条件，不替代科学门禁、资源准入、seal、`sol_reviewer` 独立审查或任何运行授权。`formal_result`、`resource_admission`、`security_certified` 恒为 `false`。

## 7. 顺序偏差（如实记录）

`agent.md` §9 要求实验启动前完成本审查。**实际顺序为：先执行 attempt_01，后补本记录。** 依据 §9 第 113 行"为形成审查证据的有界性能诊断，可在已有授权范围内先行开展"，D 作为零求解器的有界诊断属于该例外范畴；但"先跑后补审查"仍然偏离了"启动前必须完成"的字面要求，本记录不据此主张合规，仅供后续复核。

后续 D 的所有 attempt（含合同 §4 的补齐计划、E 的留出）**必须**在本审查扩展并登记完成后才启动。

## 8. 增补说明

本文件写于 `report.json` 之后，不计入该包的 input 或 source 清单，不改写 `report.json` 或 `report.sha256`。同目录 `validation_report.md` 是本包的运行后说明，两份文件均为 supplemental，不构成 completion 清单的一部分。
