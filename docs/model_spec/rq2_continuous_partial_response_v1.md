# 连续拒绝后显式部分响应合同 v1

2026-09-16，`DRAFT_NONAUTHORITATIVE`。本合同是补缺开发，不替代完整请求规划或正式科学协议。
所有响应为明确给定的mechanism_assumption；公开CPU/PDU数据没有观测到这些动作。

## 已有合同与本次范围

`formulation.md`服务平衡及§10区分合同削减、绿电延期、永久业务放弃和非合同违约；核心实验默认
`ell_drop=0`，永久放弃即使在敏感性扩展中也占共享柔性资源。历史债务取消不等于该小时少取电。
`rq2_joint_deliverability_estimands_v4.md`§9及`src/rq2_joint_deliverability_v2/evaluation.py::execute_holdout_policy`
已有grid→CFE→recovery词典序部分响应。这证明请求短缺与业务丢失本来就是不同对象，不需为了报告短缺引入loss引擎。
旧实现强制末小时inactive，并按24小时末债务评分；这些规则不能用于当前开放连续窗口。

现有连续full-request接口只有完整履约动作，拒绝后不生成任意部分响应。本合同增加显式响应的核算入口，
仍不选择动作、不声称实现完整因果policy；原完整请求、原primary拒绝和最后已提交状态均保存。
当期永久损失、历史债务永久放弃、非合同缺口和额外救援资源均未启用。

## 请求、响应、实际功率和债务

对原臂投影后的有效请求`g_req,c_req`，显式响应为`g_served,c_served`，均非负且分别不超过原请求。
不属于该臂的服务响应必须为零；原始公共观测仍完整保留。采用既有有效量规则与原容差，
若逐服务有效量之和与该臂合并有效请求不一致，则报告表示歧义并停止，不选择新的阈值。
响应的四个功率字段仅接受built-in int/float（bool不接受）；精确账采用其十进制表示，且显式核对
执行投影与该精确量相同。Fraction仅用于cohort工作分配，不能作为功率字段隐式转换。

`q_exec = g_served + c_served`，`s_grid = g_req-g_served`，`s_cfe = c_req-c_served`。
这些shortfall的单位为归一化功率；每小时能量为`shortfall * 1h`，不直接当作经验概率或业务损失。

在零永久损失、零非合同违约的本合同中：

```text
p_actual = baseline - q_exec + r
debt_next = debt_previous + q_exec * dt - eta * r * dt
allocated_recovered_work = eta * r * dt
```

未满足调用没有实际延期，因此不进入债务。未满足CFE调用通常意味着相应业务继续取电，不是业务被丢弃。
当`q_exec>0`仍禁止恢复；调用、事件、rest、energy、debt限额及恢复business/CFE/max-power全部使用原包络。
已到期短缺永久保留；unknown deadline不补填；本合同不因观察末端停止事件或清债。

为了复用原物理/cohort校验，内部构建executed-obligation投影；它只是对已声明响应的计算输入，
不是新观测源。record同时保留原`CurrentObservation`与投影后的候选step，并重放核对二者映射。
不能把投影的较小请求替换原观测、旧full-request记录或冻结结果。

## 提交与停止语义

| 情形 | 记录与状态 |
|---|---|
| 来源gap/split/provenance错误，动作缺失或表示歧义 | unassessed；不提交、不消费后缀 |
| 响应超过原请求、服务功率或cohort分配错误、原包络失败 | 保存声明/错误；不提交，不解释为所有策略不可行 |
| 局部业务候选合法，但应满足的grid请求存在短缺 | 保存候选及机制grid短缺；不提交为可延续状态，不消费后缀；实际网络后果未知 |
| grid足额、CFE响应不足，且原业务包络满足 | 提交显式机制状态，同时保留CFE shortfall；不称完整联合履约 |
| 两项请求均满足 | 提交显式机制状态；是否按时恢复仍由cohort单独判断 |

NETWORK/CFE单服务臂仅评价其负责的服务，未纳入的服务短缺为null。CFE-only的局部状态可提交不证明电网安全。
grid请求足额也仅证明给定机制调用账匹配；该接口不含网络潮流、响应时间、minimum-event-power或调用ramp认证。
原拒绝小时与显式响应只计一个输入小时。grid短缺候选与已提交小时分别计数，原状态停在最后提交小时。

## 手算验收与剩余工作

