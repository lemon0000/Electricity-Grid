# 有限登记合同候选：登记、延续与容量语义

2026-09-28，`DRAFT_NONAUTHORITATIVE`。用户已批准有限登记合同：登记期内全部
延期工作按期履约，真实后续输入不足保留unresolved；亦已批准下述双向物理功率容量修复。
登记长度、后续长度、期限、账期、预算及其他具体规则仍是待审阅建议，尚未注册。
旧冻结协议、科学候选数值和已保存结果保持；不由本页开启正式实验。

## 可具体审阅的登记规则

建议登记E=168小时内全部请求及实际正延期births，stride=24小时；机制deadline建议birth+24，
故最大需观察至第192小时。缺尾部时保留原登记集和原配对权重，不改成144小时登记。
已有源覆盖证据见 `rq2_finite_enrollment_support_v1.md`，不是对此参数组合的批准。

主评分范围建议明确为：适用hard-grid/CFE请求在E内的履约，以及E内产生的全部cohort按期恢复。
正请求未服务须单独记shortfall，不能因零birth就判联合成功。登记后新请求及其服务/缺口另表报告，
全部实际动作仍须满足物理账、网侧动作和预算规则；其新birth不能删除，也不递归扩展登记集合。
B6的separate-planning对象和shared-execution风险仍分开。

建议在完整E结束后按当前可见状态逐小时延续，直到所有登记cohort的结果已可判定，或达到登记cohort
最后due。每个实际执行的follow-up小时使用真实来源及同一固定因果策略；新增cohort保留完整债务账。
若联合失败已确定，联合维度可保持失败；**其他维度不能因联合失败而伪造成功或失败**。
若提前停止而某维度未判定，该维度保留unknown。停止时保存全部carry，不声称末债为零或未来可持续。

缺失后续输入仅在尚需该小时来判定登记履约时阻断判断；判定完成后的数据缺失不改写既有S/F。
raw>1同理：登记内原有全窗来源预验证语义若保留，应明示；follow-up建议只在实际需要读取到该小时
时触发mapping unresolved。该按需规则与旧168h整窗检查不同，需要用户批准及实现测试。

## 预算与初态

建议使用一个覆盖E及实际follow-up、最长192小时的nonrolling episode账期。第169小时不reset
event count、energy、debt、active、rest、previous call或grid carry，也不自动增加一天预算。
可提交的具体候选是：将原168h建议中的event=14、energy=2.8作为**整个有限合同episode的一次总cap**；
对应OAT为event=7/28、energy=0.7/7.0。这是新的机制选择，不与旧24h或168h预算声称科学等价。
效率、duration/rest、debt、响应等其余坐标须在自包含后继中逐项列明，不能靠本页省略继承来正式运行。
业务零历史、网侧显式初态和250MW功率映射仍是待注册机制，不是公开业务观测。

## 训练容量与holdout的量词

保留原四臂最低柔性主目标。完整训练容量D应对应一套允许信息下的因果策略，对全部注册training
支持满足所选有限登记合同。当前planner逐scenario offline追索只可能给条件性LB；固定greedy/EDF
的完整成功见证可在其属于注册策略类时给UB，失败或unknown不能证明所有策略不可行。
所选容量、策略、输入尺度和信息声明必须在holdout前冻结；逐pair超前重优化不能冒充固定策略。
源数据未补全时只报告已获证据的界或unresolved，不用松弛incumbent补完整UB。

## 已确认的容量定义问题

当前strict `request_bounded_exact_fulfillment`把每小时服务q固定为适用有效请求。若D只出现于
`q<=D`，其他所有约束均与D无关，则任何可行轨迹在峰值容量P下已可行；更大D无助于恢复。
所以有完整可行轨迹时D_N=P_N、D_C=P_C、D_J=P_J、D_B=max(P_N,P_C)，I_sep=0。
恢复、期限与网侧条件可改变可交付性，但不能据此声称观察到了非退化的时序最低容量交互。

GRID_EXCESS也不能自动解决。只读领域核对确认：在当前闭MILP和连续恢复模型内，令M为适用请求
下界峰值与qmin的较大值，可把excess-capable track的q截为min(q,M)。下界、单侧up-ramp和
on/start/rest/duration保持；每笔cohort的allocation按新birth截断，令r为新allocation之和除以eta，
则recovery、energy和debt不增，已知due仍清偿。因此可行容量不会因恢复时序而被推高到M以上。
CFE exact分量不截断；正CFE低于qmin的非法活动不会因加大D而变合法。B6逐track适用。
这个论证不外推到完整grid物理约束、离散恢复或其他新增限制；在qmin=tol的开放物理集合上，
边界松弛解也不能变成严格物理UB。

## 保留最低柔性主目标的最小修复候选

用户已批准将D明确为按declared D_DC归一化的**双向物理功率柔性容量**，在新版本planner每个track施加
`q_t+r_t<=D`。当前调用和恢复不并发，因此等价于原q<=D加r<=D。其余headroom、CFE surplus、
效率、债务、deadline、事件及能量约束继续独立成立。
不采用eta*r<=D作为物理功率限：eta*r是有效工作恢复率，r才是baseline-q+r中的实际恢复功率。
这是机制定义，不宣称公开数据识别了双向可调容量。

解析例：h1延期0.4，eta=0.8，h2为唯一恢复小时，headroom充足。原容量只约束调用，D=0.4；
新定义要求r=0.5，故D=0.5。若允许h2/h3各恢复0.25，则D回到0.4。最低容量由此能够反映
恢复期限与时序，而不是仅反映调用峰值。数值只用于解析说明，未注册为实验参数。

四臂使用相同物理功率单位；B6仍在其两套separate-planning账中分别施加q_k+r_k<=D，
保留有意的分离记账错误。B6 shared execution必须另按共享物理容量验收，不能用分离规划UB认证。
primary D继续对应允许策略类的最低容量，offline planner只给条件LB、固定greedy完整见证只给UB；
不把主目标替换为loss frontier，也不把greedy失败当所有策略不可行。

该容量单位/耦合的R4科学选择已获用户明确批准；实现按R3在独立bidirectional版本开发。
版本化同时修改planner、精确witness和固定策略恢复cap，补齐四臂/B6及解析例回归，
再推进训练到holdout绑定。既有冻结模型与结果保留其原有定义，不原地升格。

## 对应实现验收

- 第168小时birth在其due小时恢复后判定；缺少必需的后续小时为unknown，已知miss永久保留。
- 请求未服务与未产生cohort分别处理，禁止真空联合成功。
- follow-up新birth入账、预算不断开、终止保存carry，但不递归延长登记集。
- 共同历史下动作一致；按需停止只使用已揭示证据，各维度独立保留S/F/U。
- 缺源/raw>1保留原权重；来源完整不自动判成功，来源不完整不自动判失败。
- 容量参数必须进入所注册物理资源限制，并以解析例证明最低容量的解释与主问题一致。

除有限登记主对象及双向容量定义外，以上具体参数与评分/停止规则仍为待批准候选及证明义务。
实现验收见 `rq2_bidirectional_capacity_v1.md`；不由容量授权推导E/F、期限、预算或正式运行许可。
