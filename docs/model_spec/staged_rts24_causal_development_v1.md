# 网络证据驱动的连续三评价后继

2026-10-22，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。接续[公共查询规格](staged_deliverability_rts24_development_v1.md)与[构建交接](../plan/continuation_handoff_20261022_rts24.md)。本后继实现连续业务转移和证据消费，不改变B1–B3、原C审查或build_01绑定源码。它没有公共网络求解结果或运行权限。

## 证据与数值口径

[child LP审计](../../src/staged_rts24_child_optimality_v1.py)只接收已绑定经济父点的min_curtailment/min_meter/max_meter查询，先重核原独立primal和父经济KKT，再核完整child dual。max_meter按min(-meter)审计，因此其primal_objective和numeric_dual_constant为负meter口径，不能直接当正取电上端。连续内核使用同一见证的meter值作为声明容差下的数值上端，仍非rigorous bound。

采用固定变量机械消元：参考角、相等gen上下界、固定meter、零curtailment及停运branch的flow/零流方程；仅含固定量的约束dual为零。其余box lower-x、x-upper，connection=m-c-C≤0，curtailment-meter≤0的乘子均非负。证据绑定query/point/reduction SHA。独立重算stationarity、互补及Lagrangian常数与primal的绝对差，沿用1e-6；所有派生系数和结果必须有限。冗余但未消元的约束允许不同合法dual分配。

三目标梯度(dm,dc)分别为(0,1)、(1,0)、(-1,0)。meter stationarity为dm-λ_POI+κ-ρ-mL+mU；curtailment为dc+λ_POI-κ+ρ-cL+cU。gen/flow/angle按公共原式重算；Lagrangian常数保留phase-shift项。结果只说明声明容差下primal/KKT/gap一致，`rigorous_bound_certified=false`，不输出正式LB或容量证书。原audit_point的minimum_established=false不变。

业务量继续用Fraction记账。数值raw/恢复端点采用Q(str(returned_float))编码解释器返回的有限非负十进制，保留原浮点见证与证书，不做舍入、截到X或把负值改为零。该有理数是数值决策输入的确定编码，不声称精确数学最优值；所有实际P另核完整点。目标边界处的数值敏感性、native提取/终止和正式结果误差处理仍需后继审查。

## 连续转移

[业务内核](../../src/staged_rts24_causal_v1.py)使用独立ExecutionState。轨迹身份绑定fixture、plan、clean_path、method、参数、首小时、登记结束和观察结束；ledger保留同一trajectory/accounting period。每次prepare/accept核对身份与完整历史可达性，summary从同一fixture取得时间边界，不接受外部缩短窗口。

1. prepare从当前小时生成预期请求。P0健康经济点必须有完整父KKT；实际故障的reference raw必须有child最优性证据；固定余量与完整时序方法均保存实际拓扑的恢复min/max证据。instantaneous不请求恢复两端。准确角色、负荷、F/X、事故、父完整点/证据均一致。参考P0超C或完整raw超当前合法X则拒绝；未知或缺证据不变成零请求。
2. propose只读取已核当期PreparedHour和前缀state。延续B1的grid优先、green随后使用剩余D、q+r≤D、调用/恢复互斥、已到达批次EDF和业务/X预算。full_temporal恢复受实际K、网络上端、Y和债务限制，并核真实P没有低于网络下端；fixed_headroom使用原先固定R_fix；instantaneous只选择当期延期。后两者自己的连续账本保持假想安排口径。
3. accept重新prepare并重算固定策略，拒绝被篡改的准备输入和proposal。策略选定P后才审核actual_P，准确P/零额外curtailment、同一P0父点、实际拓扑和独立完整点审计缺一不可。已有最优端点已排除P或P>C时可保存已知失败，不能编造actual点。
4. full_temporal的硬约束或actual点失败保留最后已接受ledger/carry并停止；CFE承诺/实际缺口可作为已观察服务失败保留并继续，不能在summary中变成通过。简化方法继续自己的hypothetical ledger；proposal_ledger_applied与actual_accepted分开，后者仅full_temporal可为真。其恢复假设省略的真实约束仍由完整回放单列。
5. 债务、首次期限缺口、业务调用与X调用的能量/次数/持续/休息跨阶段延续。未投运资源仍由当前观察决定。全部到达任务保持工作守恒；登记外继续有业务。summary区分方法判断、完整约束回放、永久逾期、右删失和未完成覆盖，不由actual路径推导完整F/X背书。

完整C/每事故F及raw的139节点合同层不由这一actual-path内核执行。记录明确fx_contract_status=not_evaluated_by_actual_path_step；原请求图和合同业务必要条件失败仍保留。接通该层和反事实完整F/X时序是独立未完成项。

## 独立审计与验收

[独立业务审计](../../src/staged_rts24_causal_audit_v1.py)不调用writer的initialize/prepare/propose/accept。它从空前史账本和fixture身份开始，重审保存网络点/父KKT/child LP，独立按已重建cohort选固定策略，重算功率与两类服务余额、约束标志、有效恢复、期限首次缺口及全部carry，最终逐字段比较state。测试在禁用writer四个入口时仍可审计，另拒绝标签拼接、缩短summary窗口、伪造预算、功率和逾期历史。

[解析例](../../experiments/staged_rts24_causal_examples_v1.py)为显式三母线/单机组测试数据，未使用公共RTS-24数值点。P0=100，正常恢复区间[40,150]，声明故障时[40,60]，最小raw=40；手给primal/dual。早Y时q40→r40守恒；晚Y时fixed_headroom在h2假定恢复40但实际CFE不足，full_temporal到期保留40缺口、h4补做后仍保留逾期；instantaneous不恢复。该例的投运标志改变而物理网络相同，只验证carry不重置；公共工程前后模型构建证据仍单独见build_01，不称已完成跨工程公共执行。

验收覆盖：[child LP测试](../../tests/test_staged_rts24_child_optimality_v1.py)的可行非最优拒绝、正恢复下界、max负号、phase-shift常数、消元/冗余dual、完整数组/finite/hash；[连续测试](../../tests/test_staged_rts24_causal_v1.py)的三方法独立账本、actual闭环、晚Y误判、非预见性、正下界过度延期拒绝、缺/错证据、状态/期限篡改及独立审计。普通测试阻断SolverFactory。

## 成本与未完成项

当前每次prepare重审完整前缀，accept又prepare一次，summary也审前缀；完整state摘要及内嵌网络数据重复编码。T小时的前缀审计和摘要工作按Σt增长，不能按一次数值query数估总成本。对象/完整网络frame去重、合法同操作复用、持久化schema和fresh child成本尚未优化或测量。普通测试wall不充作公共整链预算。

本包未实现journal/文件发布、关闭/重开、fresh-process保存证据重放、未决attempt及终态持久化，也未实现native证据提取。下一步在独立journal后继中保存输入/完整父子证据/接受或假想状态，独立重放并覆盖提交未知/拒绝/缺输入/数值未决与收尾；任何代表性运行先登记具体包和资源。公共真实数值点、C整体性能、D/E资源和完整F/X时序仍OPEN。
