# 有限登记机制前沿：具体协议提案 v2

2026-09-29，DRAFT_NONAUTHORITATIVE。承接已获准开展的合同重审，供一次完整科学审阅。
以下“建议”均是待批准机制值；不修改旧冻结配置，不授权正式运行。
主目标继续为完整训练支持上的最低双向D，方案A额度y=Rw及有限登记主对象沿用既有批准。

## 参数合同 theta

| 项目 | 建议值／规则 | 依据及解释 |
|---|---|---|
| 登记E、stride | 168h、24h | 保留既有条件覆盖审计的研究尺度，避免结果驱动换窗口；不是业务观测 |
| 恢复due、最大后续F | birth+24h、24h | 具名统一期限机制；due小时先恢复再检查；不是文献“日内完成”的等价推论 |
| 会计期 | E与实际后续共用一个最长192h的nonrolling账期 | 第169小时不重置或追加预算；全部carry保留 |
| f、恢复headroom系数rho | f∈{.05,.20,.50}；rho∈{0,.10,.30} | 沿用旧机制坐标，不按反例反推f；headroom=rho*max(1-w,0) |
| eta、debt cap | .85、.20 | 机制anchor；债务按工作量，恢复实际功率为r，有效偿还eta*r |
| duration、rest、response | 4h、1h、1h | 小时聚合业务合同，非动态安全认证 |
| event cap、call energy cap | 14、2.8 D_DC*h，整个episode一次总cap | 继承旧候选数值而显式改变为整个有限合同的共同预算；不是逐日或rolling限额 |
| recovery power cap、up-ramp | 1、1 D_DC/h | 再分别受D、headroom、债务和适用CFE surplus约束 |
| 当小时call_limit、步长 | 1 D_DC、1h | call_limit是外生功率上限；实际调用仍受D、f*w及全部业务约束 |
| 活动与量化 | 原service tolerance=1e-6；minimum_event_power=1e-6；恢复floor至12位 | 严格活动边界及精确witness不变；原始请求与有效请求分别留存 |
| 功率尺度 | D_DC=250MW；既有12位half-even线性w投影，无idle项 | 模拟尺度，非Google实测MW；原始w>1保留并mapping unresolved |
| 初态 | 各独立episode业务零历史；可启停机组off/zero-generation且elapsed_down=ceil(minimum_down)；其他机组按dispatch_mode声明 | 四臂相同合法初态；细节见H1补充提案，不能把所有机组一概all-off |
| D域 | [0,1] | 在注册资源域内研究；超出上限无解只说明该域不可交付，不称所有D均不可行 |

保留旧OAT机制：eta=.60/1.00、duration=1/8h、event cap=7/28、energy cap=.7/7.0、debt cap=.05/.50；
其余维度使用f=.20、rho=.10及上述anchor。参数均非实证标定；20项empirical null保持。
OAT总共10个不同theta，与9个f/rho主factorial theta合为19个业务合同。

## 目标域与来源支持

数学研究域alpha∈(0,1]；建议计算网格为alpha=k/100，k=1,...,100，即统一1个百分点分辨率。
19个theta均用同一网格，共1900个cell。网格不按R_min或有解区间选择，不插入结果驱动加密点。
原46个候选参数坐标在该网格内，但映射、合同、reference发生变化，旧诊断不能冒充新cell结果。
这是看过旧负结果后的探索性后继；全部单元均发布状态，连续域只对明确证明的解析集合报告结论。

采用既有边际窗口清单和split，training为523×28=14644 pairs/cell，holdout为512×28=14336。
每pair使用边际均匀权重的乘积；重叠窗口不当独立样本，不作总体概率推断。不得跨chain/seed/split拼接。
training总计27,823,600个cell-pair身份；四臂最多111,294,400个对象身份，绝非同等数量的必要solver调用。
保持完整支持量词；解析反例可直接排除一个cell的相关臂，所有被省略计算的身份须保留及注明证明引用。
这些规模是提案计数，不构成机器可承受性证明；具体运行必须先通过计算资源门。

## 联合承诺与B6

主提案为additive_disjoint_service_commitment_benchmark。g为共同网侧请求，c为A的CFE请求，
各自先按原阈值确定有效量；正确共享臂履行g+c，采用一份可用量f*w、一份实际债务及q+r<=D。
若分量分别阈值化之和与原始合计阈值化结果不一致，该小时拒绝且不推进业务/actual状态，
相关未判定维度unresolved；保留raw、effective及mismatch证据。既有策略的这项拒绝门不被合计规则静默替换。
它是分离承诺的理论反事实，不把该D解释为所有物理共服务策略中的最低资源。

