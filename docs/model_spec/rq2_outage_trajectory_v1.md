# 多小时事故态轨迹kernel

日期：2026-09-16。状态：`DRAFT_NONAUTHORITATIVE`。
实现：`src/rq2_joint_deliverability_boundary_v1/outage_trajectory.py`。

## 范围与显式合同

本组件消费已经审计的event-blind normal候选与原事件表，建立共同H下的事故态DC网络LP。
逐小时旧corrective约束不再被拼接为连续证据；新的`actual_ramp`连接实际发电的相邻小时。
旧normal、corrective、candidate及冻结协议源码不修改。当前只有build入口，没有事故态solver适配、
结果认证或末态导入器。

所有调用必须显式给出：

- `commitment_response_mode=fixed_normal_commitment__outage_as_availability`；
- `interhour_ramp_scope=committable_only_inherited_normal_scuc`；
- `information_mode=offline_full_event_path`；
- `forced_trip_rule=generation_zero__downward_ramp_exempt_on_1_to_0_availability`；
- 每个原generator event的`(event_id,uid,return_limit_mw)`，无默认值；
- 独立`ActualGridOrigin`及`mechanism_assumption`角色；
- `weighted_total_curtailment`及严格正权重，或`fixed_curtailment_vector`及完整向量。

repair cap有限非负且不超过源Pmax，绑定原event_id/uid。该值没有公开运行识别依据，明确是机制参数。
源发电/网络数据仍是benchmark输入；不能把新的repair规则、origin或未来事件信息标为真实观测。

## 物理约束

每小时都有实际拓扑DC方程、continuous热限、lossless DC1界与节点平衡。
事故支路flow为0；修复恢复源拓扑，没有新增支路或DC1跨小时ramp。
发电bounds继承旧corrective：不可用或计划off时0；committable可用时按normal commitment施加源小时界；
fixed等于profile；curtailable处于源小时界。non-fixed可用机组保留`abs(P_actual-P_normal)<=R`。

committable的普通相邻边沿用normal startup/shutdown allowance：

```text
P_actual[t]-P_actual[t-1] <= R + Pmax * normal_startup[t]
P_actual[t-1]-P_actual[t] <= R + Pmax * normal_shutdown[t]
```

availability从1到0时，只豁免故障机组的下降ramp；当前功率仍强制0，其他机组不获豁免。
availability从0到1时，对所有generator类型施加显式`P_actual[t]-P_actual[t-1]<=return_limit[event,uid]`，
替代该边的普通上升ramp；committable的下降ramp仍保留。
fixed恢复profile超过return cap，或committable计划on且Pmin超过cap，均如实留下不可行轨迹，
不降低Pmin、不自动延迟上线、不免费增加Pmax跳变。

normal commitment是唯一计划组合，本模式没有actual u/y/z或actual dwell。
forced outage不记为自愿shutdown，outage小时不重置normal minimum-down，repair不伪造normal startup。
若需要事故性启动、延迟re-entry或outage计minimum-down，应建立新的actual commitment合同。
curtailable/fixed没有偷偷加入跨小时R限制；fixed仍由profile决定，curtailable仍受同小时response包络及修复cap。
事故后实际出力可在既有包络中继续递推，不强制瞬间等于normal。基线精确重合期限保持未注册。
与旧corrective一致，本层未增加事故态备用恢复要求，不声称完整UC或安全认证。

## 实际原点与时间

`ActualGridOrigin`包含全机组实际P、availability、前一source hour、GridIdentity及来源角色。
它必须与normal输入同split/trace/seed/source及边界，不能传入`GridCarry`冒充实际事故状态。
首版只接受显式机制原点；中途窗口若声明该原点，只是新的条件机制情景，不能声称从原trace前缀继承。
真正derived前缀交接还需实际轨迹见证，本组件拒绝裸snapshot标`derived_dispatch_witness`。

source_hour为1-based，事件仍为原zero-based half-open区间。已有前一来源小时的窗口需核对原事件决定的availability。
source起点的stationary-down事件表示已经处于故障，incoming availability必须down；不能推断index0刚发生trip。
实际初态功率按源availability/计划组合界校验，已知前一profile另核对committable的小时min/max乘初始组合、fixed精确profile及curtailable小时界。
本组件不证明机制初态的历史网络可达性。

