# 固定组合策略后继诊断包 v1

日期：2026-09-13。状态：`DRAFT_NONAUTHORITATIVE`。本项把已验证的组合controller导出为独立本地诊断包。
配置：`configs/rq2_continuous_composite_diagnostics_v1.DRAFT.yaml`；入口：
`experiments/export_rq2_continuous_composite_diagnostics_v1.py`；测试：`tests/test_rq2_continuous_composite_diagnostics_v1.py`。
旧模型、策略、配置和结果包保持原字节。新包位于
`results/tables/rq2_continuous_composite_diagnostics_v1_non_authoritative/`。

## 场景与证据来源

直接复用旧prefix配置的六个场景和265条输入，另加两条48小时场景序列，共361条配置输入。
每个场景运行network-only、CFE-only、joint-correct和B6对应的组合策略，共32个场景与臂组合。
policy在第一条观测前通过`CompositePolicy.from_config`固定；导出器每次只向controller传一个CurrentObservation。
参数、调用、deadline、初始零状态和策略均为mechanism_assumption。来源ID、哈希、holdout标签为合成标识，
没有导入真实公开数据，也没有新增正式split/coupling。

| 场景 | 来源/变化 | 诊断用途 |
|---|---|---|
| normal_recovery | 原场景原输入 | 常规primary轨迹 |
| insufficient_recovery | 原场景原输入 | 零恢复仍推进合法时钟，保留逾期债务 |
| unknown_deadline | 原场景原输入 | 清偿不把unknown改称按时完成 |
| late_recovery | 原场景原输入 | 迟到清偿保留到期短缺 |
| b6_shared_rejection | 原场景原输入 | B6在26保留primary拒绝，同小时转共享恢复，后继到48 |
| censored_prefix | 原25小时输入 | 已接受cohort未到deadline，保留截尾 |
| recovery_then_hard_call | 双服务23/24/25，29时grid=CFE=0.3 | joint/B6完整调用超限，后继仍未评价 |
| recovery_then_source_gap | 双服务23/24/25，第29条输入的power_source_hour改为99 | 显式synthetic_identity_fault_injection，四臂停止 |

新场景的override在固定配置中列出，最多两个补充场景；来源小时修改须标记为fault injection。
额外场景不是经验扰动抽样，也不是挑选策略有利区域的正式实验。
所有场景按相同规则如实记录；正常/unknown等旧场景CFE-only无调用的情况继续保留。

## 逐小时记录与计数

每条已提交输入只生成一条records行，包含case、arm、完整policy_id、submission_index、原观测与证据角色、
before/committed共享物理cohort状态、primary planning归档、组合prefix summary及两个可空子记录：

- `primary_event`仅在本小时尝试原策略时出现，保存状态/阶段/错误、原尝试动作、planning候选和原接受动作。
- `recovery_event`仅在本小时触发或继续共享补救时出现，保存决策阶段/错误、已生成实际动作及其校验状态。

切换小时两个子记录同时存在，原拒绝不会被覆盖，输入小时也不会重复计数。
切换后不重放原planning；旧primary planning归档逐时保持不变。
`outcome`只取`primary_validated`、`recovery_validated`或`unassessed`。
未评价时committed状态等于before，仍保存尝试动作/原错误；后续配置输入只留在inputs中，不产生虚构records。

本固定配置共1330条提交记录，其中1324条validated、6条unassessed。
B6共享拒绝场景中primary接受25小时、recovery验证23小时，唯一验证小时总计48。
硬调用场景：network/CFE各验证48小时，joint/B6第29条输入未评价并停在28，分别留下19条未提交输入。
来源gap场景四臂均在第29条输入停止，最后验证28；其raw source hour=99只作为错误来源标识，不解释为第99小时已服务或已验证。

summary分列`first_unassessed_submission_index`、`first_unassessed_source_hour`与`last_validated_hour`；
原拒绝也拆成`original_rejection_submission_index`与`original_rejection_raw_source_hour`，包括逐时prefix_summary；
产物不保留容易混淆的`original_rejection_hour`字段。N/C/J在gap场景的原拒绝输入序号为29，raw标识为99。
输入计数不是风险分母或实际曝光量。原拒绝与后继策略单独标识，组合策略结果不能写回旧B6结果或解释为其原策略效果。
cohort使用精确numerator/denominator整数字符串，保留unknown、历史miss和截尾；不擦除微小余额。
未评价小时及后缀实际结果为null，`risk_probability=null`、completion/formal/claim/security均保持关闭。

## 文件与验证

| 文件 | 内容 |
|---|---|
| config.json | 交付配置、扩展场景完整参数及controller配置 |
| inputs.jsonl | 八场景全部361条配置输入 |
| policies.json | 四个完整组合policy_id到参数的映射 |
| records.jsonl | 只含提交前缀，一次输入一行，两阶段子记录分列 |
| summary.json | 分场景/臂的计数、状态、原拒绝、停止位置与cohort |
| evidence.json | 合成输入/派生输出、身份和计数边界 |
| README.md | 从同一summary机械生成的浏览表 |
| diagnostic_manifest.json | 成员字节数/SHA256、导出器和依赖代码/配置/测试绑定、Python/PyYAML版本 |

