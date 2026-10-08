# 连续科学候选：参数、窗口与评分建议

2026-09-28 用户已选择有限登记合同作为主对象，登记期内全部延期工作须按期履约，
后续真实输入不足仍为 unresolved。具体合同见 `rq2_continuous_complete_target_contract_candidate_v1.md`。
本页及原候选 YAML 的窗口/期限/预算仍为历史参数建议，数值字节保持；后续自包含协议须整合
已选择的对象与明确的 enrollment/follow-up 范围，不能把原168小时观察窗直接当作完整证书。

当前实现适配补充（2026-09-28）：候选 `minimum_event_power=1e-6`，等于既有
`SERVICE_TOLERANCE`。现有 `ContinuousPlanningInputs` 仅接受最小事件功率严格大于该值；
在一个已可接受的小型输入中只替换此字段，构造即拒绝，未调用 solver。
证据为 `results/tables/rq2_continuous_science_candidate_v1_non_authoritative/planner_admission_audit.json`，
SHA `564718a6947738da9f4189bcf7157a0ef70205dae523eceae52f298e005e1d57`。
这是现有闭 MILP 的适用范围缺口，不是候选服务不可行。后继须证明开放活动边界的下界松弛与
严格有效动作见证，或另行明确审阅科学合同；不能为接通代码静默抬高候选参数。候选 YAML 字节保持。

该适配的 build-only 开发现已实现，见 `rq2_continuous_planner_open_activity_v1.md`：
闭边界松弛与严格物理见证分离，新33项及相关回归共179项通过。原生赋值/solver界接入仍待开发，
尚未封存或提供正式容量证书；无需重复构造旧 admission 反例。

原生接入随后已形成 `rq2_continuous_planner_open_activity_native_v1.md` 所述开发产物：
新48项及相关回归共299项通过，真实四臂短例与完整数值快照已保存。它仍仅给开放前缀的松弛区间，
有限登记完整容量、training/holdout绑定及全支持资源门保持开放。

2026-09-28，DRAFT_NONAUTHORITATIVE。对应
`configs/rq2_continuous_science_candidate_v1.DRAFT.yaml`。
这是可逐项审阅的建议包，不是完整预注册；不注册新数值、不改旧冻结协议、不提供运行许可。

## 建议及科学代价

| 项目 | 具体建议 | 依据与代价 |
|---|---|---|
| 研究对象 | 保留完整连续服务；完整合同尚未绑定，前缀LB到完整对象的关系为条件命题 | 未来义务/period未定义前不发布complete LB；不保证四臂有限曲线 |
| 观察窗 | 同split/seed/chain的168小时，stride24小时；每24小时仅分chunk | 一周为设计假设，覆盖多次日界；不宣称独立样本或真实业务会计周期 |
| 债务期限 | birth+24，due小时恢复后记录剩余债务 | 新机制假设；不是公开数据识别的job deadline。逾期后偿还不抹去历史miss |
| 会计期 | 单一168h nonrolling期，chunk不reset | 现有单期账可承接；不提供未来重复周或rolling合同 |
| 累计预算 | 原24h参考event/energy参数显式乘7；duration/rest/debt不乘7 | 新的预算尺度假设，需批准；并不保留旧24h cells的完整语义 |
| 其他参数 | 使用v5的效率、duration/rest、ramp/response、最小事件功率坐标；参数见YAML | 以当前自包含v5作比较，不能把v1或合成fixture当现行授权 |
| 初态与功率 | 业务零历史、网侧显式all-off机制；250MW线性工作负载投影 | 初态必须通过动态网侧验证，250MW不是Google实测容量；不能由可构模推断可行 |
| raw>1 | 源值保留，对应评估保持mapping unresolved和原权重 | 不clip，不删除困难holdout。它扩大未知质量，不能当作物理服务失败 |
| 配对 | 固定窗口边缘乘积作为机制benchmark | 不是经验joint，也不能把其结果解释为人口概率；依赖结构推断另待登记 |
| 风险 | 固定支持权重上的明确失败/明确成功/未知三态，区间为[F,F+U] | deadline未覆盖、动作未知、solver未认证分别保留；已确认失败不因后缀未知消失 |
| 恢复/损失细节 | recovery power cap=1、永久损失=0、实际延期工作全部可恢复、恢复表示12位 | 四项均明确作为待批准机制选择，不能归入“v5已授权” |

20项实证未知仍全为null。原始job服务deadline、checkpoint、preemptibility和Google绝对MW不会被这些
机制建议“补成”观测。已实现聚合可恢复账也不提供逐job可恢复性证据。

请求建议明确沿用当前`source_pair`的机制尺度：`R=1-cfe_call_fraction_at_alpha_1`，
`C=max(alpha-R,0)/alpha`，恢复CFE头寸为`max(R/alpha-1,0)`，均以声明的D_DC归一化；
网侧`G`为共同reference削减MW除以D_DC的MW值。C不再乘当前workload，也不裁剪到baseline。
因此完整请求可能超过当前负载，必须保留该结果；它是非可替代服务义务机制，不宣称真实数据中心
碳核算。已有合法部分响应、未满足义务和网侧停止语义继续适用。

168h选择和乘7预算均未批准；它们不能为了得到可行曲线而随结果修改。
完整服务容量与有限观察窗口风险须分别标识，风险区间不能替代完整容量证书。

预算物化为anchor event=14、energy=2.8；对应OAT为event=7/28、energy=0.7/7.0。
这里没有每日或rolling上限，允许周预算集中在某一天（仍受duration/rest/debt约束）。
候选cell采用新namespace，不能复用旧46-cell身份、容量或结果。

