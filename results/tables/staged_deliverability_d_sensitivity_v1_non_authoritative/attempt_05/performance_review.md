# D 敏感性包 attempt_05 的整体性能审查记录

2026-11-05，`DRAFT_NONAUTHORITATIVE`。按 `agent.md` §9 对 D 敏感性包登记的启动后性能审查，补记于执行完成之后（顺序偏差见 §7）。

绑定对象：`results/tables/staged_deliverability_d_sensitivity_v1_non_authoritative/attempt_05/`，`report.json` 737737 B，SHA-256 `fb2ffd8a9c9d140dd6f6f71a3fa73076f33610761fa1f44ff06f0b8705090df4`。

## 1. 完整路径与调用量

`experiments/staged_deliverability_d_sensitivity_v1.py` 的 DAG。对 27 个参数组合各执行一次，无分支递归、无子进程、无回调：

| 阶段 | 每组合 | 27 组合合计 |
|---|---:|---:|
| 读取基础 fixture 并 deepcopy | 1 | 27 |
| 打补丁（f、alpha、K 与 idle 同步缩放） | 1 | 27 |
| 可行性筛查（容量 + CFE 上界） | 1 | 27 |
| 写出变体 YAML | 1 | 27 |
| 执行网格 `run_matrix` | 24 次评估 | **648** |
| 汇总 `summarize` | 1 | 27 |
| SHA 计算（变体 fixture） | 1 | 27 |

逐小时模型步：每评估含原生执行 3 次路径（方法、重放、参考）× 10 小时 = 30 步，648 × 30 = **19440 个模型小时步**。

**求解器 0、PYPOWER 点 0、子进程 0、外部下载 0、付费查询 0。**

增长：对组合数、单元数、方法数、小时数均为线性，`O(combos × cells × methods × hours)`。无跨组合缓存，无 journal、无 checkpoint 重开。

## 2. 整体优化空间

| 候选 | 结论 |
|---|---|
| 变体 fixture 落盘后复用 | **不采纳**。27 次写出合计不足 100 KB 且每份都需 SHA 入库；不落盘会使复现失去逐组合输入绑定。 |
| 跨组合缓存观测序列 | **不采纳**。f 与 alpha 影响 `HourInput` 之外的参数与派生量，K 改变 `compute_capacity`/`idle_mw`，三者都使观测不同，无重复可复用。 |
| `full_temporal` 参考执行去重 | **不采纳**，同主包性能审查 §2：会使参考定值与方法定值共享对象，削弱两轴独立性；此处冗余为 27 × 8 = 216 次，实测约 1.8 秒。 |
| 并行组合 | **不采纳**。总 wall 5.3 秒，并发只增加失败面。 |

结论：无实质瓶颈，无需优化。

## 3. 有界代表性实测

同一冻结字节下实测（`rq2-executor`，单进程）：

| 指标 | 实测 |
|---|---:|
| 全扫描 wall | 5.311 s |
| 每组合 | 196.7 ms |
| 每次评估 | 8.20 ms |
| traced 峰值 | 底噪（< 0.01 MiB），tracemalloc 追踪值 |

成功路径 648/648 全覆盖。**昂贵失败路径未覆盖**：无 solver 失败、无超时、无 I/O 注入、无结构不可行组合（本轮 27 组全部通过筛查）。合同 §7 的停止条件本轮未触发，其成本为 UNKNOWN。

## 4. 科学与校验等价

- 未做优化，无等价问题；上述四个候选均明确不采纳。
- 变体生成是**纯补丁**：只改 `flexible_fraction`、`parameters.alpha`、`equipment[*].capacity` 与 `equipment[*].idle_mw`，其余字段从基础 fixture 逐字继承。K 与 idle 同步缩放，符合既有"设备变更须同时改变待机"的义务。
- 基础 fixture 未被修改，字节由 `base_fixture` 字段绑定并读回。
- 未放宽任何验收阈值；不涉及 gap、残差、LB/UB 或对偶界。

## 5. 预算与停止条件

登记上限（沿用主包 §6）：总 wall ≤ 4 小时；单进程 RSS ≤ 512 MiB；产物 ≤ 32 MiB；并发 1。

实测对照：wall 5.311 s（占上限 0.037%）；`report.json` 737737 B + 27 个变体 fixture；全部远低于上限。

停止条件：attempt 目录独占创建、拒绝覆盖（本轮五次 attempt 各自独立，无覆盖）；`D5` 单列不追平；超限停止保留已接受单元。本轮未触发。

**未做**：心跳、无进展判据、超时中断。理由：单进程 5.3 秒的纯内存包，此类机制无操作意义；若组合数扩至数百或接入 RTS-24，须补齐。

## 6. 绑定与结论

| 绑定项 | 值 |
|---|---|
| 基础 fixture | `configs/staged_deliverability_d_v1.DRAFT.yaml`（SHA 见 report.json `base_fixture`） |
| 变体 fixture | 27 份，逐份 SHA 记入 `combos[*].fixture` |
| 源 | `src/staged_deliverability_d_grid_v1.py`、`src/staged_deliverability_replay_v1.py`、`src/staged_deliverability_development_v1.py`、`experiments/staged_deliverability_d_sensitivity_v1.py` |
| 环境 | `D:\Miniconda3\envs\rq2-executor\python.exe` |
| 规模 | 27 组合 × 24 评估 = 648 |

**整体性能审查：本包范围内完成。**

完成本审查**仅**解除 `agent.md` §9 的启动前条件，不替代科学门禁、资源准入、`sol_reviewer` 独立审查或任何运行授权。`formal_result`、`resource_admission`、`security_certified` 恒为 `false`。

## 7. 顺序偏差

与主包相同：**先执行、后补审查**。依据 §9「有界性能诊断可在已有授权范围内先行开展」，本包零求解器且总 wall 5.3 秒，属该例外范畴；但字面要求是"启动前完成"，本记录不据此主张合规。

## 8. 本轮修正的实现缺陷

审查准备期间发现 `pin()` 对仓库外路径抛 `ValueError`（`Path.relative_to` 失败），使临时目录下的测量无法完成。已改为：仓库内路径记相对路径，仓库外路径记绝对路径，**不丢弃该文件**。该修改只影响记录字段的书写方式，不影响 `attempt_05` 已发布字节（其 fixture 全在仓库内），也不影响任何科学输出。

## 9. 增补说明

本文件写于 `report.json` 之后，不计入该包的 input 或 source 清单，不改写 `report.json` 或 `report.sha256`。同目录 `validation_report.md` 与本文件均为 supplemental。
