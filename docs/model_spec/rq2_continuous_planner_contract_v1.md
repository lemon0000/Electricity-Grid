# 连续四臂开放前缀规划内核开发合同 v1

状态：DRAFT_NONAUTHORITATIVE；已有build-only内核和解析赋值测试，尚未注册正式科学协议。

## 对象与复用边界

当前开发对象是`open-prefix offline capacity-bound planner`。
实现位于`src/rq2_joint_deliverability_boundary_v1/continuous_planner.py`，不调用solver。
`src/rq2_joint_deliverability_v2/model.py::build_arm_planning_model`已有按共同向量长度建模的四臂结构，
可参考arm/track映射、event/ramp/energy/debt骨架及独立solver证书语义。
旧输入生成固定24h；旧模型从zero initial开始，末小时要求inactive，并约束terminal debt（旧协议为0）。
旧模型无逐cohort deadline，`structural_recovery_witness`依赖末端清债，均不能原样作为开放连续证据。
新实现采用独立文件，保留旧sealed模型和结果。

## 必须显式提供的模式

两个字段相互独立且无默认值，连同initialization、period、terminal规则进入planner身份。

| 字段 | 开发枚举 | 语义 |
|---|---|---|
| service_action_mode | sealed_v4_grid_excess_cfe_exact | 适用网络轨允许x_grid>=g_eff，CFE为x_cfe=c_eff；可额外grid削减以满足qmin |
| service_action_mode | request_bounded_exact_fulfillment | 完整前缀履约要求x_grid=g_eff、x_cfe=c_eff；与现有capacity policy的served<=request相容 |
| decision_information_mode | offline_full_prefix_recourse | 各scenario使用已给完整前缀优化，共享D；只能形成离线容量证据 |
| decision_information_mode | registered_causal_policy | 须绑定已注册policy/history信息集；generic离线MILP当前必须拒绝此模式 |

单服务臂不适用的请求依既有arm映射投影为0。两种行动模式的结果不得混为同一个training-policy证书。
GRID_EXCESS只复现旧grid/CFE服务方程，不代表完整旧sealed模型。
当前`temporal_step_rule=exact_fraction_floor_duration_ceil_rest`绑定identity/evidence：duration取精确floor，rest取精确ceil。
它与旧v2含1e-6舍入偏移的规则在非整数近边界参数上可不同；不能跨该差异直接传递旧对象的LB。
声称与当前capacity policy相容时，还须保持其effective请求分解一致性门；不能把该接口会拒绝的微量表示歧义
经另一种cutoff规则改成可执行输入。
区分反例：H=1，g=.05、c=0、qmin=.10，其余容量/ramp条件允许.10；旧模式可取q=D=.10，
bounded模式必须q=.05却违反活动最小值，因此无D可完整响应。现有capacity policy选择0并保留grid shortfall。

## 初版内核与验收

- 输入共同H、显式same nonrolling period和canonical zero period start；不从24h切片自动重置预算。
- shared arms使用共享账；B6 planning保留grid/CFE独立event、energy、debt与cohort账以及共同D，
  同时保留旧模型shared connected-demand sum和各轨available限制；不能用B6 physical共享执行账替代分离规划。
- terminal=`open_carry`，不增加末小时inactive或清债要求；逐cohort恢复分配守恒。
  已在H内观察到的已知deadline须验收；超过H的deadline及unknown保留carry/删失身份。
- 最小验收包括四臂峰值手算、两种action mode反例、末小时birth仍可carry、eta=.8时.25债务需.3125恢复、
  due-hour边界、B6一轨call另一轨recover、period/reset拒绝及solver bound方向。
- 首个实现阶段只做Pyomo模型构建、解析赋值与约束/见证审计。solver执行适配随后接入，参考
  `solver_adapter.py`的接口及规模统计；不直接沿用旧`finalize_capacity_certificate`的completed-24h resolved口径。
  grid-excess旧模式解不能借现有served<=request的aggregate接口作完整后验见证，须独立标注其派生执行投影。
