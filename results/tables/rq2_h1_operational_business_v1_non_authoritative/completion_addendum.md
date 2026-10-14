

### 2026-10-08 — H1 exact business adapter 与全来源 scalar 表示检查闭合

新增 `experiments/h1_exact_business_development_v1.py`、对应测试和
`docs/model_spec/rq2_h1_exact_business_development_v1.md`。适配复用旧 v2 bidirectional policy 主体，
以 Fraction 保留当前CFE allocation/request/surplus及业务输入；strict f*w字段仅允许decimal语义无损转换。
Rref入值为B-P_ref；current内检查raw/effective合计与旧float-zero路径分类，保持原阈值与12位恢复规则。
business clock=t+1，完整历史/ledger/cohort/due与nonrolling预算保留；科学projection排除source/audit标签。
成功只生成detached business candidate和exact actual power，尚不构成持久或paired commit。

首轮22 passed/2 failed/15.06s，失败原件保留于attempt1_snapshot与root_tests_attempt1.json。
已修复：极邻近阈值Fraction与旧float zero混算导致分类改变时入口拒绝；copy/deepcopy/pickle保护。
修复后根25 passed/14.19s；与旧bidirectional policy合并66 passed/15.08s；
独立只读 `/root/outage_preseal_review` 25 passed/14.36s，均exit0，无开放PRE_SEAL implementation finding。
独立四臂label oracle与absolute clock+100平移oracle通过；其首次测试路径缺失、第二次未规范化birth key
的oracle失败经历均保留在审查转录，不隐藏或算作科研不可行证据。

新增 `experiments/audit_h1_exact_business_interface_development_v1.py`。
冻结workload全来源1632行逐行保留，每行f=.05/.20/.50三项，共4896检查。
training2448及holdout2430项均lossless；6条原holdout raw>1对应18项保持source_mapping_unresolved。
没有新增interface_unresolved、没有删行或裁剪输入。该离线表示检查不是holdout性能评价或策略未来输入。
独立只读 `/root/outage_origin_design_review` 的fresh内存审计与落盘JSON全对象相同，0 bad records。
它只覆盖现有来源的f*w strict scalar表示；未证明Rref/CFE阈值完整可达域、业务可行性或正式执行。

结果目录 `results/tables/rq2_h1_operational_business_v1_non_authoritative/` 保留全部失败、快照、审查和checks。
全程真实native=0、Job=0。source_input_binding_verified、persistent_lane_owner、same-key registry、
common publication、paired commit、完整192小时N/Rref/A执行、resource_admission、formal_execution_ready、
formal_result仍false。B6此单元仅shared actual业务，planning LB/UB仍为外层完整义务。
后继推进source-bound持久owner、N历史前缀重验、same-key sticky conflict、原子paired publication；
随后真实raw ingress/Job/分段预算、按需follow-up、完整manifest/DAG/LB-UB、资源/seal/fresh official review。
新的具体native包仍需在上述门齐备后另获明确运行授权。
