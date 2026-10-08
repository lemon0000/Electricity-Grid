# RQ2 连续多日服务协议草案 v1

状态：`DRAFT_NONAUTHORITATIVE`，2026-09-12。机器草案为
`configs/rq2_continuous_multiday_service_v1.DRAFT.yaml`；参数证据见
`rq2_continuous_multiday_parameter_evidence_v1.md`。本次交付范围是协议设计、显式给定动作的连续回放和小型验证。
旧 sealed v5、v2 model、执行协议与历史结果继续作为原有口径保存。本草案尚未注册，不生成 seal、production manifest 或运行权限。

## 1. 时间、信息与边界

每小时为半开区间，状态标在小时末。24小时只作为 observation chunk；raw-origin block不自动代表自然日或业务结算日。
power/workload各自的source hour必须逐小时递增，split、trajectory、outage seed、trace、normalization与provenance hash保持相同。
跨来源两条连续边缘不意味着同一物理时钟或经验联合分布。Google同钟CPU—PDU数据保持external robustness用途，不能直接替代RTS调用或Alibaba业务合同。

本草案采用**一个显式 fixed nonrolling accounting period**贯穿所有chunks；期长、起点与预算须作为同一个机制情景预先给定。
只要period不结束，event count和累计调用能量一直累计；跨24小时边界不能增加预算。
本版本不执行period切换；多period的event归属、rolling预算、合法reset及跨期债务结算需要独立后继合同。
这是一项明确的草案范围选择，不表示真实业务采用该制度。

初始状态必须完整输入，包括previous call、active duration、rest、prior-event flag、event count、累计energy、debt和period ID。
未观察到的carry-in不能默认为零。测试采用零初始状态和非零初始debt两种**机制情景**；实证输入仍为unknown。
单一period的carry-in必须保留其因果历史：`debt <= cumulative_call_energy`，正累计energy要求prior-event历史。
非零测试初始debt/energy均为0.125、event count为1、已观察rest为2小时；仅传入debt而丢弃energy/event历史会被拒绝。
前一chunk的全部末状态原样成为下一chunk初始状态，不在边界推进时间、恢复或清债。
回放API使用不可变`JointReplayCursor`一起携带状态、最后观测身份和固定envelope；
初始化显式建立情景，后续chunks只接受返回的cursor，不接受另传anchor或替换envelope。
重新初始化是新情景，不是原轨迹的延续；本开发接口不提供持久化、防恶意篡改或production checkpoint证书。

## 2. 服务与恢复的机制合同

设同一基准功率归一化后的需求为 \(p_t^0\)，网络与CFE义务为 \(g_t,c_t\)，恢复为 \(r_t\)。本草案的测试路径为

\[
q_t=g_t+c_t,\qquad p_t=p_t^0-q_t+r_t,\qquad
0\le q_t\le\min(p_t^0,\bar q_t).
\]

加法表示分离义务消耗共享资源，是机制假设。co-benefit结算仍未决；不把同一削减的两种价值强行解释为两倍物理功率。
`workload_occupancy`在合成回放中承担\(p_t^0\)的接口角色，仅取[0,1]；公开CPU或Alibaba raw fraction不能未经映射送入此字段。
六条raw>1值继续保留，不clip；真实归一化/absolute MW映射仍待注册。
CFE请求不得先裁剪到可用柔性。回放的\(g,c\)是显式合成输入，未从实际dispatch推算，也未认证网侧安全。

恢复采用

\[
0\le r_t\le\min(\bar r_t^{business},\bar r_t^{CFE},\bar r_t^{max}),\qquad
b_{t+1}=b_t+q_t\Delta t-\eta r_t\Delta t\ge0.
\]

同小时CFE-compatible surplus必须作为独立输入；缺失不能用business headroom代替。
本情景假设调用时不恢复，\(0<\eta\le1\)，债务单位为归一化power-hour；效率仅作用于恢复项。
累计调用能量\(E_{t+1}=E_t+q_t\Delta t\)，已恢复的能量不返还累计调用预算。
每个prefix都检查债务上限，未来恢复不能修复过去违规。

