# B6 分离规划拒绝后的固定共享后继 v1

2026-09-16，`DRAFT_NONAUTHORITATIVE`。用户指定按拒绝类型与实际动作语义继续开发。
此草案补齐`separate_planning`拒绝后的一个明确机制，所有动作与参数均为mechanism_assumption。
旧actual-action、controller、配置、测试和诊断包保持原字节。

## 实际动作合同

新策略在第一条观测之前固定primary与shared recovery规则及其精度、触发阶段、失败语义和独立policy_id。
只适用于B6原臂：原`separate_planning`或`shared_execution`拒绝在同一原观测触发一次共享动作选择，
从最后已经提交的shared物理/cohort状态出发；以后永久按共享账运行。分离planning不恢复，原拒绝记录不改写。
新策略身份不同于旧B6与旧组合策略，不能把它的结果写回D_B、原B6策略或原诊断包。

完整网络/CFE调用保持`q=g+c`，调用时r=0；空闲时共享恢复cap为business/CFE-compatible/max-power/debt-over-eta的最小值，
采用旧固定精度保守量化及known EDF、unknown FIFO分配。功率`p=baseline-q+r`，债务`b_next=b+q-eta*r`。
这里复用原动作选择器与ActualActionRecord/共享回放校验，不另定义容差或放宽event/duration/rest/energy/debt限额。
规划失败只说明该固定分离动作失败，不能推断其他分离动作数学不可行。

| 拒绝/动作情形 | 实际语义 |
|---|---|
| separate planning失败、共享动作合法 | 同小时提交独立后继动作；保留原primary rejection与未提交planning证据 |
| shared execution失败、共享重选合法 | 按同一固定规则提交，覆盖旧补救机制的具名情形但使用新policy身份 |
| primary input_validation/policy_decision拒绝 | 不触发后继；停止，实际结果未评价 |
| shared决策无法生成或动作不满足原包络 | 保存错误及可用的尝试动作；不推进物理账，后缀未评价 |
| 输入source/split/provenance漂移 | 先拒绝身份，不能把错误小时当已服务时间 |
| 合法零/迟到恢复 | 时钟推进；到期短缺永久保留，unknown不变为准时完成 |

本合同不引入部分服务、非合同业务损失、额外救援资源或请求裁剪。完整硬请求超限仍不能生成可验证实际后缀。
这些处置属于后续独立合同，不由扩大触发阶段暗中实现。

## 审计链与计数

后继每条decision保存固定spec、before shared状态、原观测、阶段/error及可空ActualActionRecord。
decision从before重放以校验动作；cursor校验完整相邻状态链、首条与原拒绝观测完全相同以及策略身份。
命中触发阶段必须保存同小时decision，不能构造只有halted primary而没有补救记录的同身份cursor。
失败后禁止消费后续小时。原始source hour、submission index和最后validated hour分别报告。

`submitted_unique = len(primary.records) + max(0, len(successor_decisions)-1)`；
`validated_unique = primary_accepted + successor_validated`。
切换小时只有一份时间曝光，原拒绝作为子事件保留。实际末状态只能取最后验证小时；未知后缀仍null。
本地记录的确定性一致性不是防篡改签名、事前登记证明或production checkpoint。
`policy_id`只绑定策略规则；对另一组合法输入完整重放可产生同policy_id的另一条轨迹。
正式封存前外层必须绑定输入/轨迹hash及运行身份，不能用此局部cursor校验替代来源验签。

## 独立手算验收例

沿用既有synthetic envelope：eta=0.8、maximum duration=3、minimum rest=2、call cap=0.5。
h23=(g=.125,c=0)，h24=(g=0,c=.125)且本小时所有恢复cap=0，h25=(g=.125,c=0)。
每笔due=birth+3。h24关闭恢复是事先给定合成输入，防止旧分离轨在另一服务调用时发生更早的共享恢复冲突。

- 原B6在h23/h24共享状态均合法；h25 grid track仅休息1小时，分离规划拒绝，primary最后提交h24。
- 共享轨h23–25是同一持续3小时事件，h25动作q=.125、r=0、p=.875可通过；其debt=.375、energy=.375、event count=1。
- h26恢复.3125、work=.25，清偿h23/h24两笔；债务=.125。
- h27恢复.15625、work=.125，债务=0；截至h48原primary仍止于24，而组合验证48个唯一小时。

对照例保留旧双调用h23/24/25并增加h26第四小时调用：separate与shared均违反maximum duration，后继仍unassessed。
未来输入扰动不能改变早前决策；整段/分块、unknown、迟到恢复、参数身份/记录变异、原拒绝不可跳过均须验证。

## 验证记录

实现：`src/rq2_joint_deliverability_boundary_v1/b6_planning_recovery.py`。
配置：`configs/rq2_continuous_b6_planning_recovery_v1.DRAFT.yaml`。
测试：`tests/test_rq2_continuous_b6_planning_recovery_v1.py`。
新增18项针对性测试通过（0.63s）；最终8文件相关回归167项通过（15.73s）。
手算合法共享后继、完整请求仍失败、两种触发、唯一小时、未来扰动/分块、来源故障、决策故障、
历史/身份变异、known/unknown优先级、恢复三侧限额、永久miss与精度残差均有直接断言。
独立pre-seal审查完成，限定范围无阻塞实现finding；尚未签发official结论。所有正式科学/数据/结果/claim/security门保持原状态。

实际相关回归命令（解释器为`D:/Miniconda3/envs/compute/python.exe -B`）：

```text
python -B -m pytest -q -p no:cacheprovider tests/test_rq2_continuous_b6_planning_recovery_v1.py tests/test_rq2_continuous_rejection_coverage_v1.py tests/test_rq2_continuous_recovery_controller_v1.py tests/test_rq2_continuous_actual_action_contract_v1.py tests/test_rq2_continuous_four_arm_replay_v1.py tests/test_rq2_continuous_causal_policy_v1.py tests/test_rq2_continuous_debt_cohorts_v1.py tests/test_rq2_continuous_composite_diagnostics_v1.py
```

`git diff --check`通过；旧科学successor v5、implementation v2、execution v3的outer所绑定inner及
5/14/22个成员SHA256均匹配。未运行formal或solver，未生成production manifest/receipt，未清理仓库。

独立只读pre-seal审查完成：以下8文件回归228项通过（24.73s），另125组恢复cap枚举满足功率、
eta工作量与债务守恒；限定范围无阻塞实现finding。独立回归范围与主线程167项不同，不相加作为唯一测试数。

```text
python -B -m pytest -q -p no:cacheprovider tests/test_rq2_continuous_b6_planning_recovery_v1.py tests/test_rq2_continuous_recovery_controller_v1.py tests/test_rq2_continuous_actual_action_contract_v1.py tests/test_rq2_continuous_causal_policy_v1.py tests/test_rq2_continuous_four_arm_replay_v1.py tests/test_rq2_continuous_debt_cohorts_v1.py tests/test_rq2_continuous_multiday_service_v1.py tests/test_rq2_joint_deliverability_boundary_v1.py
```

审查实现SHA256为`7f9d6db4ed2a7d820dfa6a7c9c9e213dc6cf052f2399cdb6a78374615ae7128e`，
测试为`3dfe73757c98b1d23828f25fd0f5eb124233e1ad8a6cba8e33c76a3975bcf302`。
此为开发证据，不是official审查；正式封存仍需冻结验收矩阵、外层输入/轨迹绑定和fresh独立review。