1. baseline=1，g=.25、c=.5、call cap=.5；给定g_served=.25、c_served=.25、r=0、p=.5。
   请求总量.75不改写，CFE短缺.25、grid短缺0、新增债务.5。eta=.8时清偿需累计恢复功率小时.625；
   沿既有每小时cap=.3125的fixture需两小时，不能声称一小时清偿。
   未满足CFE的.25不形成cohort、不登记为lost work。
2. baseline=1，g=.75、c=0、cap=.5；给定g_served=.5、p=.5。局部业务候选可合法，
   但grid短缺.25，保存候选并停止；不得用“最大可做.5”把完整硬请求改成.5。
3. 连续调用已到maximum duration，再声明正调用仍拒绝；把响应改名为损失不能绕开合同。
4. gap/来源漂移、超请求响应、negative power、欠/超分配、unknown/逾期、未来扰动、同小时计数、历史拼接均须验证。

后续完整策略仍需在结果前固定动作选择与独立policy身份、训练容量接入、响应时间/ramp/min-event、
风险事件/分母/权重、未知后缀与删失合同。若要永久损失敏感性，须另定义逐笔
`incurred = recovered + remaining + explicit_permanent_loss`和已有miss不可抹去，以及共享资源/损失限额与证据。
当前未选择正式策略或科学参数，不将这些扩展当作主线必需的自动救援。

允许origin为policy_decision、separate_planning、physical_execution、shared_execution的halted原策略。
input_validation不建立此cursor；effective表示歧义在response_accounting独立拒绝，不能靠显式动作掩盖。
policy_decision的full-call超baseline可以进入本接口。B6独立共享后继和本接口是不同开发合同，
本接口只接受原PolicyCursor，不接组合cursor，不形成自动串联或优先链；完整组合policy身份仍待开发。
q_exec=0时执行投影due_hour=None，不为未执行请求创建债务；原观测due_hour保持原值。

## 开发验证

实现：`src/rq2_joint_deliverability_boundary_v1/partial_response.py`；
测试：`tests/test_rq2_continuous_partial_response_v1.py`（37项）。
接口只接受显式typed动作，合同身份固定为`explicit_partial_response_zero_loss_grid_shortfall_stop_v1`；
它不是完整policy_id，局部确定性重放不替代外层输入hash/轨迹身份。
`grid_service_failure/cfe_service_failure`仅对通过局部业务校验的candidate返回布尔值；无candidate或未纳入该服务时为null。
短缺量本身在包络失败时至多是声明值的算术诊断，不能被统计为已执行真实服务结果。

主线程以下7文件相关回归186项通过（2.20s），包含grid短缺在原容差内、等于容差及超过容差三种边界。
解释器为`D:/Miniconda3/envs/compute/python.exe -B`：

```text
python -B -m pytest -q -p no:cacheprovider tests/test_rq2_continuous_partial_response_v1.py tests/test_rq2_continuous_b6_planning_recovery_v1.py tests/test_rq2_continuous_actual_action_contract_v1.py tests/test_rq2_continuous_four_arm_replay_v1.py tests/test_rq2_continuous_causal_policy_v1.py tests/test_rq2_continuous_debt_cohorts_v1.py tests/test_rq2_continuous_recovery_controller_v1.py
```

只读领域设计审计确认上述请求/响应/功率/债务分账与既有规格一致；独立pre-seal实现复核已确认数值finding闭合。
首轮审查发现Fraction功率可在精确shortfall与float投影debt之间产生差值；现限定功率数值域并核对投影，
新增8项类型反例及1项canonical十进制守恒/候选不能替代origin测试。独立fresh相关回归186项通过。
投影角色是正式组合/导出的待验项：必须携带外层record和原observation，不得把candidate anchor导出为source。
当前局部接口不是来源验签器，没有将此边界标记为正式完成。
旧冻结协议、实现和结果保留；未运行solver/formal，不改变科学或运行门。
旧prefix/composite `--verify-existing`均exit0、replay_matches=true，分别24组合/1038记录与32组合/1330记录。
旧科学v5、implementation v2、execution v3的outer绑定inner及5/14/22个成员SHA256仍匹配。

独立pre-seal审查最终结论：限定范围没有未闭合实现finding；targeted 37项、相关186项通过，
另枚举四臂20组合法/短缺/超包络组合，无提交、债务或failure分类差异。此为开发审查，不是official verdict。
审查实现SHA256：`7c39bee9adb551096224b6f72bb301896125f40ca918c12132bd3586d2790e26`；
测试SHA256：`d7b6548d772ae1ecb5a10ecdfee487d65c23d1a9ad3e251898f4aca8ddd7b9f0`。