## 目标、身份与下游边界

`fixed_curtailment_vector`将每个`c[t]`精确fix为给定值；
`weighted_total_curtailment`最小化`sum(w[t]*c[t])`，全部权重严格正且进入identity。
无事故小时`c[t]=0`，事故小时`0<=c[t]<=DC_requested[t]`；修复后不能用未注册的额外削减偷偷消除衔接问题。

身份覆盖normal输入、owned candidate、完整事件表、实际原点、repair caps、objective及运行源码。
重新审计normal assignment，并核对原candidate execution依赖；调用者必须提供预存摘要。

weighted解只可能成为某个离线标量化问题的incumbent；不保证向量唯一，也不证明因果响应。
旧逐小时最小值不能自动组成跨小时可行向量；是否冻结某个向量为下游硬调用、
选择因果controller或多场景非预见性约束、以及是否联立业务服务，仍须完整科学协议。
本组件不产生`grid_need`正式输入包、容量证书、official gate或事故安全结论。

## 当前验证

27项针对性测试通过（9.42s），包含：单小时包络全部满足但跨小时违反5 MW ramp的反例；
forced trip/repair分离；cap19<Pmin20不放宽；修复后实际25 MW可不同于normal30 MW；
fixed/curtailable修复cap差异；stationary-down起点；身份/来源/原事件/模式缺失拒绝。
另覆盖跨chunk首小时修复保留原事故身份、前序actual availability，以及fresh import依赖闭包精确匹配。
测试为事故态构模和解析赋值；四次3h及一次1h normal基线微型求解各限1秒/1线程，用于提供真实owned输入。
加入最后两项测试前，outage/candidate/normal/carry四文件176项相关回归通过（26.62s）；源代码此后未变。
独立pre-seal复跑当前27项通过（9.11s）；前序小时界和测试计数两项文档finding已同步并完成最终复核，限定范围无开放finding。
新事故态LP尚未运行solver；本kernel不提供结果赋值见证、实际末态交接、因果策略或安全认证。后继赋值组件见下节。

当前源码SHA256：`9982f430a19f9c3b365d14419665bf2514d99b4d5b178444842e2c7b6fd733bf`；
测试SHA256：`a52950781cc12052e80bc2909b3bb51e058aa1326a32d1de8e96452661b4cf97`。
实际命令为`python -B -m pytest -q -p no:cacheprovider`加上述四个对应测试文件；最后两项补充后单独重跑outage测试文件。

## 赋值见证与同一轨迹切片开发合同

后继已实现为`outage_assignment.py`，验证状态和接口范围见`rq2_outage_assignment_v1.md`；以下为该组件的设计依据。

下一组件先消费完整variable assignment，fresh rebuild本模型，分别核对全变量inventory、有限数值、
fixed值、变量界及全部active约束；保存原值与残差，不round、repair或根据失败放宽容差。
它证明的是声明容差下给定赋值的可行性，不能仅凭赋值签发optimal bound或唯一削减向量。

首版实际末态交接只限同一完整outage problem及同一已接受完整assignment的切片重放。
仅normal_candidate_id相同不足以绑定轨迹：suffix重新优化可能选择不同actual路径，特别是weighted目标的退化解。
因此必须同时绑定full outage identity、full assignment identity、normal candidate和绝对cut source hour；
原事件、repair参数、目标及information mode继续由完整问题身份绑定，suffix只消费原赋值对应小时。

actual末态独立保存全机组实际generation、原事件确定的availability、cut时active原事件和source hour，
角色为`derived_offline_assignment_witness`。normal边界另从同一normal赋值前缀回放，不能用actual出力覆盖normal GridCarry。
跨cut持续事故不重新生成trip；repair匹配原event的返回限额。相邻不同事故须同时处理旧机组repair与新机组trip。
切片交接不提高信息等级，仍是offline full-event-path证据；不能作为因果控制器或完整历史可达性证明。

验收至少包括：完整与分块重放一致、cut正好位于trip/repair/持续故障、修复后actual与normal不同、
错assignment/原事件/时钟/split身份拒绝，以及缺变量、多变量、非有限值、fixed值和物理约束篡改拒绝。
完整事故态solver适配在上述见证后接入；原逐小时标量curtailment的结果门不能直接适用于本模型。
