# 多小时事故态短求解与原生结果连接

日期：2026-09-16。状态：`DRAFT_NONAUTHORITATIVE`。
实现：`src/rq2_joint_deliverability_boundary_v1/outage_short_solve.py`。

## 执行与预算

消费已绑定完整normal候选、原事件、actual origin、repair参数和目标的`OutageTrajectoryInputs`。
显式`Rq2SolverSpec`与`GridDevelopmentBudget`经验证后，内部fresh build并检查真实变量/约束规模，再创建版本核对的solver。
预算沿用现有类型的硬上限：每次不超过30秒、4线程、168小时、20,000变量、100,000约束；
本入口无论预算的call上限多大，都只允许一次实际调用，并核对该次配置秒数不超过总预算。
时间限制是传给solver的配置，不声称约束整个Python进程的wall-clock。

不重试、不换solver、不做zero-DC替代、无production写入。事故态求解不会重新运行normal或重优化suffix。
原始输入与执行identity在执行前后比较；合同标识为固定literal，漂移拒绝。
执行身份覆盖spec、预算、solver/Pyomo等版本、已有依赖闭包和三个事故态组件源码。

## 原生证据与赋值

保留全部solver/problem/solution记录的typed enum、原始数值类型/表示和有限数值投影。
要求唯一solver/problem记录、一个minimize目标，完整变量/目标label映射；重复/未知label、缺used变量均拒绝。
`load_solutions=False`后显式load。仅允许带理由记录的canonical fixed常量或完全unused、无界连续变量补全；
这些补全不标为solver观测。native+completion与loaded全变量快照须相同。

求解前、load前、load后结构，以及fresh canonical结构相同；load前初值不得被隐式更新，options和runtime版本亦核对。
物理赋值由`audit_outage_assignment`重建全模型独立核验，固定1e-6容差。
严格solver feasibility tolerance还参与最优目标验收，不能把更宽物理容差冒充solver设置已满足。

`assignment_witness`与solver lineage分开保存。目标映射不一致或runtime漂移可能使lineage失败，
已经得到的canonical可行赋值仍只是数学模型下的独立赋值见证，不能被称为已确认solver incumbent。
timeout带完整可加载赋值时也可保留该见证；无解、缺变量、load失败或多个solution不会生成有效owned最优区间。

## 两种目标的结果边界

fixed向量模式：各小时`c[t]`由canonical模型精确fix，目标恒0；提供固定向量可行见证，
`development_objective_interval=None`。native `[0,0]`不代表grid调用为零。

weighted模式：保留逐小时`c[t]`和`w[t]*c[t]`贡献。只有满足以下条件才提供开发级标量目标区间：

- native typed ok、optimal/globallyOptimal与唯一optimal solution；
- 无执行/lineage错误，canonical赋值通过且残差不超过solver spec；
- finite `0<=LB<=UB`、`LB<=canonical objective`；
- canonical objective及UB位于`[0,sum(w[t]*requested[t])]`；
- UB与canonical objective差不超过`min(spec.feasibility_tolerance,1e-9)`；
- native objective若存在，与canonical objective在同一阈值内相等；
- `(UB-LB)/max(abs(objective),1e-12)`不超过事前spec gap。

使用严格非负域，负数raw bound保留但不签发开发区间；不裁剪raw bound来通过门。
此区间只属于offline scalarized objective，不是逐小时削减界、唯一`grid_need`、业务容量或条件容量X证书。

所有原生infeasible报告仅保留在raw enum记录，不继承旧corrective的HiGHS error/infeasible特殊验收。
`native_infeasible=False`、`infeasibility_certificate=None`；失败不等于数学不可行。
始终保持`external_grid_need_trace=None`、`causal_policy_certificate=None`、
`information_mode=offline_full_event_path`、formal/security=false。

## 开发验证

测试入口：`tests/test_rq2_outage_short_solve_v1.py`。当前40项通过（25.46s）；六文件251项相关回归通过（76.57s）。
五次真实事故态求解限定小型H=2/3模型，每次1秒/1线程，另两次normal微求解生成已审计输入；其余solver故障由内存假结果注入。
正目标例每小时20 MW削减、权重2/3，逐项贡献40/60与原生/重算目标100一致；fixed同向量目标0且不产生调用区间。
覆盖缺失/重复/未知变量、非有限值、多记录、timeout、无解、原生目标缺失或不一致、界倒置/超域、
preload/load篡改、根/约束失活、options/version漂移及solver创建前预算拒绝。fresh导入依赖闭包相等。

实际使用`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`，相关回归文件为
`test_rq2_outage_short_solve_v1.py`、`test_rq2_outage_assignment_v1.py`、`test_rq2_outage_trajectory_v1.py`、
`test_rq2_continuous_grid_candidate_v1.py`、`test_rq2_continuous_grid_normal_v1.py`和`test_rq2_continuous_grid_carry_v1.py`。
源码SHA256：`166bbdffc16f3f1a6cf412dff626338d38e38a741997e4ec7eb9a66932f10139`；
测试SHA256：`7a79f494fd4b091529c8a9fdc73b7cd36006e85cb9dedaaa496ae6bf3073a57e`。
独立pre-seal另复跑40项通过（25.85s），当前限定范围无开放实质finding。正式规模、完整continuous输入发布、机制参数与因果/完整服务证书仍待完成。

## 下一主线连接（待实现）

当前curtailment是相对normal请求的净减载；它尚未同时承载业务grid/CFE调用和恢复。
业务controller/planner的实际功率另按baseline-call+recovery核算，二者不能靠变量同名或单位换算自动合并。
下一步先验证固定业务动作的实际MW轨迹与事故网络的共同可行性，保持已注册业务请求与债务账，
而不是直接把本离线优化向量选成外生grid_need。具体协议和验收以blocker的“业务动作和恢复后的实际节点负荷”条目为准。

后续更新：固定业务轨迹的构模及赋值检查已由`business_grid.py`实现，见`rq2_business_grid_v1.md`。
37项targeted与六文件193项回归通过，独立pre-seal限定范围无开放实质finding；该联合模型的owned求解尚待接入。

该owned入口后续已开发，当前验证状态见`rq2_business_grid_short_solve_v1.md`。
