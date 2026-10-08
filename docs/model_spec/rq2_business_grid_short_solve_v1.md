# 固定业务动作的连续网络短求解

日期：2026-09-16。状态：DRAFT_NONAUTHORITATIVE，开发用离线可行性检查。

## 对象与复用

实现：`src/rq2_joint_deliverability_boundary_v1/business_grid_short_solve.py`。
测试：`tests/test_rq2_business_grid_short_solve_v1.py`。
输入沿用`BusinessGridInputs`及`rq2_business_grid_v1.md`：完整已提交业务前缀、显式MW映射、
同一horizon的normal基线和事故路径。业务动作固定，恢复功率进入实际节点负荷。
信息模式仍为`offline_full_event_path`，配对、归一化与初态保持机制假设。

本入口复用`continuous_grid_candidate._solve`的内部构模、规模门、单次native求解、完整变量解析、
显式load和fresh canonical检查。资源/solver规格沿用`outage_short_solve._admit`，并要求专用purpose
`fixed_business_network_feasibility`；不复用corrective/zero-DC的特殊不可行状态兼容路径。
输入identity和execution identity在调用前后重算，绑定业务前缀、网侧输入、实现依赖、solver规格与预算。

## 结果的含义

只对单一feasible/optimal原生solution、完整native/completion与loaded赋值一致且没有load/inventory错误的
结果，调用独立`audit_business_grid_assignment`。它重建网络并额外以原始exact MW核验节点平衡，容差固定1e-6。

- `physical_assignment_witness_available`：完整赋值通过业务—网络联合检查。
- `solver_lineage_checked`：原生流程无错误，canonical赋值与solution状态合格，且solver status为ok/warning、
  termination为optimal/globallyOptimal/feasible/maxTimeLimit/maxIterations/maxEvaluations/userInterrupt/resourceInterrupt之一。
  此项不表示最优性；infeasible/unbounded/failure等termination即使附带可行赋值也不能通过。
- `owned_solver_assignment_available`：上述两项同时成立。
- `network_feasibility_status`：有物理见证时为`witnessed`，其余为`unresolved`。

timeout的完整可行incumbent仍可形成物理见证；options、目标或solver outcome不一致时独立物理见证与solver来源可信性分列。
原始`raw_solve.optimal/native_infeasible/bounds`仅保留来源报告；常数0目标的界不转换为网络调用或容量界。
`development_objective_interval/external_grid_need_trace/capacity_certificate/causal_grid_dispatch_certificate/
infeasibility_certificate`均为null，formal/security为false。
业务CFE短缺、适用性和未完成恢复仍由联合见证单列；网络可行不代表完整业务履约。

## 验收反例

真实3小时合成例的实际业务功率为17.5、23.125、20 MW，对应发电37.5、43.125、40 MW。
相同合法业务动作在4 MW/h ramp下不能取得可行网络赋值，保持unresolved；不改动作来绕过约束。
另验证CFE短缺仍保留，以及支路全窗故障时unused angle的显式canonical completion。
每次真实求解限1秒、1线程；这些微例不构成正式规模验收。

数值反例使用请求`.1099999999999999`、20 MW单位、第一小时发电`37.799999`：通用浮点残差
约`9.999999974752427e-7`，原decimal映射精确残差`1.000000002e-6`。因此原生canonical门可通过，
联合exact MW门仍须拒绝；不以投影误差扩张容差。
故障注入包括异常、无解、缺失/非有限变量、多solution、不合格状态、加载漂移、功率失衡、
timeout、目标/options漂移；预算、输入摘要和运行时合同漂移必须在对应边界拒绝。

## 当前验证与下一边界

最终37项新测试随六文件236项相关回归全部通过（115.12s）。独立pre-seal发现的solver termination与
可行赋值矛盾时lineage误标问题已修复，独立复核限定范围无开放实质finding；新增status子集独立8项通过（12.09s）。
此前独立27项及后补2项身份漂移反例均通过。本草案不提供official审查或启动许可。
测试构造曾调整两处：exact MW反例改为能隔离浮点/精确门的输入；unknown/error状态按Pyomo实际load拒绝行为
断言无物理见证。未放宽数值门或生产模型。
验证命令使用`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`，
相关文件为business_grid_short_solve、business_grid、outage_short_solve、continuous_grid_candidate、
outage_assignment、continuous_prefix_handoff各自的`test_rq2_*_v1.py`。
源码SHA256：`78ee40f2a40e691875fdc5e117bc58521b39f503d8f89f759346bda91d920b46`；
测试文件SHA256：`087db2a6c0f68029d3c8de4087e0869778d47a26b4de08e7a0ab7c12aefcf367`。
本组件补齐固定业务动作的求解接口，尚不定义因果网侧调用、训练容量与holdout绑定、完整恢复延续合同或正式输入包。
下一项为因果网侧请求的信息合同，见`rq2_causal_grid_request_contract_v1.md`；
不将一次离线轨迹可行性推广为持续服务容量认证。
