# 完整连续服务目标与前缀证据关系候选

2026-09-28，`DRAFT_NONAUTHORITATIVE`。用户现已明确选择有限登记合同作为主研究对象：
完整评价登记期内全部延期工作的按期履约，后续真实输入不足仍报 `unresolved`。
本次选择不注册 enrollment 长度、follow-up 输入、period 参数、策略类或完整正式协议。
依据为 `rq2_continuous_science_candidate_v1.md`、`rq2_continuous_planner_contract_v1.md`，以及
`docs/plan/RQ2_连续正式实验决策与验收_v1.md` 第2节已列出的两种 closure。只读领域核对由
`/root/continuous_target_contract_design` 完成；以下为设计建议，不是 official verdict。

## 必须区分的两种对象

当前主对象为下表的有限登记合同；长期持续服务仅保留为不同数学对象的说明。

| 对象 | 完整履约所指 | 尚需明确 |
|---|---|---|
| 有限登记合同 | 预先登记的全部 birth cohorts 按期限完成；follow-up 的新义务仍进入物理账 | enrollment、follow-up、评分 cohort、输入、period、初态和因果策略 |
| 长期持续服务 | 未来仍产生新请求，每期服务和逐笔期限持续满足 | future successor support、跨期状态机、因果策略类和延续可行证书 |

二者均不同于“只把观测前缀跑完”。有限登记对象也不等于无限期可持续：例如登记168小时 births、
deadline 为 birth+24，至少需要覆盖至192小时的相关输入和履约证明；这些小时不能由零请求尾部
或重复最后一天补造。总观察仅168小时而仅登记前144小时 births 是另一个对象，不能默默替换。
这些数字沿用现有候选作说明，尚未批准。

## 已选择有限登记对象的验收义务

登记集合 E 必须在读取履约结果前确定，不能因末端恢复资料缺失而缩短。每个 E 内实际正延期
产生的 cohort 都要有 birth、due、remaining 和历史 miss；未执行的请求缺口仍按服务义务单独
报告，不能因没有 birth 就算履约成功。对已发生延期，成功需要验证全部登记 cohort 按期偿清。
未观察到 due 且仍有债务的 cohort 为 unresolved；已验证的逾期不会因后续信息缺失或偿清而消失。

follow-up 保留真实输入驱动的新义务、共享预算和状态连续性；新 birth 继续入物理账，不能因不在 E
中而被删除。它们不自动扩展登记 cohort 评分集合，也不构成无限递推的新完整评分对象。
登记期外网络/CFE服务的验收范围、follow-up 所跨 period 的预算及输入支持仍须在正式合同中明确。
不能补零请求尾部、循环周或假定未来有恢复头寸来关闭旧债。

训练容量证书必须绑定 E、适用请求范围、逐笔期限、允许信息、固定初态/预算以及同一完整输入支持。
完整 UB 需要在全部注册支持上验证某个允许策略的登记履约及适用物理约束；只验证观察前缀仍不足。
资料不足时保留未知界；若报告前缀 LB，仍需满足下文集合包含条件。四臂继续分别认证，B6 规划
见证不升级为 shared execution 保证。这些是所选对象的证明义务，不是已取得的容量证书。

## 长期对象的精确定义模板

若选择长期对象，合同应明确 cell、arm、容量域、初态集合 \(X_0\)、信息滤子、因果策略类
\(\Pi_a\)、period 状态机 \(\mathcal P\) 和非空完整输入路径集 \(\Omega^\infty(\Gamma)\)。
\(\Gamma\) 是与已揭示历史一致的后继输入集合，不能从有限样本自动推定为循环周。

\[
D_a=\inf\{d\in[0,1]:\exists\pi\in\Pi_a(d),\ 
\forall(x_0,\omega)\in\mathcal A(X_0,\Gamma),\ \forall t\ge0,
\ \Phi_a(x_t,z_t,\pi(h_t))=1\}.
\]

注册目标支持为非空集合 \(\mathcal T_a=\mathcal A(X_0,\Gamma)\subseteq
X_0\times\Omega^\infty(\Gamma)\)，并要求其两个投影分别覆盖全部注册初态和全部注册输入路径；
不允许空支持使全称命题真空成立。兼容关系只采用事前来源/初态规则，不能根据履约结果删除路径。
它避免把本不允许的初态/路径随意作笛卡尔积。
状态须按 \(x_{t+1}=T_a(x_t,z_t,\pi_t(h_t))\) 递推；\(\pi_t\) 对注册信息滤子 adapted，
其中 \(h_t\) 只含决策前允许揭示的历史及当前 \(z_t\)。
\(\Phi_a\) 包括适用请求的履约定义、业务功率平衡、网侧约束、事件/恢复/债务/deadline 与
period 转移。相同已揭示历史必须产生相同动作；normal 计划允许预先公布哪些信息也属于合同。
有限登记对象可用对应有限输入路径与评分 cohort 替换此模板的无限时域量词，但不能沿用其长期主张。

B6 的 \(D_B\) 仍是 separate-planning 两套时序账的最低柔性，不能用 shared 实际执行的可行性
替换其定义，也不能把 separate-planning UB 当作 shared execution 履约保证。

状态至少包含 grid carry、previous call、active/duration/rest/prior-event、period identity、本期
event-start count/累计 energy、逐 cohort 的 birth/due/remaining 和永久 miss。采用非重叠更新期
时，一个可审阅的机制选择是：event 按起始期归属，本期计数/能量在边界更新，而 active、rest、
previous call、cohort、miss 和 grid carry 保留。这是新规则，尚未批准或实现；当前单期代码
禁止 period identity 改变，且将 prior-event 与累计 count 关联，不能只把 count 归零就称作跨期支持。

