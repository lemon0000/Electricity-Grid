# 固定因果补救 controller 与组合策略身份 v1

日期：2026-09-13。状态：`DRAFT_NONAUTHORITATIVE`。本轮在显式实际动作合同上固定动作生成规则，
作为RQ2连续服务的机制开发。配置、实现与测试分别为：
`configs/rq2_continuous_recovery_controller_v1.DRAFT.yaml`、
`src/rq2_joint_deliverability_boundary_v1/recovery_controller.py`、
`tests/test_rq2_continuous_recovery_controller_v1.py`。

## 策略选择与信息边界

组合规则名为`primary_then_permanent_shared_recovery_v1`。初始化时提供原arm与primary/recovery两个FixedPolicy，
包括固定量化精度；尚未接收任何小时观测时即生成policy_id。
policy_id以SHA256绑定arm、两阶段规则与精度、触发阶段、同小时切换和永久共享语义、停止规则及机制证据类别。
这是实现内的策略身份，不是预注册、时间戳或签名。手工重建整个对象及身份属于另建候选，不能证明其真实事前登记。
正式应用仍需独立绑定代码、配置、输入和注册时间；本轮不seal，也不生成运行授权。
YAML通过`CompositePolicy.from_config`构造：schema、顶层字段清单、rule、trigger_stages、transition、failure、evidence_class及关闭的门逐项校验，
primary/recovery完整构造成FixedPolicy。语义字段必须与实现及policy_id一致，否则拒绝。
fixture只是合成测试数据入口，不属于policy_id；数据、envelope与period仍作为轨迹输入另外携带，不能把同策略身份当成同实验身份。

primary沿用原固定规则；仅在`physical_execution`或`shared_execution`拒绝时触发补救。
触发规则只看记录阶段，不解析错误字符串来选择更有利的策略。`input_validation`、`policy_decision`或
`separate_planning`拒绝保持未评价并停止。这些未覆盖的拒绝类型不推断为不可补救或数学不可行。

进入补救的首个观测就是原拒绝观测，本小时仍从最后已提交物理状态出发。
补救只根据本臂已提交的共享物理/cohort账、当前观测及固定精度，调用既有`_choose_actions`：

1. 完整履行本臂原网络/CFE投影请求；有效调用时恢复为0。
2. 空闲时恢复上限取当前business headroom、maximum recovery power与debt/eta的最小值；CFE相关臂另受当前CFE-compatible surplus约束。
3. 恢复向下量化，再按known deadline从早到晚、同deadline按出生小时，unknown随后FIFO分配精确工作量。
4. 动作通过既有`advance_actual_action`及原包络后才提交。选择/表示失败或校验失败，均保持未评价并停止，不再搜索替代动作。

复用旧选择器也保留其B6 effective分解一致性检查；阈值边界不一致仍显式拒绝。本轮不放宽任何数值或科学阈值。
两阶段调用的都是固定机制规则；补救阶段使用共享物理账，而非B6分离planning账。若共享规则仍无法满足完整请求，
本小时实际状态保持未评价，不能通过裁剪请求、引入救援资源或消除债务来推进时钟。

唯一advance入口接收一个`CurrentObservation`，没有未来序列、horizon长度、forecast或外部动作callback。
策略参数不会根据后缀结果调整。测试将同一历史前缀配上不同未来headroom，验证先前决策不变，
并检查整段与分块执行完全一致。此结论只覆盖实现的信息依赖，不证明输入在现实中按此时间可用。

## B6及状态审计

B6的组合策略先使用旧分离规划，在共享执行拒绝时永久切到共享恢复规则。它不是继续运行原B6策略；
后续B6分离planning不再调用，旧primary、未提交planning候选和拒绝记录完整保留。
实际动作由共享历史产生，不使用旧planning未来状态；新到达的调用和恢复继续积累事件、能量和cohort债务。
组合策略须用完整policy_id单独标识，不能把它的表现写回旧B6结果或当成B6原策略的风险改善证据。

`RecoveryDecision`保存spec、before actual cursor、当前原观测、阶段、错误和after actual cursor，
并确定性重放校验。`CompositeCursor`绑定policy_id与spec、primary参数与arm、首个原拒绝观测及相邻补救状态链。
观测身份先于动作选择校验。若选择阶段失败，after为空，错误保存在decision；
若动作已生成但校验失败，after保留ActualActionRecord中的尝试动作与未评价状态。
两种情况均不推进物理账，且禁止消费后续小时。
命中切换阶段的halted primary必须携带同小时补救记录；即使补救也失败，仍须保存该记录。
直接删除补救记录或手工构造仅含该primary的同身份cursor会被拒绝，不能在同一policy_id下绕过自动切换。

## 计数和解析例

`summarize_composite_policy`分开报告primary accepted、recovery validated和原拒绝小时。
同一小时的原拒绝与补救决策只计一次输入：

