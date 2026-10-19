# 三 arm hour-0 完整合成集成报告

状态：完整合成集成及独立进程保存记录重放通过；证据为 non-authoritative development。

三个独立 N0 经 common、Rref、逐 lane 业务映射与 Actual 到达 paired commit；关闭后重开，保存记录中的 heads、projection 和 carry 核对一致。
本例使用合成 source/enrollment/registry 与 fabricated solver adapter：N0 Windows Jobs 为 3，canonical selector Jobs 和真实 native 调用均为 0。

## 完整链耗时

| 阶段（原始 trace label） | 秒 |
|---|---:|
| `source_and_fixture_setup` | 49.240302 |
| `arm_0_open` | 22.266088 |
| `arm_0_N0` | 363.992076 |
| `arm_0_roster_attach` | 613.223998 |
| `arm_0_close` | 106.153947 |
| `arm_1_open` | 93.283349 |
| `arm_1_N0` | 1167.053634 |
| `arm_1_roster_attach` | 1042.233706 |
| `arm_1_close` | 178.419012 |
| `arm_2_open` | 170.350524 |
| `arm_2_N0` | 1984.152144 |
| `arm_2_roster_attach` | 1475.247811 |
| `complete_common_scientific_replay` | 1204.210455 |
| `common_genesis_and_inspect` | 24169.300104 |
| `selector_harness_and_reference_snapshot` | 2852.317712 |
| `Rref_parent_run` | 3524.686588 |
| `missing_all_Actual_rejected` | 4452.900991 |
| `Actual_snapshot_start_cfe_only_shared` | 0.000486 |
| `Actual_snapshot_ready_cfe_only_shared` | 2759.364169 |
| `Actual_parent_ready_cfe_only_shared` | 1460.685977 |
| `Actual_parent_returned_cfe_only_shared` | 6094.663703 |
| `Actual_cfe_only_shared` | 70.266683 |
| `Actual_snapshot_start_joint_correct_shared` | 0.000517 |
| `Actual_snapshot_ready_joint_correct_shared` | 2767.160583 |
| `Actual_parent_ready_joint_correct_shared` | 1459.117225 |
| `Actual_parent_returned_joint_correct_shared` | 6082.829101 |
| `Actual_joint_correct_shared` | 70.003454 |
| `Actual_snapshot_start_network_only_shared` | 0.000452 |
| `Actual_snapshot_ready_network_only_shared` | 2755.459461 |
| `Actual_parent_ready_network_only_shared` | 1457.467733 |
| `Actual_parent_returned_network_only_shared` | 6220.133730 |
| `Actual_network_only_shared` | 77.012760 |
| `missing_Actual_rejected_cfe_only_shared` | 16443.316412 |
| `missing_Actual_rejected_joint_correct_shared` | 23816.098280 |
| `missing_Actual_rejected_network_only_shared` | 20484.132395 |
| `paired_commit_and_readback` | 121923.418612 |
| `selector_parents_and_handoff_closed` | 0.001228 |
| `arm_2_close` | 0.209170 |
| `reopen_bootstrap_roster_common_and_close` | 2224.673797 |
| `paired_owner_reopen_replay_and_close` | 270.495198 |
| `integration_report_saved` | 0.006973 |
| `identity_bookends_restored` | 0.560919 |
| collection 与剩余 teardown | 4.213912 |
| pytest 总墙钟时间 | 259910.325371 |

独立进程保存记录重放及引用字段检查：401.167957 秒，其中六次新鲜历史校验与字段检查为 154.601544 秒。

计时包含测试专用 implementation identity bookends；并行检查记录见 chain_postcheck.json 的 timing_conditions。该计时不构成 native 运行预算或资源准入。

## 保存记录与边界

- carry SHA256：`7802224a162685f4f1e353fc9fa8f971c73f9dc0dd719876454895116773e29d`
- projection SHA256：`72b422d5734c6ea6d536b56c9bd74b583c783bb6cd2da7d8c2bf9669bf8762a1`
- holder head：`a3abb701e38dc2940447275370b84ed951cffa8dc51b6a0b2a8a8cdc1214e374`
- 三个 N0 Job 均 exit 0 且 whole_job_quiescent；具体 PID、creation identity 和原始 observation 在 chain_postcheck.json。
- 完整测试包含缺 Actual 的拒绝检查；补充失败窗口证据须按各自测试范围阅读。
- 本报告只覆盖该 hour-0 合成输入。跨小时/192h、正式资源准入、封存、official review 和正式实验仍需各自出口。

## 核验入口

- [terminal.json](<D:/CUHKSZ/Research Project/electricity-grid/results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/chain_07/terminal.json>)，SHA256 `5da14d3218d963751ef103cc06d3d63364f7559f7f5783e332dc1ab7d9c9ab5b`
- [postcheck_supplement_04_non_authoritative/chain_postcheck.json](<D:/CUHKSZ/Research Project/electricity-grid/results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/chain_07/postcheck_supplement_04_non_authoritative/chain_postcheck.json>)，SHA256 `dd5ec208ed7900208d682131ff0292ea346e2033a393c1342ef8f7ef496d067f`
- [postcheck_supplement_04_non_authoritative/fresh_process_replay/terminal.json](<D:/CUHKSZ/Research Project/electricity-grid/results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/chain_07/postcheck_supplement_04_non_authoritative/fresh_process_replay/terminal.json>)，SHA256 `146d6282162851c3796b8e0fba786630d3b2b18fe094488255735975c374b47e`
- [postcheck_supplement_04_non_authoritative/fresh_process_replay/result.json](<D:/CUHKSZ/Research Project/electricity-grid/results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/chain_07/postcheck_supplement_04_non_authoritative/fresh_process_replay/result.json>)，SHA256 `8c2134c2aa32fd9f73abfa17fb4747ba5f76e36108b050577acfb55e19e0aa92`
- [postcheck_supplement_04_non_authoritative/postcheck_manifest.json](<D:/CUHKSZ/Research Project/electricity-grid/results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/chain_07/postcheck_supplement_04_non_authoritative/postcheck_manifest.json>)，SHA256 `35fb24716a6cf2cd56cb0f5db9273e10e820208c9733ec5cf74d68982a8f37e1`