每个窗口独立采用所声明零历史/网侧初态，重叠窗口中同一source hour可能具有不同运行前史。
这是假设窗口起点条件的benchmark，不是一条在窗口之间连续传递的实际轨迹。
uniform window权重隐含training seed质量175/523、174/523、174/523，holdout为175/512、170/512、
167/512；seed顺序为20260822、20260823、20260824，不宣称等seed权重。

风险事件明确为次级有限窗口服务及窗内birth-cohort合同；当前仅观察168h，不构造169—192h动作、
预算或normal计划。仅正的有效实际延期量产生cohort，birth h的恢复小时为h+1至h+24（含），
due小时恢复后任何exact正剩余均为miss，不套用1e-6服务容差。due越过观察末端且尚欠债则U；
已经偿还且无历史miss的cohort可判成功，但不能据此判完整持续服务成功。

每个适用维度独立分F/S/U且质量和为1；不适用维度为N/A，不算成功或未知。网络物理可行性仍约束
全部实际提交动作，CFE-only不承担的network service维度不混同物理约束。F优先只适用于同一维度
已经独立验证的失败；请求超baseline本身、source staging失败、selector未完成均不证明实际F。
沿用现有source_pair整窗预验证：全部168小时映射成功才开始任何策略动作；任一raw>1使整pair保持U，
不先执行其好行前缀。holdout超界位于0015/0016/0018三个块、共6小时，受影响7-block起点9至18，
共10/28个workload窗口；product配对为5120/14336，因此在本候选处理方式下形成至少10/28的U质量。
它不是服务失败率。通过来源预验证后才出现的运行期未知仍按同维确证F优先规则处理。原分母保留。
确定性benchmark区间与抽样置信区间分开，当前不报告后者。

## 候选规模暴露的计算问题

先核现有`chains.json` SHA，再按每链`max(block_count-6,0)`计算7块连续窗口：

| split | power窗口 | workload窗口 | 乘积配对 | 46-cell配对评估数 |
|---|---:|---:|---:|---:|
| training | 523 | 28 | 14,644 | 673,624 |
| holdout | 512 | 28 | 14,336 | 659,456 |

若每次配对评估直接走一次当前全UID四臂168h episode，每次需要
`168*(160+4*159)=133728`次selector级调用，training为90,082,390,272次，holdout为88,187,731,968次。
这些是特定直接展开方式的条件算术，**不是实际实验调用清单、性能测量或所有算法的计算下界**；
尚不含normal、容量搜索、多次评估与审计。training planner可能采用不同求解方式，不能把此数当作其实际调用数。

因此现有“逐cell、逐pair、全UID逐级重建”的直接方案不能仅靠扩wall预算就视为可执行方案。
必须先明确哪些网侧来源可以在相同身份、信息时序和请求不变条件下复用、哪些计算必须逐cell执行，
并核对是否需要新的等价求解实现。不能无授权删除UID级、缩减完整支持、只跑成功窗口或用采样结果冒充原完整对象。

## 已有实现与真正待补

可复用：跨chunk账、逐笔deadline及永久miss、固定容量因果策略、部分响应、网侧selector、
episode事务、normal来源执行与零solver回放。代码具备这些字段不等于参数已注册。

仍需闭合：

1. 完整未来义务及跨period合同；在没有延续证据时完整UB和完整归因保持unresolved。
2. 对上述CFE/网侧共同尺度与完整请求机制的科学审阅；它没有经验数据中心碳核算解释。
3. training容量求解、代表选择及完整支持验收规则；以及所得证书到四臂holdout策略的绑定。
4. normal预测发布、实际信息揭示、初态与来源的完整声明。
5. 全任务清单和可行计算路线，之后才选择每级时限及整任务资源。
6. 依赖结构、coupling稳健性和区间推断合同；重叠窗口不能直接做iid bootstrap。

参数建议通过后仍需把这些部分合为自包含科学协议并独立审查。当前草案不宣称上述内容已完成。

## 当前机械核对

v5、公开input_status及continuation chains的三个pin核对通过；候选3维factorial为36组，
五维各两个非anchor OAT为10组，合计46个不同参数向量。窗口与条件调用计数由已保存链重算。
对已有debt_cohorts做零solver时序小例：birth=1、due=25，hour24未偿仍为right-censored，
hour25恢复后miss为0、状态recovered_by_deadline，验证候选端点与现有账一致。
核对未调用solver，也未改变来源工件。

独立R4设计预审提出期末follow-up、完整目标未绑定、风险命名、birth/精度、N/A、raw>1作用域、
seed权重、预算尺度、窗口初始化和新增机制选择等问题，已据此澄清本候选。
完整未来合同、训练证书绑定、计算方案、候选schema与评分反例验证依然待补；不宣称完整pre-seal通过。

机械证据保存在`results/tables/rq2_continuous_science_candidate_v1_non_authoritative/structure_audit.json`，
SHA256为`6ba0fc07cf551a9fc1d18952849b46e8e8ffb051dca8accb8da41e9b5c4ec884`。
绑定候选SHA256为`2a0e7686b9f92355dc421531c2150ecab354a8106abea54c2d2c5d25259c9051`。
raw>1核对读取已核SHA的`alibaba_dimensionless_workload_blocks_v3/workload_blocks.csv.gz`，按exact decimal
判断，并与chains的有序block_ids匹配；没有改变投影接口、排除窗口或重新分配权重。