- 非零规划初态涉及历史peak容量和B6双ledger，不能从当前physical handoff直接转成规划起点。
  若后续支持，须带完整可达历史或period_peak_call以及所有event/rest/energy/cohort状态；不能只带剩余debt。
  不声明分块独立优化等价于整段优化：离线追索读取的未来不同。

## prefix与complete证据的边界

前缀最小容量的有效solver证据为`L_prefix <= D_prefix* <= U_prefix`。
只有明确证明对每个D均有

`proj_prefix(F_complete(D)) ⊆ F_prefix(D)`

才能传递`L_prefix <= D_complete*`。须绑定同一arm/track会计、行动集或已证明的松弛映射、输入支持及其
prefix投影、归一化、容量域、初态、period、历史峰值、event/energy/debt/cohort与全部响应/恢复/deadline规则。
prefix只能删除尚未观察的未来约束，不能增设complete对象没有的终端约束。

离线追索在相同条件下可作为因果policy的松弛，但其最优值和incumbent不是因果policy的容量点值或UB。
没有上述映射证据时，只报告`prefix_capacity_interval`；complete UB保持null、状态保持
`unresolved_open_terminal`，不生成完整四臂有符号归因。
timeout、局部失败、缺bound或缺incumbent不能解释为不可行。被严格认证的prefix不可行也须在同一投影关系
和容量域下才有完整对象的必要失败含义。

## 仍需正式科学决策

正式H/stride/support/coupling/weights、行动集、causal policy class、finite enrollment/follow-up或viability closure、
rolling会计与初态/burn-in/评分协议均未由本文件注册。可先开发参数化模型构建和小型机制oracle；
正式planner/训练证书/完整服务容量上界及四臂归因须在这些科学合同明确后验收。

## 当前实现与验收范围

`ContinuousPlanningScenario`只接受显式mechanism输入、training split的JOINT/shared源容器及连续双时钟；
每个scenario保留trace/seed/provenance，所有scenario共同H且名称唯一。
`ContinuousPlanningInputs`要求显式行动/信息模式、period/initialization/terminal；本版仅1小时步长、
built-in int/float源数值、minimum-event-power严格大于原活动容差。其他步长、非零初态、rolling period、
causal-policy声明、holdout输入及有表示歧义的bounded请求均拒绝。
这些是当前开发接口限制，不改变正式协议阈值，也不声称覆盖被拒绝参数区域。

模型同时约束当前available、call_limit、shared baseline、track容量、up-ramp/response、duration/rest/count、
累计energy/debt及business/CFE/max recovery headroom。每小时每轨cohort birth等于实际计划调用q（dt=1），
allocation以effective work计且只作用于已出生cohort；恢复效率只乘一次。
known due-hour恢复后余额必须为0，晚恢复不能补救此前硬期限违规；未来期限与unknown不增加terminal清债约束。
grid-excess在原始请求为0的小时也可能计划额外调用；其新债务期限沿用该小时显式due或unknown，不能自动推定。

本步`recovery_representation=continuous_nonnegative_recovery_relaxation`进入输入、planner identity与evidence。
MILP的`[0,cap]`恢复集合是物理有效集合`{0}∪(tol,cap]`的上集松弛，也宽于因果策略的量化/EDF规则。
当cap>tol时它等于该物理集合的闭凸包，而不是拓扑闭包；当0<cap<=tol时物理集合仅含0，MILP仍可能允许正恢复。
不能为贴合后者擅加epsilon或改动阈值。minimum-event>tol则是当前闭MILP精确表达调用活动的适用性门，
不应把被拒绝的qmin==tol参数区称作已覆盖的松弛。
request-bounded仅说明服务响应约束关系，不声称整个离线行动集等于现有causal策略。
原始输入与派生grid-excess执行投影的独立逐时后验审计尚待接入；不能仅凭约束赋值验收授予incumbent UB。
当前目标属于relaxed-prefix对象。将来即便对松弛求得双边证据，也只能先命名为`relaxed_prefix_capacity_interval`；
物理prefix的UB须来自有效化/量化后通过独立逐时cohort回放的见证，LB传递仍须上文集合包含门。
`_continuous_evidence`保留relaxed-prefix/prefix interval、complete LB/UB和causal证书为null，完整对象状态为unresolved。