B6保留既有分账错误：grid/cfe各自检查q_k<=f*w、q_k+r_k<=D及自己的时序预算；
规划不额外检查g+c<=f*w。故A_B6同时反映可延期量重复使用与时序/容量分账差异。
B6共享实际执行仍只有一份f*w、一份D、一份债务与预算，不用规划见证认证实际成功。
建议绑定既有bidirectional容量策略的确定规则语义，A接入仍须新版本身份：B6规划两账只提供D_B证据，
实际执行不合并两套规划恢复动作，而从共同g/c请求和一份实际状态重新生成动作。
调用先受D、f*w、call_limit、w、剩余call能量、债务上限、ramp以及event/rest/duration共同限制；
允许活动时最大化可服务总调用，先分配grid再分配CFE，剩余请求各记shortfall，不将未服务请求生为债务。
有效调用为零时才恢复，恢复取D、power cap、业务headroom、适用CFE surplus及债务/eta之min，再floor至12位；
按最早已知due、再birth顺序分配，未知due置后。同一实际削减只生成一份实际cohort；
共享实际witness或网侧拒绝则不提交该动作。该规则也用于N/C/J的具名固定策略UB探测，各臂仅启用适用请求。
所有适用CFE恢复均使用同一A额度推导的surplus；network-only不强制CFE恢复上限。
物理共服务max(g,c)不属于本提案的执行规则。

## 共同reference与信息时序：建议H1后继

为支持真实来源按需延续，建议分开保存三类电网状态：共同normal状态N、共同reference状态Rref、各臂actual状态A_a。
N含正常计划的commitment、generation、残余up/down/dwell；H1 normal使用当前base conditions及baseline B=250w，
不把当期事故吸收到正常基准。Rref使用自己的上一小时状态，在当期normal commitment及已揭示事故/修复条件下，
按现有reference词典序先最小化B-P_ref，再最小化相对normal出力的L1偏差，再按generator UID最小化出力，得到g和新Rref。
N、Rref、A_a不得相互回写。reference审计身份绑定pair、小时、源输入、初态、目标及确定性选择规则，
计算不读取alpha、任何theta坐标、D、arm或实际响应后的carry；身份标签不作为决策变量。
不允许在相同已揭示历史下按隐藏pair ID选择不同动作或基准。
此为新的myopic reference机制，与旧整窗normal不同；可能更保守、失去跨小时启停预见能力，必须单独标记比较边界。
H1目标、机组边界与并列解具体提案见`rq2_h1_common_reference_candidate_v1.md`：normal先成本、再UID commitment、再UID generation；
这些新增normal阶段须按该页锁定/残差规则单独开发验收，
不能仅截短旧模型就宣布已实现，也不能将normal数值验收规则推广到容量planner。
仅当前信息不足以得到合法reference或实际dispatch时保留unresolved，不补造未来输入或宣称物理不可行。
小时顺序固定为：揭示当期输入→H1 normal更新N→reference更新Rref并发布g→A映射发布c→策略提交业务动作→
各臂actual selector→业务与actual成对原子提交。normal/reference失败阻断所有仍需该小时的臂；actual失败只阻断该臂。
共同链仅在至少一臂仍需该小时判断登记结果时推进；已停止臂不因其他臂继续而改写结局。
复用要求窗口起点、完整N/Rref初态及允许输入相同；重叠窗口的同一source hour不能仅按时间戳复用。

## 登记评分与按需后续

登记期内评价所有适用请求，以及登记期全部实际正延期cohort的按期偿还；未服务请求单独记缺口。
初始E小时来源整窗预验证，缺失或非法映射保留原pair权重并unresolved。后续逐小时只在判断登记履约仍需时读取。
完整E结束后，直到全部登记cohort结局可判定或最后due停止；后续新请求仍按共同固定规则执行，
其birth和全部债务保留，但不递归扩展登记评分集。各维度独立S/F/U，失败证据只优先于同维度unknown。
停止时保留完整carry；末债不必为零，不能解释为无限期可持续。缺尾只在判断仍需该小时且缺源时导致unknown。

## 最低D的证据与计算协议

