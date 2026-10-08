# 固定业务实际功率与连续事故网络的联合检查

日期：2026-09-16。状态：`DRAFT_NONAUTHORITATIVE`。
实现：`src/rq2_joint_deliverability_boundary_v1/business_grid.py`。

## 范围与输入

本组件验证一条已经由固定容量策略提交的完整业务前缀及对应网络赋值，不选择业务动作、不求容量，
也不将离线事故削减向量注册为外生grid request。
输入为`CapacityPolicyCursor`、调用者预存的prefix digest、完整`OutageTrajectoryInputs`及三个显式机制声明：

- `power_mapping=linear_workload_power_no_idle_offset_v1`；
- `source_pairing=declared_power_source_and_workload_pairing_mechanism_v1`；
- `parameter_role=mechanism_assumption`。

`normalized_unit_mw`使用正的canonical decimal string，如`20`或`0.1`，不接受float、指数或多余尾零。
线性映射没有idle offset是本接口的显式机制假设，不是公开CPU/PDU数据已识别的事实。
首版network只作为weighted模式的物理包络模板使用；其目标和curtailment变量在新模式中被替换，
不能传入已有fixed-curtailment向量而假称同时遵守该向量。

入口调用`export_prefix_handoff`从canonical zero origin重放全部原始observation和action，核对预存摘要。
只接受非空、全部已提交、长度与network horizon完全一致的前缀。首次拒绝后的未知轨迹或中途裸snapshot不在范围内。
split、outage seed、初始绝对power source hour及全部后续power hour必须一致，workload连续性由原prefix校验。
双方source hash/trajectory名称可处于不同命名空间；grid input identity与prefix digest同时绑定它们，
不覆盖任何一侧，也不把机制配对描述为真实同钟观测或经验联合分布。

## MW映射与数值

先用Fraction保存原始归一化值和decimal scale，逐小时计算：

```text
baseline = scale * workload_occupancy
grid = scale * grid_served
cfe = scale * cfe_served
recovery = scale * recovery_action
actual = baseline - grid - cfe + recovery
```

必须精确满足`baseline == Fraction(str(normal.dc_requested_mw[t]))`，且actual不超过
physical maximum及connected capacity。原始grid/CFE请求、执行分量、recovery和各自shortfall都保留。
None表示该臂不承担对应服务，不转换为已完成的零短缺。

进入Pyomo前进行一次float转换；保存精确分子/分母、float、hex与转换误差。非有限或正值下溢至0拒绝；不round/clip。
网络赋值除了canonical `1e-6 MW`残差检查，还用原始精确业务MW、源数值的确定性decimal表示和完整赋值
重新计算每个节点的功率平衡，采用同一`1e-6 MW`阈值。浮点投影不能掩盖精确映射下的失衡。

## 网络模型与审计

新建fresh outage物理骨架，保留全部generation bounds、same-hour redispatch、actual interhour ramp、
forced trip、原event repair cap、AC/DC拓扑和热限。删除该新实例的旧balance/objective/curtailment组件，
再建立每小时`actual_dc_power`参数和完整节点平衡，目标为常数0。原outage源码和输入对象均不修改。
这是单独的prescribed-business-load模型；没有遗留可自由优化的减载变量。
无事故CFE减载和高于baseline的恢复负荷均可被表示，不能借原event-only非负curtailment规则阻止或裁剪这些动作。

`audit_business_grid_assignment`再次fresh build，要求变量inventory完整、值有限，分别记录fixed、bound、
active constraints及精确映射节点平衡残差。失败不会修改原业务cursor、债务、request、恢复或deadline历史。
见证只能由审计入口构建，身份包含完整网络输入、业务prefix及其实现闭包、映射声明、数值投影与本实现源码。

## 四臂及结论边界

- NETWORK核对grid执行后的实际用电；CFE不属于该臂。
- CFE可接受网络物理检查，但原grid request未被该臂执行；grid适用性为false，grid shortfall为None，grid证书仍null。
- JOINT同时计入grid/CFE/恢复。已提交轨迹可能存在CFE shortfall，不能据提交成功推断完整请求已满足。
- B6仅核对已有共享实际执行轨迹，不验证或恢复其separate-planning双账。

`physical_network_assignment_valid`只表示给定模型下该赋值通过；
`effective_applicable_requests_fully_served`另按各臂原有效请求的精确shortfall是否为零判断。
后者也不证明债务按期完成。`full_service_completion`、grid obligation证书、causal grid dispatch证书保持null。
业务策略可按当前信息执行，但网侧赋值仍可使用完整未来事件；组合仍标`offline_full_event_path`，formal/security=false。

## 验证状态

最终37项targeted通过（20.88s），六文件193项相关回归通过（53.05s）；独立pre-seal另复跑37项通过（20.61s），
限定范围无开放实质finding。事故trip/repair cap、支路flow bound、来源错配、双namespace绑定及fresh依赖闭包均已覆盖。
双机repair fixture明确minimum-up=5以保持完整三小时normal on计划；偏移power source origin时同步偏移due hour。
这些fixture修正后再做最终回归，未放宽模型约束或数值门。
测试只对本模型构模和手工赋值；四次normal输入微型求解各限1秒/1线程，未运行本联合模型的solver或正式实验。

使用`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`，相关文件为
`test_rq2_business_grid_v1.py`、`test_rq2_outage_trajectory_v1.py`、`test_rq2_outage_assignment_v1.py`、
`test_rq2_continuous_capacity_policy_v1.py`、`test_rq2_continuous_aggregate_response_v1.py`、`test_rq2_continuous_prefix_handoff_v1.py`。
源码SHA256：`dabb7d9078bf4c914a0a48aab0cc262be57b4acff1ec8d91cb498b661fea2a2c`；
测试SHA256：`57b09c2cb909d0b417acd31dfe4a798d0ae2a73db51675545150a7bd51347e84`。
`git diff --check`通过；旧grid/solver及已跟踪configs无diff。
下一步在这些检查闭合后接入固定业务轨迹的短时网络可行性求解，保持动作及机制输入不变。

后续更新：该短求解入口已开发为`business_grid_short_solve.py`，验证状态见
`rq2_business_grid_short_solve_v1.md`；上述37项为构模/赋值组件自身的历史验证范围。