## 前缀下界的适用条件

当前 planner 对每条 training scenario 分别进行 offline 追索，并放松恢复行动集。其量词是
\(\forall p\in S_H,\exists u^p\)，不同 scenario 在共同历史下不必选择相同动作。
要把其有效 solver LB 传递到完整对象，必须逐项证明：

1. \(S_H\subseteq\operatorname{proj}_H\Omega(\Gamma)\)，每个前缀都有注册的完整延续。
2. arm/track、请求投影、容量单位/域、初态、period、历史峰值、cohort 和期限规则一致。
3. 对每个容量 \(d\)，完整可行轨迹限制到前缀后属于该松弛模型；不能额外清债、重置预算或
   增加完整合同中没有的终端限制。
4. offline/连续恢复确为完整因果行动集的上集松弛，且原生界来源和模型身份经过核验。

只有这样才有 \(L^{rel}_{a,H}\le D^{rel}_{a,H}\le D_a\)。有限观测的 product pairing 本身不证明
第一项，松弛 incumbent 也不提供完整或因果 UB。

完整 UB 需要一个固定因果策略，以及覆盖**全部目标支持**的完整见证或延续证书。若用末态集合
\(K\)，必须覆盖全部注册前缀末态，或另有将完整支持归约到已检查前缀的证明；只检查其子集
\(S_H\) 不足。对 history-dependent \(\Gamma\)，证书状态还必须携带决定后继集合的充分信息：
增广为 \(s_t=(x_t,\eta_t)\)，证明 \(\Gamma(h_t)=\widehat\Gamma(s_t)\) 并核验信息状态的转移，
此时 \(K\) 定义在增广状态上。
每个允许状态、每个允许后继均须满足服务约束并回到 \(K\)，且包含逐笔期限可达性，不能只证明
一步不越界或债务有界。单条人工尾部不能替代这些量词。

合同未定义为 `unbound`；合同已定义但证明不足为 `unresolved`。完整双边证据齐备才报有限区间。
只有整个注册容量域严格不可行时才报告相应不可行/estimand undefined；仅在已证明容量可行集
随上限嵌套时，才可用最大容量不可行覆盖整个域。固定 greedy 策略失败、timeout 或缺 incumbent
都不满足该证明义务。含无穷或缺失界时不强行计算四臂有符号归因。

## 固定策略与最低容量不是同一证书

所有注册 admissible causal policies 的最低容量 \(D_a^{adm}\)，与既有 greedy/EDF 策略族的
最低履约容量 \(D_a^{greedy}\) 不同。仅在该策略族包含于注册类时才有
\(D_a^{adm}\le D_a^{greedy}\)；greedy 的完整成功见证可给前者 UB，失败不能证明前者不可行。

现有 `capacity_policy._select_action` 中，容量仅进入 call cap；恢复选择不直接依赖该容量。
对固定请求路径、其他 caps 和初态，若两容量都不小于适用 effective 总请求峰值，容量项不会
影响 `min(request, cap)`。在固定规则和相同外部输入下可逐时归纳动作及物理状态相同；内容 identity
仍会因容量声明不同而不同，这不是跨任务归档复用许可。

若进一步采用严格 request-bounded 完整履约、容量只限制调用量，则每臂完整调用量已经固定。
候选峰值分别为 \(P_N=\sup g_t\)、\(P_C=\sup c_t\)、\(P_J=\sup(g_t+c_t)\) 和
separate-planning 的 \(P_B=\max(\sup g_t,\sup c_t)\)；各 supremum 取遍该臂注册的
\((x_0,\omega)\in\mathcal T_a\) 和全部目标时刻。完整可行集合非空且峰值容量有完整见证时，
最低容量等于对应峰值；恢复/期限/网侧条件决定该峰值是否可交付。不能把这一条件结论推广到
grid-excess 行动集、容量参与其他限制的模型或未来请求随容量改变的目标。

若履约评分允许最多1e-6的 shortfall，则峰值等式不再成立。例如请求3e-6、执行2e-6留下1e-6
缺口：它不满足严格响应相等，却可能通过相应容差判据。正式目标必须在两者之间作明确选择，
不能把逐时 stop 门当作完整服务定义。现有下界模型和 fixed policy 的不同证据范围继续保留。

## 可独立推进的活动边界适配

候选最小事件功率等于活动容差1e-6，而现有闭 MILP 要求严格大于它；已用零solver小例复现，
见 `rq2_continuous_science_candidate_v1.md` 和 `planner_admission_audit.json`。
可研究版本化的 `open_activity_boundary_outer_relaxation`：保留物理集合
\(q=0\) 或 \(q>tol\) 的含义，用闭约束 \(q\ge tol\,on\) 提供下界松弛；边界
\(q=tol,on=1\) 只能属于松弛证据，不能通过严格有效动作见证。已有 witness 在
`planner_witness.py` 中对正调用 `q<=TOL` 拒绝，应保留这一门。不得改变科学参数或放宽物理动作。

实现验收至少包括：合法动作到松弛模型的投影、恰在边界的假活动被 witness 拒绝、
略高于边界的有效例、四臂及B6账一致、旧版本字节保持，以及无 complete/causal 认证升级。
该适配不依赖选择长期或有限登记对象，但不能单独关闭完整目标或训练/holdout门。

上述 build-only 适配已形成独立类型实现及33项测试，相关回归共179项通过；
见 `rq2_continuous_planner_open_activity_v1.md`。原生赋值/界接入与完整证书仍待完成。