每个(arm,theta,alpha)有自己的Pi；主对象为存在该cell内同一个pi对全部training支持履约的最低D，不要求跨1900cells共用策略。
H1 normal、reference及actual dispatch选择器是固定环境机制，不属于可优化pi。
pi只决定合法业务调用、恢复及cohort分配；可见历史包括相对时钟、cell常量与D、当期w/y/g/c/limits、已揭示电网信息、
该臂业务/cohort状态及A_a的已提交历史。完整源数组、未来后缀、audit/source/split/pair ID不可见；相同可见历史动作必须逐字相同。
训练后策略可冻结，但不得用隐藏ID记忆后缀。B6的Pi是两套分离规划因果账；共享实际执行单独评分。
固定bidirectional capacity+EDF策略只是Pi中的具名成员，不能把其最小成功容量定义为整个Pi的最优值。
整窗来源预验证是审计门，不将未来值或错误位置提供给策略；前缀未来扰动测试须覆盖N、Rref、g和业务/actual动作。

1. 精确必要条件阶段：使用A原始有理数及原活动规则。q_C>tau且q_C>f*w给出相关臂反例；
   B6按分量条件，正确joint另检g+c。解析反例绑定具体合同、来源和阈值，整cell排除不删pair。
2. 剩余cell先建同合同offline松弛，取得有效LB；放松非预见性、物理约束或后续义务时明确方向。
   必须证明其可行集包含完整因果对象，旧窗口planner结果未经此证明不能直接拼成LB。
3. N/C/J用预先声明的固定因果容量策略及EDF恢复在完整training支持逐pair核验UB，按小时严格witness和实际网侧验收；
   B6的规划UB只验两账完整因果履约，共享actual另验，不以它替代分账目标。
   候选容量先用D=j/100，j=0,...,100的固定网格，允许在任何找到的成功容量保存UB，但不以失败点二分或推断全局不可行。
   未评估点标记未评估；网格间最优性只能由有效LB/UB间隔支持。不得以D=1替代尚未获得的training容量证书。
   更大D也可能改变固定greedy的恢复并导致actual ramp失败；业务容量放宽不证明固定策略端到端成功单调。
4. 只有有效LB和完整UB均有证据时报告区间；缺少一侧就保留对应未知。精确数学认证始终另列，不能由浮点gap通过推定。
   gap、residual、integer及normal专属规则保持各自原版本，求解预算不足保留unresolved。
5. holdout前冻结每臂具名training成功容量与策略；这是最低D的已认证可行上界对应策略，不冒称未知的精确最优策略。
   无可行训练证据的臂不默认外生D做原holdout；标明未执行原因并保留支持清单。B6若有分账训练证据，执行其共享策略并单独报告后果。

对N/C/J可写L_a=max_s L_off(a,s)，U_a为固定容量网格中具有同一具名策略全支持成功证据的最小已验证值；
任一pair未决则该d不构成UB。B6的D_B上下界只针对分账规划对象，不能把共享执行失败否定为分账规划不可行，
也不能把分账UB称为共享可交付UB；其两账因果见证与共享执行策略必须分别绑定身份。

具体solver资源、任务复用、完整身份清单和运行批次尚待开发pilot核定；H1补充提案已列出词典序阶段成本门，本稿不授权长pilot或正式run。
必要实现包括A operational精确/浮点转换、H1共同reference、按需follow-up、同合同LB证明与全支持UB汇总。
这些缺口未闭合前不能生成execution-ready或正式容量证书。


## 2026-09-30 授权与开发状态

用户已明确“批准 v2 合同并开发验证”。本页与配套H1/v2参数合同的科学开发授权已取得；此前“待批准”措辞保留为提案形成记录，不再作为重复询问依据。具体运行权限、资源门和执行验证仍独立。

首个独立实现normal_h1_model.py已有逐mode初态、单小时词典序阶段构模、等式锁及严格赋值审计；110项新旧相关测试通过14.04秒，正在闭合只读pre-seal复核。它尚未包含native逐阶段求解、已验收前级锁值来源、当前小时source adapter、causal shared-prefix key、三链持久发布或完整履约证书。旧normal代码与协议保持。


### 后续开发进度：来源事务与真实资源探针

上述首个模型实现之后，H1短native链、原始报告重放、normal episode、固定来源凭据与source-bound intent/outcome已分别完成开发验证；对应独立规格和非正式结果保留。真实RTS仍被原20calls短门拒绝，未执行native链。

`rq2_normal_h1_resource_shape_v1.md`记录真实232阶段首末模型零solver探针，并确认最坏单事件3892576270 bytes超过本机SQLite单记录1e9 bytes。必须开发独立分块存储/资源准入，保留原始报告与前驱链；不能把两次构造耗时或当前小receipt当成完整链资源预算。共同发布、Rref/A三链、按需follow-up和完整支持LB/UB仍待集成。正式资源字段仍null，formal_execution_ready=false。
