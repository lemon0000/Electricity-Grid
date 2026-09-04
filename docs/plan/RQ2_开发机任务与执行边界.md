# RQ2 开发机任务与执行边界

更新日期：2026-09-03

本页是当前工作导航，不是冻结配置、执行授权、结果凭证或论文证据。科学口径以
`agent.md`、`RQ2_公开数据鲁棒识别路线图_v6.md`和预注册配置为准；阶段门禁以
`docs/model_spec/blocker_register.md`为准。

## 1. 当前证据状态

- fresh HiGHS/Gurobi confirmatory pilot v4 已完成，四个独立 worker、结果重建和
  semantic contract 均通过；该结果只关闭跨求解器确认门。
- process-isolated HiGHS V8 已完成固定 `0008 -> 0009` nonformal evidence run，
  publication 为 `committed_success`，独立 post-result review 为 `PASS`。
- formal activation V1-V4 均未取得执行许可；V4 的独立结论为 `ESCALATE`。当前
  没有可执行 formal candidate，也没有 formal-run authority。
- 1071-block grid package、pairwise package和identification package均未发布。
- 四臂增强基线的 core、checkpoint contract、external preflight入口及
  identification/report contract已实现为 validate-only 状态；外部grid输入、
  独立复审、用户执行授权和正式结果门仍未打开。
- 联合服务可交付前沿v2已seal并等待独立R4 review；主设计为46个cells，主指标为
  `I_joint = D_J - max(D_N,D_C)`及其`I_sep + A_B6`分解。target-specific CFE
  builder、非互斥归因和正式runner尚未绑定；sealed outer SHA-256为
  `ae1e8a8a5c4c276e5c0d54900636de94e5402f29923817cf8cb70067b90c90f7`。
- 已有70-cell派生benchmark保持
  `R1=0, R2=0, R3=69, mixed=1, unresolved=0`，不支持原正向H2。

## 2. 本开发机可执行的工作

1. 维护研究问题、estimand、外推边界、blocker和论文叙事的一致性。
2. 对已存在的配置、manifest、checkpoint inventory和结果包进行只读核验。
3. 运行Ruff、单元测试、合成小例、`--validate-only`和零solver门禁测试。
4. 在明确开发授权下构建新的 non-authoritative draft，并完成pre-seal测试与
   fault injection；seal和独立review按`agent.md`第7节另行执行。
5. 完善四臂增强基线的测试、schema和报告模板，但不得把缺失的正式grid package
   替换为合成或历史checkpoint。
6. 按联合可交付前沿主线同步研究问题、estimand、论文叙事与证据门，同时保留
   `formal_result=false`与`security_certified=false`。

## 3. 当前顺序

1. 封口联合可交付前沿科学协议并取得独立R4 review。
2. 建立target-specific CFE call、46-cell inventory、容量分解和非互斥归因的
   versioned implementation successor。
3. 由用户另行决定是否授权创建formal activation V5 draft。该授权只覆盖设计与
   短验证；seal、独立review和formal run仍分别受门禁约束。
4. 若formal activation successor通过独立review并另获formal-run authority，从block zero运行冻结的
   1071-block process-isolated HiGHS grid流程。
5. grid package完整发布并验签后，依次开放46-cell planning、training-support
   audit、pairwise replay和identification。
6. 按冻结bottleneck vector报告single-service binding、joint interaction、
   B6 capacity bias与场景外服务后果。

## 4. 停止条件

- timeout、missing incumbent、资源停止或证书不完整只进入`unresolved`。
- E0保留无条件质量，不进入条件业务风险或R3。
- 未发布完整grid package前，不运行pairwise或identification。
- 未取得独立review与单独formal-run authority前，不启动、恢复或替换formal run。
- 不复用v5的202个HiGHS checkpoint或历史Gurobi的9个checkpoint形成新正式结论。

## 5. 入口

- 科学路线：`docs/plan/RQ2_公开数据鲁棒识别路线图_v6.md`
- 确认性主线：`docs/plan/RQ2_联合服务可交付前沿确认性方案_v2.md`
- 不可变科学基础：`docs/plan/RQ2_联合服务可交付前沿确认性方案_v1.md`
- 指标规格：`docs/model_spec/rq2_joint_deliverability_estimands_v1.md`
- 论文导航：`docs/plan/RQ2_论文路线图.md`
- 阶段门禁：`docs/model_spec/blocker_register.md`
- 增强基线：`docs/plan/RQ2_增强基线鲁棒性预注册_v1.md`
- 历史Windows交接快照：`docs/plan/RQ2_执行机交接_v2.md`
