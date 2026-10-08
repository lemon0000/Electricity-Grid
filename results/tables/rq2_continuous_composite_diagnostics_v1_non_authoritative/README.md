# 组合策略后继诊断包

DRAFT_NONAUTHORITATIVE；输入和策略均为合成机制假设。
原策略拒绝与同小时补救分别保存，小时计数不重复。B6组合策略拥有独立policy_id，不能写回旧B6结果。
未评价小时保持最后已验证状态；收到错误来源标识不等于验证了该小时。计数不用于经验风险概率。

| 场景 | 臂 | 输入提交数 | 原策略接受 | 补救验证 | 总验证 | 未提交输入 | 首个未评价输入序号 | 停止阶段 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| normal_recovery | network_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| normal_recovery | cfe_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| normal_recovery | joint_correct_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| normal_recovery | joint_b6_separate_planning_shared_execution | 48 | 48 | 0 | 48 | 0 | None | None |
| insufficient_recovery | network_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| insufficient_recovery | cfe_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| insufficient_recovery | joint_correct_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| insufficient_recovery | joint_b6_separate_planning_shared_execution | 48 | 48 | 0 | 48 | 0 | None | None |
| unknown_deadline | network_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| unknown_deadline | cfe_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| unknown_deadline | joint_correct_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| unknown_deadline | joint_b6_separate_planning_shared_execution | 48 | 48 | 0 | 48 | 0 | None | None |
| late_recovery | network_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| late_recovery | cfe_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| late_recovery | joint_correct_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| late_recovery | joint_b6_separate_planning_shared_execution | 48 | 48 | 0 | 48 | 0 | None | None |
| b6_shared_rejection | network_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| b6_shared_rejection | cfe_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| b6_shared_rejection | joint_correct_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| b6_shared_rejection | joint_b6_separate_planning_shared_execution | 48 | 25 | 23 | 48 | 0 | None | None |
| censored_prefix | network_only_shared | 25 | 25 | 0 | 25 | 0 | None | None |
| censored_prefix | cfe_only_shared | 25 | 25 | 0 | 25 | 0 | None | None |
| censored_prefix | joint_correct_shared | 25 | 25 | 0 | 25 | 0 | None | None |
| censored_prefix | joint_b6_separate_planning_shared_execution | 25 | 25 | 0 | 25 | 0 | None | None |
| recovery_then_hard_call | network_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| recovery_then_hard_call | cfe_only_shared | 48 | 48 | 0 | 48 | 0 | None | None |
| recovery_then_hard_call | joint_correct_shared | 29 | 28 | 0 | 28 | 19 | 29 | actual_validation |
| recovery_then_hard_call | joint_b6_separate_planning_shared_execution | 29 | 25 | 3 | 28 | 19 | 29 | actual_validation |
| recovery_then_source_gap | network_only_shared | 29 | 28 | 0 | 28 | 19 | 29 | input_validation |
| recovery_then_source_gap | cfe_only_shared | 29 | 28 | 0 | 28 | 19 | 29 | input_validation |
| recovery_then_source_gap | joint_correct_shared | 29 | 28 | 0 | 28 | 19 | 29 | input_validation |
| recovery_then_source_gap | joint_b6_separate_planning_shared_execution | 29 | 25 | 3 | 28 | 19 | 29 | input_validation |

inputs.jsonl保存完整场景输入；records.jsonl只保存提交前缀及原策略/补救子记录。
policy_id与策略参数见policies.json；配置、精确cohort余额和原始错误保存在对应JSON成员。
diagnostic_manifest.json仅是本地非权威清单；验证依赖相同本地代码和Python/PyYAML版本。
验证：python -B experiments/export_rq2_continuous_composite_diagnostics_v1.py --verify-existing