旧prefix导出器仅作为plain、snapshot、make_inputs等纯函数依赖，未修改其字节，也未调用其写入入口。
manifest绑定这些实际依赖以及actual_actions/recovery_controller。policy_id绑定策略语义；manifest再绑定输入与实现字节，
二者不是同一种身份，也不充当pre-registration或安全签名。

生成拒绝覆盖已有目录，写入采用exclusive create，manifest最后写入；中断产生的半包不能通过inventory检查，
不会自动删目录、续写或覆盖旧包。验证入口只读检查exact inventory、普通文件、成员哈希/大小和依赖绑定，再完整重放并逐字节比较七个成员。
因此篡改输入、记录、summary或policy映射，即使重新计算成员清单哈希，也不能通过重放校验。
验证依赖本地代码和相同Python/PyYAML版本，不是独立模型正确性或工程安全证明。

```text
python -B experiments/export_rq2_continuous_composite_diagnostics_v1.py
python -B experiments/export_rq2_continuous_composite_diagnostics_v1.py --verify-existing
```

## 验收与剩余范围

测试包含独立逐行功率/债务守恒、状态停止、原拒绝/补救分列、旧输入保持、policy/evidence/unknown/censoring、
重新哈希后的四类篡改、缺失manifest/额外文件/字节破坏/依赖变化及拒绝覆盖。
仍缺真实业务参数、非零carry-in、损失/抢占模型和未覆盖拒绝类型的实际动作合同；完整真实运行风险与正式数据实验保持阻塞。
本包仅完成当前固定组合机制的本地交付；下一步应梳理尚未覆盖的拒绝类型及其实际动作语义，不直接扩大正式实验。

## 本轮实际验证记录

解释器：`D:/Miniconda3/envs/compute/python.exe -B`。编辑前检查git状态和相关进程，核对当前合同、计划及blocker，
未发现活跃正式运行。复用本会话已读的仓库指令和karpathy-guidelines，仅新增本轮配置/导出器/测试/本文与新交付成员，
向计划/blocker追加状态，未修改旧代码、配置或结果。

主线程针对性命令`python -B -m pytest -q tests/test_rq2_continuous_composite_diagnostics_v1.py`在拆分raw source字段后为
`13 passed in 19.76s`。拆分前完整相关回归为`257 passed in 76.02s`；相关十文件命令：

```text
python -B -m pytest -q tests/test_rq2_continuous_composite_diagnostics_v1.py tests/test_rq2_continuous_recovery_controller_v1.py tests/test_rq2_continuous_actual_action_contract_v1.py tests/test_rq2_continuous_prefix_diagnostics_v1.py tests/test_rq2_continuous_causal_policy_v1.py tests/test_rq2_continuous_four_arm_replay_v1.py tests/test_rq2_continuous_debt_cohorts_v1.py tests/test_rq2_continuous_multiday_service_v1.py tests/test_rq2_joint_deliverability_boundary_v1.py tests/test_rq2_joint_deliverability_continuation_audit_v1.py
```

独立只读`sol_reviewer`在最终字段版本运行十文件回归为`257 passed in 54.95s`；raw-source歧义finding已闭合，未见新增开放finding。
独立oracle核对32组合、1330记录、1324 validated、114未提交输入，以及submission唯一性、状态链、停止末行、summary与policy_id均一致。
该审查只属于non-authoritative pre-seal findings，不是official verdict、receipt或运行授权。
固定目录生成前确认不存在且无相关活动进程；上述生成与`--verify-existing`两条命令均已运行，返回32组合、1330记录、完整重放匹配。
独立落盘核验确认exact 8个普通文件、7个成员bytes/SHA及16项依赖SHA匹配，原歧义字段已移除，README证据边界一致，未见新增finding。

旧prefix交付`--verify-existing`通过（24组合、1038记录），原22项文档哈希绑定与公开数据交付7个成员哈希匹配。
`git diff --check`通过；旧v5 symlink环境项本轮未重跑，仍未验证。本轮没有正式实验、solver、下载、付费查询或仓库清理。

开发SHA256绑定（不是seal）：

| 文件 | SHA256 |
|---|---|
| configs/rq2_continuous_composite_diagnostics_v1.DRAFT.yaml | `7810034308502f6066ddda05bdb5ec0c1dde11faae81c9560f55e116c010294a` |
| experiments/export_rq2_continuous_composite_diagnostics_v1.py | `1cb6adda51f9fbfa8df87eb5978f59da6e10ef0e7bb3fef1e4e7c3e27548775d` |
| tests/test_rq2_continuous_composite_diagnostics_v1.py | `7808397efc67bd50dd2b44f25b6d8ad96aa361f9529c79b01e1c96b49d084dce` |
| results/tables/rq2_continuous_composite_diagnostics_v1_non_authoritative/diagnostic_manifest.json | `8893c7080d7f17bd1f935f125e54fe8a8edea94d172205b57d73e6523406f466` |