针对性测试覆盖四臂解析峰值、H=1/3/48末端、24h跨界、两行动模式反例、
due-hour/.8效率/late recovery、两cohort错配、B6独立恢复、全部主要包络及输入/身份拒绝。
另覆盖非零source-clock起点的绝对deadline、微量连续恢复的松弛标签及错误恢复模式拒绝。
duration=2.9999999不能容纳3小时活动，rest=2.0000001不能按2小时重启，均有显式边界反例。
测试通过手工轨迹和独立Fraction账赋值，检查全部Pyomo约束与变量域，不执行solver或声称最优证书。
cohort变量规模为O(scenarios×tracks×H²)，尚未通过正式窗口规模/许可证/资源门。
当前58项构模测试及6文件193项相关回归通过（1.44s）；领域方程核查无阻塞finding，提出的两项
语义标识均已落实。独立实现pre-seal限定范围无开放finding，恢复集合术语finding已闭合。
审查方实际复核58项targeted（0.70s）及全部连续模型439项测试（35.21s）通过，静态确认未调用solver。
源码SHA256：`7074867f8d9080e9b093703fdfda4c43c2f9fe197dec6bcd34aad88fcca27384`；
测试SHA256：`b55e55ac2ffd4133643dea9e2b9d1d08abb134c6c106fd54e86cb891a0ca73ea`。
旧capacity诊断包36组/1091条仍完整重放一致；`git diff --check`无输出。
以上只记录draft pre-seal findings，不生成official verdict/receipt或打开正式门。

## 后续solver赋值适配的开发合同

逐时动作核验已由`planner_witness.py`实现，独立pre-seal限定范围无开放finding，详见
`rq2_continuous_planner_witness_v1.md`。它不替代solver原变量与数值残差审计。

下一适配由调用方独立提供可信inputs与arm，不从求解后模型元数据反推科学合同。
先快照所有Var（包括inactive容器中的变量），保留稳定组件/索引身份、原数值、repr与float.hex；
独立重建canonical模型，要求变量inventory完整一致后装入原赋值。变量界、整数性、所有canonical约束残差
分别报告；不能因提交模型的约束被deactivate或改写而漏检。若将来引用该次求解的dual bound，还须核验
实际送入solver的完整目标/约束/域结构与canonical对象一致；原赋值合法本身不能证明bound来源合法。

有限float到动作Q的转换固定为shortest round-trip decimal，即Fraction(repr(x))，保留原hex并核对round trip。
不得按容差取整、归零、clip或补齐恢复分配。仅exact Q==0的allocation可省略；其余微量必须保留。
service_power是表达式，须按exact baseline-q+r派生并明确标记。转换后的动作即使通过浮点残差，仍可能
被精确见证拒绝；这种情况保留原解与拒绝原因，不能自动修复或签发物理UB。

复用旧`solver_adapter.py`的配置解析、版本检查和工具接口；不复用旧`_constraint_residual`的active-only合并判定，
也不复用旧24h的`solve_arm_minimum_capacity`/finalize证书逻辑。timeout、缺incumbent、非有限数、残差失败、
缺bound及不一致的界分别记录；不得以abs(UB-LB)掩盖倒置的界。有限候选与合法bound独立保留，
分别属于relaxed prefix、effective prefix或尚无映射证据的完整服务对象。此段为开发合同，不注册正式阈值。
