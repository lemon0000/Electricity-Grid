# Continuous planner逐时执行见证

状态：`DRAFT_NONAUTHORITATIVE`。本组件服务于RQ2连续四臂容量规划的独立动作核验；输入与动作均为机制假设，输出为派生机制见证。实现为`src/rq2_joint_deliverability_boundary_v1/planner_witness.py`，测试为`tests/test_rq2_continuous_planner_witness_v1.py`。

## 输入与范围

沿用`rq2_continuous_planner_contract_v1.md`的training场景、canonical zero初态、single nonrolling period、1h步长与open terminal。候选必须绑定完整planner identity，按原顺序覆盖全部场景及小时。容量、grid/CFE执行量、恢复功率、实际业务功率、逐birth恢复分配均要求非负精确Fraction；不从solver status推断动作，不静默舍入或修复候选。

`REQUEST_BOUNDED`要求执行量等于对应有效请求，且原请求有效分解一致；`GRID_EXCESS`允许grid超额响应，CFE仍精确满足有效请求。保留原始CapacityObservation及执行请求投影，两者不能互相替代。共享轨道按grid+CFE总量判定活动，不逐分量抹去小量。

## 独立核验

在复用物理/cohort回放前，以Fraction独立检查：共享connected baseline、逐轨D/availability/call cap、minimum-event、up-ramp/response、duration/rest/count、累计调用能量、债务限额、恢复headroom、功率平衡及恢复分配总量。物理回放已有的浮点容差不替代这些精确约束。

ramp上限绑定canonical模型实际预计算的浮点系数，再按其十进制表示转Fraction；不改用两个十进制参数的精确乘积。例`.29*.1`得到`.028999999999999998`，故`.029`调用在该草案系数下拒绝；不借容差覆盖这一差异。

eta乘恢复功率在模型中保留为系数乘决策变量，债务账继续使用十进制eta与Fraction恢复的精确乘积。Pyomo对该表达式的浮点求值可能有舍入残差，须在后续solver残差审计中单独报告，不能反过来改变cohort守恒。

正恢复必须严格大于十进制SERVICE_TOLERANCE，转换为物理float后亦保持活动；任意Fraction恢复不被强制到某个十进制格点。正调用与恢复不能同轨同时发生。恢复有效工作为eta乘恢复功率，分配给显式原始source-hour birth；既有cohort回放继续检查birth合法性、逐笔守恒和物理/精确账的一致性。

B6使用独立grid/cfe规划轨道，各自检查包络，仍共享grid+CFE不超过baseline的限制；grid恢复不受CFE surplus限制，CFE轨道受限。B6通过仅表示separate-planning前缀见证，不表示共享业务实际执行可行。

每小时恢复后检查已知硬deadline；发生miss立即拒绝，之后的恢复不能消除已观察逾期。未知deadline保持unidentified，观察末端仍带债务或活动事件时诚实保留截尾，不增加末端清债约束。

## 失败与证据

失败记录保存原输入、动作、before、已经形成的投影与candidate_step。该场景在首个失败小时停止，execution保持最后接受状态；其他独立场景仍核验。因硬deadline失败的candidate_step保留逾期金额，不能只看execution上的cohort汇总而遗漏它。

全部配置场景的全部小时通过才有witness_capacity。外层审计对象重放验证其内容，不能通过替换部分场景结果制造接受状态。witness identity绑定候选、planner identity、合同版本和活动容差；它不是生产闭包或签名。

物理/cohort数值桥接的debt divergence或carry-in mismatch标为`unassessed_numeric_projection`；其他候选拒绝也不构成模型数学不可行证据。未评价后缀不能统计成成功。

本阶段未核验solver原变量、整数性、所有原约束残差、界或终止状态。`prefix_upper_bound`、完整服务LB/UB和因果策略证书保持null，`solver_residual_audit_complete=false`。离线任意分配见证亦不能直接成为EDF固定因果策略的训练证书。完整服务的容量界还依赖明确的projection/continuation关系。

## 开发验收

针对性测试覆盖四臂、原请求/执行投影、微小恢复、任意Fraction恢复、到期与迟到恢复、B6并行分轨恢复、严格容量及完整包络、功率/分配守恒、支持完整性和数值故障注入。独立审查新增ramp预计算系数边界反例；测试与pre-seal findings按实际检查记录。此文不产生official PASS、seal、正式结果或运行授权。

最终41项针对性及7文件234项相关回归通过；独立复核41项targeted、planner/witness合计99项通过，限定范围无开放finding。审查发现的ramp预计算系数问题已修复，eta精确守恒保持。另324组四臂两小时无恢复赋值对照一致。

源码SHA256：`88664772c4d4a7006cae835b05de4dc80a998e048d58e36e2bb8fb5600478f78`；测试SHA256：`7529670a455fc98daf092912d44ef3f0300e8f52faec3d34a31ce5e1b4e2ef4d`。后续工作是完整原变量快照、canonical残差审计与solver outcome适配。
