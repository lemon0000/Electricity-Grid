# 连续服务合成前缀诊断包

状态：DRAFT_NONAUTHORITATIVE。全部输入为机制假设，未使用真实观测。
四臂使用各场景相同的逐小时输入；已接受小时表示固定动作通过服务包络校验。
首次拒绝小时及其后的实际服务结果未评价，不能从该包计算完整风险率或数学不可行性。

| 场景 | 臂 | 配置小时 | 提交观测 | 接受小时 | 最后提交小时 | 拒绝阶段 | 逾期 cohort | unknown cohort | 截尾 cohort |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| normal_recovery | network_only_shared | 48 | 48 | 48 | 48 | None | 0 | 0 | 0 |
| normal_recovery | cfe_only_shared | 48 | 48 | 48 | 48 | None | 0 | 0 | 0 |
| normal_recovery | joint_correct_shared | 48 | 48 | 48 | 48 | None | 0 | 0 | 0 |
| normal_recovery | joint_b6_separate_planning_shared_execution | 48 | 48 | 48 | 48 | None | 0 | 0 | 0 |
| insufficient_recovery | network_only_shared | 48 | 48 | 48 | 48 | None | 3 | 0 | 0 |
| insufficient_recovery | cfe_only_shared | 48 | 48 | 48 | 48 | None | 0 | 0 | 0 |
| insufficient_recovery | joint_correct_shared | 48 | 48 | 48 | 48 | None | 3 | 0 | 0 |
| insufficient_recovery | joint_b6_separate_planning_shared_execution | 48 | 48 | 48 | 48 | None | 3 | 0 | 0 |
| unknown_deadline | network_only_shared | 48 | 48 | 48 | 48 | None | 0 | 3 | 0 |
| unknown_deadline | cfe_only_shared | 48 | 48 | 48 | 48 | None | 0 | 0 | 0 |
| unknown_deadline | joint_correct_shared | 48 | 48 | 48 | 48 | None | 0 | 3 | 0 |
| unknown_deadline | joint_b6_separate_planning_shared_execution | 48 | 48 | 48 | 48 | None | 0 | 3 | 0 |
| late_recovery | network_only_shared | 48 | 48 | 48 | 48 | None | 3 | 0 | 0 |
| late_recovery | cfe_only_shared | 48 | 48 | 48 | 48 | None | 0 | 0 | 0 |
| late_recovery | joint_correct_shared | 48 | 48 | 48 | 48 | None | 3 | 0 | 0 |
| late_recovery | joint_b6_separate_planning_shared_execution | 48 | 48 | 48 | 48 | None | 3 | 0 | 0 |
| b6_shared_rejection | network_only_shared | 48 | 48 | 48 | 48 | None | 0 | 0 | 0 |
| b6_shared_rejection | cfe_only_shared | 48 | 48 | 48 | 48 | None | 0 | 0 | 0 |
| b6_shared_rejection | joint_correct_shared | 48 | 48 | 48 | 48 | None | 0 | 0 | 0 |
| b6_shared_rejection | joint_b6_separate_planning_shared_execution | 48 | 26 | 25 | 25 | shared_execution | 0 | 0 | 3 |
| censored_prefix | network_only_shared | 25 | 25 | 25 | 25 | None | 0 | 0 | 3 |
| censored_prefix | cfe_only_shared | 25 | 25 | 25 | 25 | None | 0 | 0 | 0 |
| censored_prefix | joint_correct_shared | 25 | 25 | 25 | 25 | None | 0 | 0 | 3 |
| censored_prefix | joint_b6_separate_planning_shared_execution | 25 | 25 | 25 | 25 | None | 0 | 0 | 3 |

config.json 保存解析后配置；inputs.jsonl 保存各场景完整合成输入序列。
records.jsonl 只保存实际提交的前缀、当前观测、尝试动作、规划候选与提交状态。
summary.json 按场景和臂分别计数，不跨场景合并为概率；精确债务见 numerator/denominator。
diagnostic_manifest.json 是本地非权威文件清单，既不是 production manifest，也不构成运行授权。
验证：python -B experiments/export_rq2_continuous_prefix_diagnostics_v1.py --verify-existing