`submitted_unique_hours = len(primary.records) + max(0, len(recovery_records)-1)`

`validated_unique_hours = primary_accepted_hours + recovery_validated_hours`。

submitted包括送入接口但被身份/数值/包络检查拒绝的输入条目，不能用作已验证服务时间或真实风险分母。
最后已验证小时、remaining_debt和cohort状态从最后提交的物理账取值；不把未评价小时之前的状态说成该小时末状态。
`risk_probability=null`、`completion_claim_allowed=false`、`formal_result=false`。

48小时合成fixture沿用旧causal配置：小时23/24/25各grid=CFE=0.125，eta=0.8，shared headroom=0.3125。
network-only、CFE-only、joint-correct沿primary走满48小时；B6原primary在26拒绝，原接受前缀为25小时。
组合规则在小时26/27/28选择shared恢复0.3125，债务分别降到1/2、1/4、0，后继验证23小时；合计48个唯一验证小时。
这只是固定机制的解析例，不是最低柔性前沿、最优性证明或经验策略效果。precision=2的独立机制测试保留量化余额和永久deadline miss，
用于证明不因成功目标而擦除残差。

## 验收与范围

验收覆盖四臂48小时、原拒绝/后继状态区分、唯一时钟计数、known/unknown恢复优先级、量化/迟到短缺、
未来后缀扰动、分块一致性、调用时不恢复、新调用债务、原硬调用失败、无效来源身份、未覆盖阶段不切换及策略/记录绑定。
旧actual-action合同仍支持显式给定动作；本模块是其单独的固定策略调用方，未改写旧代码、配置、记录或结果。

后续可为该组合策略建立独立的后继诊断结果包，明确primary/补救/未评价各段；尚未覆盖的失效行为仍须先补齐其实际动作合同。
真实业务参数、非零carry-in、丢失/抢占模型、正式split/coupling和真实运行风险仍未识别；
本轮所有策略与动作均mechanism_assumption，全部正式科学协议/输入/运行/claim/security门保持原状态。
本轮实际验证、独立审查和字节绑定见下文。

## 本轮实际验证

解释器`D:/Miniconda3/envs/compute/python.exe -B`。编辑前核对git状态、当前合同、执行计划与blocker；
相关进程检查未发现活跃正式运行。复用本会话已读的AGENTS.md/agent.md与karpathy-guidelines约束。
新增本轮配置、controller、测试及本文，计划/blocker追加状态；未改旧代码、协议或结果。

针对性命令：`python -B -m pytest -q tests/test_rq2_continuous_recovery_controller_v1.py`。
独立审查发现同身份cursor可缺失触发后的补救记录，现已收紧构造校验并覆盖replace/手工构造负例。
另修复配置元数据未被构造入口校验的问题，补齐trigger/transition/evidence/failure/gate/未知字段负例。
最终主线程针对性为`28 passed in 0.72s`。最终相关九文件命令：

```text
python -B -m pytest -q tests/test_rq2_continuous_recovery_controller_v1.py tests/test_rq2_continuous_actual_action_contract_v1.py tests/test_rq2_continuous_prefix_diagnostics_v1.py tests/test_rq2_continuous_causal_policy_v1.py tests/test_rq2_continuous_four_arm_replay_v1.py tests/test_rq2_continuous_debt_cohorts_v1.py tests/test_rq2_continuous_multiday_service_v1.py tests/test_rq2_joint_deliverability_boundary_v1.py tests/test_rq2_joint_deliverability_continuation_audit_v1.py
```

主线程最终九文件回归为`244 passed in 47.18s`。独立只读`sol_reviewer`复核为`28 passed in 0.84s`及`244 passed in 47.53s`，
两项pre-seal finding均闭合，当前未发现开放实现finding；下表三项hash与最终字节一致，diff检查通过。
该结论仅为DRAFT范围的non-authoritative pre-seal findings，不是official verdict、receipt或实验授权。

旧前缀交付`--verify-existing`通过（24组合、1038记录、完整重放一致）；此前19项文档字节绑定及公开交付7项成员哈希均匹配。
`git diff --check`通过；旧v5 symlink环境项未重跑，仍未验证。本轮没有正式实验、solver、下载、付费查询或仓库清理。

本轮SHA256开发绑定（不是seal）：

| 文件 | SHA256 |
|---|---|
| configs/rq2_continuous_recovery_controller_v1.DRAFT.yaml | `8f392ac35dce687a166304ba144795b673449cb3b3fd5e114c8c5b46296e5e04` |
| src/rq2_joint_deliverability_boundary_v1/recovery_controller.py | `3ba4f525b404500a3254e5eb51d345deeb3945472f4d5a98e50e2a076d0859d4` |
| tests/test_rq2_continuous_recovery_controller_v1.py | `06392f6b05c6e178edfd11e48723cc8f6cbd08174c61f3886647243193ea9749` |
