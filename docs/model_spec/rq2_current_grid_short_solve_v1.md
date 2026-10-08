# 当前小时固定功率网络短求解

日期：2026-09-19。状态：DRAFT_NONAUTHORITATIVE，独立pre-seal限定范围无开放实质finding。

实现：`src/rq2_joint_deliverability_boundary_v1/current_grid_short_solve.py`。
测试：`tests/test_rq2_current_grid_short_solve_v1.py`。

## 合同

接受`current_grid_step`的当前信息、当前揭示、上一实际carry和给定exact MW功率。
内部fresh构模，检查显式solver spec及短预算后至多调用一次solver；复用`continuous_grid_candidate._solve`的
native记录、完整变量、canonical补值、显式加载、模型结构/options/version前后核对及fresh canonical审计。
然后独立调用`audit_current_grid_assignment`，在原exact业务功率下重审节点平衡、出力界、response与actual ramp/repair。
输入及执行身份在前后重验；短求解identity绑定本实现、输入摘要及既有原生pipeline闭包。

只接受规范化solver spec。三类solver tolerance不得超过1e-6，线程、秒数、总秒数和规模必须在显式GridDevelopmentBudget内。
当前horizon固定1；budget本身保证horizon/call caps均至少1。单次入口不执行重试、无事故替代或零DC确认。
测试中真实求解均为单小时小型LP，每次1秒/1线程；这一入口不是正式runner或新规模资源许可。

## 见证、求解来源与状态推进

以下证据分别记录：

1. `physical_assignment_witness_available`：成功加载的完整赋值通过独立网络审计。
2. `solver_lineage_checked`：原生流程无错误、canonical赋值合格、solution status为feasible/optimal，
   且solver status为ok/warning、termination属于显式允许的有incumbent情形。
3. `owned_solver_assignment_available`：同时满足前两项；只有此时本result的`next_carry`非空。

timeout若存在完整合法incumbent，可以提供赋值与carry，但不能声称最优。
objective/options等来源异常时，独立物理见证可以单列，result的next_carry仍为空；其assignment_witness内部carry
只是已有给定赋值审计的派生产物，不是本入口的合格solver后继。
solver不可行/无界等报告若与solution相矛盾，来源验收失败；缺解、加载失败或不合法赋值保持unresolved。
失败不修改传入的before，不生成或消费后缀小时，也不升级为数学不可行证明。

`network_feasibility_status='witnessed'`仅指存在独立物理赋值见证，不隐含合格solver来源或可从本result推进。
零目标原始bound保留在raw记录内，不输出目标区间、网侧请求、容量、因果dispatch、数学不可行或安全证书。
给定完整信息与固定功率的单小时求解不注册非唯一dispatch选择规则；不能据此证明完整因果策略。
normal提前发布时间、origin、repair cap和当前报告仍是机制声明，实际观测证据边界保持。

## 验收

覆盖真实当前功率可行及跨小时实际ramp拒绝、真实repair cap；fake native注入exception、missing/NaN变量、
多解/无解/错误status、加载篡改、功率平衡失败、timeout incumbent、矛盾termination、objective/options异常，
以及exact MW与float容差差异、预算/solver适用性、陈旧输入、运行后identity漂移和受控result构造。
最终37项针对性测试通过（14.28s）；五文件193项相关回归通过（79.22s，在最后两项测试增加前，源码未变）。
命令为`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`，文件为tests目录中的
`test_rq2_current_grid_short_solve_v1.py`、`test_rq2_current_grid_step_v1.py`、`test_rq2_continuous_grid_candidate_v1.py`、
`test_rq2_business_grid_short_solve_v1.py`和`test_rq2_grid_information_v1.py`。
补充真实branch outage的reference angle/unused angle canonical completion与fresh-import依赖闭包测试；
当前导入的49个仓库文件与输入/执行identity覆盖集合一致。
独立pre-seal复跑当前37项通过（13.97s），并独立核对真实支路故障微例与49项依赖闭包，限定范围无开放实质finding。
`git diff --check`通过；原grid/solver/scenario源码、冻结配置与正式结果保持。

开发字节SHA256（非production seal）：

- source：`c6eb97a2b6fa9b3729206e6f9b75bed93475aa59c5527e9a5319af51659208ec`
- test：`a6b99c8bc4bfb33b3a523b3beaae147ac5185125835299a8fdd4b37decbcf673`

下一项为当前网侧请求与dispatch选择的自包含机制合同及四臂逐小时连接；完整恢复、输入包和正式运行门继续开放。