实现中上述方程使用effective调用/恢复：先对原始`g+c`求和，再将不大于`SERVICE_TOLERANCE=1e-6`的调用或恢复置零，
超出该值则完整保留；功率平衡、事件与energy/debt均使用同一effective值。
这是沿用既有boundary组件的离散容差机制，不是精确实数累计：每步被忽略的原始调用能量至多为`1e-6 * dt`，
长时域不能据此宣称原始微小调用的累计误差为零。原始请求字段仍保存；本回放不把这些原始微量义务认证为已履行。
该容差沿用接口测试语义，未变更任何正式验收阈值。
连续active小时属于同一事件，duration跨日累加。inactive间隔按实际小时累计，minimum rest不是“债务已经清零”。
仅inactive→active增加event count。event duration、count、energy、debt、call limit均按显式情景参数检查。
`minimum_recovery_hours`是既有接口名，本草案中表示minimum interevent rest。

## 3. 截尾、deadline与估计对象

observation end本身不要求inactive或零债务。缺未来数据和缺deadline分别报告：

| 条件 | 口径 |
|---|---|
| 缺已注册completion deadline | 合同未定义；completion estimand undefined |
| 已给deadline但观察未覆盖 | right-censored；保留已观察事件、债务与违规 |
| 覆盖deadline但未求解/验证履约 | inputs complete，不能宣称completed |
| 已观察违规后结束 | 违规继续报告，删失不覆盖违规 |

尾部若未来可用，必须包含新的grid/CFE义务，不能添加任意长度零请求尾部。
当前deadline与tail保持null：真实job完成时间是执行结果，不自动成为承诺deadline。
若后续采用每笔债务deadline，需引入age/cohort ledger和回收分配规则；聚合\(b_t\)不足以证明逐笔准时完成。

候选四臂仍为\(D_N,D_C,D_J,D_B\)。其连续版本须在**相同注册period、初始状态、支持集和deadline口径**下定义最低柔性。
仅观察到有限prefix且无completion合同，不能报告完整连续可交付\(D\)或把prefix可回放当作可持续服务前沿。
若四臂未来均有有效定义，沿用有符号分解
\(I_{joint}=D_J-\max(D_N,D_C)=I_{sep}+A_{B6}\)，不预设嵌套或差值正负。
B6规划中的grid/cfe独立ledger必须分别跨日携带；执行则须回放共享物理ledger。本轮仅实现joint-correct显式动作回放，四臂优化和B6策略转换待开发。

holdout候选方案固定训练所得策略，逐小时只使用已揭示信息及携带状态。不得从training末状态接到holdout开头，
不得使用未来恢复机会重新优化当前动作。已有splits保留；Google新split、跨来源coupling和支持集筛选均未注册。
后续holdout应分别报告观测服务违规数量/能量、实际观察暴露小时、末债务、active状态和completion删失数量；
在没有注册sampling/coupling时，这些不能称经验联合风险概率。给定动作回放只检查动作序列，不认证生成动作的策略非预见性。

## 4. 参数冻结前的开发验收矩阵

| 验收项 | 当前证据/测试 |
|---|---|
| 48小时与任意分块逐状态一致 | 独立解析prefix debt/energy/event oracle |
| hour 24→25仍在同一事件，debt不消失 | hour 24 debt=0.5，hour 25 duration=3/debt=0.75 |
| 次日duration/energy/debt超限 | 跨chunk故障测试拒绝 |
| event count/rest跨chunk累计 | 两次调用合成反例 |
| 共享预算与服务功率平衡 | 分别够用但相加超限；错误服务功率均拒绝 |
| 恢复兼容性与因果债务 | business/CFE任一不足、提前恢复均拒绝 |
| 初始debt及截尾 | 非零carry-in保留；缺deadline和缺未来分别标记 |
| split/gap/identity隔离 | 新回放测试及既有boundary回归 |
| 证据与历史完整性 | 交付离线verify-existing，既有sealed/input hash回归 |

测试输入来自YAML的`synthetic_fixture`，数值为手算用的二进制友好小数，未用公开结果挑选有利参数。
回放器不运行solver；首个不合法动作抛出`ValueError`，表示该给定动作/合同校验失败，不能证明不存在其他可行策略。
已有observed violations经边界保持；本回放器不承担完整观测违规收集器的职责。

下一阶段：基于本表确定机制情景和证据缺口的处理方式，完成deadline/period与split/coupling登记后，开发四臂planner和固定策略holdout。
正式科学协议、数据输入、solver/实现、独立审查、单独formal授权各门仍需分别完成。
