# RQ2 连续正式实验：决策与验收

日期：2026-09-16。状态：`DRAFT_NONAUTHORITATIVE_DECISION_PACKET`。
这是实现前的可审阅决策包，不是完整预注册、生产seal、审查PASS或运行授权。
目标保持为能够启动RQ2四臂连续服务正式实验；以下缺口不以已有合成测试通过替代。

## 1. 本轮关键路径核对

上一轮完成的拒绝覆盖与补充测试是开发进展。进一步核对后，当前关键路径是连续科学协议和网侧输入语义，
而非继续扩充fallback分支。B6 separate-planning拒绝后的新补救策略可独立研究，但不是定义四臂规划容量的必要前置。
现有合成回放、债务、四臂controller与两套诊断包继续复用；它们不提供最低柔性求解器或正式数据入口。

### 网侧跨块连续性尚未建立

证据链：

- `configs/rts_gmlc_public_grid_need_dispatch_v4.yaml`的`model.normal_baseline`为
  `free_boundary_24h_normal_state_SCUC`。
- `experiments/run_rts_gmlc_public_grid_need_dispatch_v4.py::_process_block`按单块调用`_normal_baseline`；
  没有active outage的块不求normal baseline，仅保存空generation/commitment与`not_applicable_no_active_outage`。
- `_normal_baseline`调用`src/grid/rts_gmlc_scuc_solver_successor.py::solve_normal_prescreen_with_spec`，
  后者用`_build_model(context, fixed_initial=None)`。
- `src/grid/rts_gmlc_scuc.py::_build_model`仅在`fixed_initial`非空时把首小时ramp连接到输入发电状态；
  free-boundary首小时startup/shutdown固定为0。
- `_derive_initial_state`将初态明确标为`optimization_derived_free_boundary_not_observed_chronology`。

因此，source hours连续、事故事件跨日和旧1071块全部发布，均不能单独证明跨块commitment/generation/ramp连续。
这里没有声称具体旧轨迹违反了ramp；已证明的是其合同和调用路径没有提供该跨块保证。
旧benchmark及其冻结结果继续有效于原有范围。continuous successor须选择并注册网侧边界：
若要求网侧亦连续，需新的连续dispatch证据；若只把旧逐块调用视为外生机制序列，必须明确缩小网侧解释，不能沿用连续电网主张。
本目标优先保持连续语义，不以外生逐块序列默默替代。

### 开放右边界不自动给出完整容量

用户已选择开放的连续多日服务。hour 23义务和全部carry state保持，观察末端不强制清债或inactive。
这并不等于所有末端cohort已在deadline前恢复。只有有限前缀的可行解，最多证明该前缀约束被满足；
不能把其容量UB作为完整恢复服务容量的UB，更不能称无限期可持续。

对同一完整合同，令`D_prefix`为观测前缀约束的最小容量；任何完整可行轨迹的限制都必须满足前缀约束，
故前缀solver的有效LB可作为完整容量的必要LB。完整容量UB还需完整合同下的延续可行见证。
缺少未来请求、deadline或延续合同，完整容量应为`unresolved`/上界未知，不能借用前缀incumbent补上。
该关系不授权用`D_prefix`替换原主estimand；如何正式报告部分识别结果需在新协议中明确。

## 2. 提交决策的科学范围

推荐保留四臂、有符号归因、完整请求、共享预算、逐笔债务、开放边界和诚实删失，以公开数据驱动的机制benchmark推进。
业务参数继续标为mechanism_assumption；实证层20项null不被机制值覆盖。
需要明确接受：数据不足时正式结果可以是容量/风险区间或unresolved，不保证得到四条有限的完整交付曲线。
若要求每臂均有完整履约的有限容量认证，须先提供或批准有依据的deadline与continuation合同；现有本地观测不足以保证做到。

| 待定项 | 可审阅建议 | 对验收的影响 |
|---|---|---|
| 主estimand | 保留完整连续服务容量对象，单列前缀容量证据；完整对象只报有证据的界或unresolved | 禁止把前缀UB变成完整UB；缺任一臂有限认证区间时不作完整四臂符号结论 |
| 机制参数 | 使用明确注册的业务假设，不将完成时间当deadline；逐项记录来源或机制身份 | 真实deadline/recovery等仍null；需另行确定机制期限、预算和初态数值 |
| 网侧 | 新continuous-grid successor，保留selected-state DC范围及官方限额 | 逐小时状态、初态来源、跨chunk ramp/min-up/down、事故响应与无事故小时均须有证据 |
| 会计期 | 显式period；chunk不reset；是否多period及跨期event归属先注册 | 不把旧每日event/energy限额默默扩展成全周限额，也不自动乘7 |
| 时间窗 | 只从已有split/seed/trace内连续片段构建；窗口长度和stride在结果前固定 | 重叠窗口不是独立样本，窗口权重、支持选择及bootstrap须重订 |
| raw workload >1 | 源值保留；资源占用映射、归一化基准与超界处理单独注册 | 不能直接送入现有[0,1]回放接口，也不能未经声明clip |
| coupling | 电力/工作负载保持各自时钟，采用注册的benchmark coupling集合 | 不宣称经验联合分布；不能把所有潜在邻接视为同钟观测 |
| holdout | 训练选容量与策略后冻结；失败后未知实际轨迹保留unknown | first rejection不等于实际hard-grid失效；无损失合同不能生成真实服务缺口 |
| 右删失 | 已观察违规不消失；未覆盖deadline的cohort不算成功 | 仅在事件定义、分母和权重均注册后形成风险界；输入损坏与服务未完成分开 |
| 加法与co-benefit | 继续把加法非可替代义务标为机制假设；co-benefit未决 | 不将加法解释为唯一物理事实，不改旧冻结共享预算 |

这里尚未选定未知期限/预算、注册新split/coupling、放宽科学门或修改旧46-cell数值。
审批本页的方向也不能代替之后对完整自包含参数协议的审阅。

### 完整履约对象的两种closure候选（主对象已选择）

2026-09-28 用户明确选择有限登记合同：完整评价登记期内全部延期工作的按期履约；
后续真实输入不足仍报 unresolved。此选择不同时批准下述示例长度、期限或会计参数。
具体证明义务见 `docs/model_spec/rq2_continuous_complete_target_contract_candidate_v1.md`。

- 有限登记cohort：预先固定enrollment interval，并至少观察一个最大deadline长度的follow-up。
  follow-up的新网络/CFE义务仍进入物理账，只有enrollment cohort进入该完整履约评分。
  例如总episode168h、机制deadline24h只能登记前144h births；登记168h births至少需192h输入。
  这些数值是决策示例，未注册；结果只属于有限登记cohort，不是无限可持续服务。
- 长期/持续服务：明确未来输入集合、rolling合同与因果动作，并证明末态进入robust controlled-invariant/viability set。
  当前没有这种延续证书；缺证书时完整容量继续unresolved，不以周期重复、零尾部或最后一天清债代替。

若改成rolling-24h event/energy合同，必须携带过去24h调用与事件起点历史，不能只携带累计总量。
现有单一nonrolling-period代码不能宣称已支持该合同。初态若采用zero-history，须显式注册为机制情景；
holdout不接training末态。上述选择须在完整协议中批准后再进入对应正式planner实现。

## 3. 零solver窗口规模证据

读取既有continuation `chains.json`并先核对SHA256
`0f661707d4ebb6ceb6f12073e6426a03b542322324df8a4f99b6d229ced8fc48`。
按每24小时一个起点，仅在各连续链内计数`max(block_count - H/24 + 1, 0)`：

| H小时 | power training/holdout窗口数 | workload training/holdout窗口数 |
|---|---|---|
| 48 | 538 / 527 | 33 / 33 |
| 72 | 535 / 524 | 32 / 32 |
| 168 | 523 / 512 | 28 / 28 |

本表只说明候选支持的几何规模，不选择实验窗口、不运行dispatch、不设置概率，也不证明联合continuation可用。
现有Google744小时同钟配对继续作外部描述性/稳健性证据，不能替代RTS网侧请求和Alibaba业务合同。

## 4. formal-ready逐项证据要求

| 顺序 | 必须完成的对象 | 当前证据与缺口 | 完成证据 |
|---|---|---|---|
| 1 | 完整continuous科学协议 | 当前仅机制草案；期限/会计/删失/映射/coupling仍未注册 | 自包含YAML/spec、完整验收矩阵、明确科学决策、fresh pre-seal及exact-sealed独立R4 PASS |
| 2 | continuous网侧输入合同与实现 | normal、连续事故kernel、原赋值/同轨迹actual交接、事故态owned短求解及固定业务实际功率构模/赋值检查已有开发验证与限定pre-seal；固定动作联合网络短求解37项新测试/236项回归与预审闭合；因果输入信息合同已有草案、generator及正式连续dispatch包仍缺 | 新输入/状态schema；小例、ramp/min-up/down/事故跨日守恒、E0和unresolved合同、独立审查 |
| 3 | 四臂continuous planner与证书 | 已有开放前缀kernel、逐时见证、canonical赋值审计及短求解DRAFT；complete/causal证书仍缺 | horizon/cohort/carry/预算模型，解析oracle与小型solver，LB/UB/gap/残差，四臂非嵌套归因 |
| 4 | fixed-policy holdout与识别 | 固定声明容量策略、部分响应和诊断已开发；训练容量绑定及正式风险定义仍缺 | 容量进入执行约束，揭示时序、失败定义、风险分母、删失区间、coupling/transport/bootstrap合同与测试 |
| 5 | 数据包与实现闭包 | raw margins/公开交付存在；连续dispatch包未发布 | 全成员hash、完整支持与窗口权重、无泄漏、原始/机制字段隔离；不得拿历史checkpoint补正式包 |
| 6 | solver/runtime/runner | 历史solver确认不自动涵盖新规模；V7仍DRAFT | 新规模许可证与资源门、短pilot（若需长pilot先授权）、执行快照/lease/失败窗口/Windows验收、fresh独立审查 |
| 7 | 启动前核验 | 当前没有该continuous实验的formal-run authority | exact科学/代码/输入/runtime一致、无开放finding、资源/进程/目标目录核验；执行前单独明确授权 |

网侧输入补充：逐小时N-1 outage overlay揭示机制已有`event_disclosure.py`、36项新测试/63项相关回归
及限定pre-seal闭合，见`rq2_event_disclosure_v1.md`。这只补事件可见性接口；normal事前信息、单小时网络输入、
请求生成/调度选择及真实来源适配仍缺，不能据此关闭第2项或把截断event end当repair。

正常计划审计与单小时信息隔离已有`grid_information.py`及36项新测试/179项相关回归、限定pre-seal闭合。
该接口将normal预测作为显式事前机制输入，当前actual条件另传；计划真实发布时间/选择规则、actual carry、
单小时网络验收及请求生成仍未完成，不据此关闭因果输入门。

后续当前小时网络验收已有`current_grid_step.py`，41项新测试/173项相关回归及限定pre-seal闭合，
见`rq2_current_grid_step_v1.md`。它只补给定固定功率及赋值的actual carry，未实现owned短求解、请求/dispatch选择或因果证书。
第2项仍未完成，不能以这一单步验证替代完整continuous输入包。

单小时owned短求解后续已开发并完成限定pre-seal，见`rq2_current_grid_short_solve_v1.md`：37项新测试与193项相关回归通过。
当前可提供给定实际功率的赋值见证及受控carry，仍缺共同请求定义、dispatch选择规则和完整输入包；第2项保持未完成。

共同reference候选第一步LP/赋值审计已开发，44项新测试/193项相关回归及限定pre-seal闭合，见`rq2_reference_grid_v1.md`。
原赋值审计不选择或发布G，也不提供reference后继。后续数值selector与受控跨小时状态已开发，
当前验收记录见`rq2_reference_selector_v1.md`；各臂actual selector、共同请求适配及完整链仍缺，第2项保持未完成。

actual selector后续已开发并完成限定pre-seal，46项targeted/220项相关回归通过，见`rq2_actual_dispatch_selector_v1.md`。
该接口选择给定功率下的候选网侧末态，未连接共同请求适配和业务/网络双提交；第2项仍未完成。

共同请求exact G/U适配后续已完成限定pre-seal，38项targeted/223项相关回归通过，
来源审计绑定split/seed/hour且保留normalization，见`rq2_common_request_adapter_v1.md`。
跨小时mapping固定、reference来源与业务prefix联合提交及业务/网侧双状态事务仍缺，第2项继续未完成。

网侧正式输入生成本身可能需要单独长运行：届时先交付可审阅的已验收grid候选，再申请对应运行权限，
不能把“准备到可开始正式实验”解释为现在已授权1071块或新的多日grid正式计算。
旧V7修复按原记录保留；连续科学/数据门未明确前不把其运维验收当作主线替代品。

## 5. 当前动作与审查性质

本轮已读代码确认网侧free-boundary缺口，并取得窗口计数。只读`sol_modeler`提供关键路径建议；
其意见是设计审计，不是official verdict，不生成seal/receipt，不开启任何gate。
用户随后明确先补尚未覆盖拒绝及实际动作语义；已有B6共享后继开发与审查，显式部分响应开发见
`docs/model_spec/rq2_continuous_partial_response_v1.md`。这些组件复用原债务与四臂账，主容量/正式协议门仍待关闭。
所有原冻结协议、结果和用户未提交文件保留，不清理仓库。


## 2026-09-20 四臂连续小时协调开发

`episode_coordinator.py`已连接单对象内存中的四臂共同请求链、固定策略、公平物理/业务初态、整窗最坏预算预检和逐小时预留。
保留各臂独立停止；末小时保留恢复债务，窗口消费完不代表完整履约。完整小时输入、候选、外层提交、已开始/未完成/未开始臂分别记录。
`hourly_transaction.py`同步区分dispatch执行异常与求解前网络输入拒绝，缺失执行结果不猜零调用。
独立pre-seal 31项episode（44.69s）及23项hourly（32.10s）通过，findings闭合；九文件323项相关回归通过（170.08s，exit 0）。
完整合同、开发hash和命令见`docs/model_spec/rq2_episode_coordinator_v1.md`；旧22/291项记录保留为此前版本证据。
下一项为完整episode证据的持久化及无solver重放，再处理跨进程唯一性/恢复；现有业务prefix不能替代reference→mapping→business→actual全链。
本组件仍为DRAFT_NONAUTHORITATIVE。完整连续输入、训练容量与四臂策略绑定、正式规模、恢复/right-censoring及科学/正式运行门未关闭。
所有初态与未识别业务参数保持机制声明；没有新增真实运行观测、正式结果、容量/安全认证或formal-run authority。


## 2026-09-20 完整episode重放的原生证据前置核

新增`grid_evidence_replay.py`，保存原生求解记录并相对于独立提供的canonical模型重算结构、原生赋值、completion、残差、目标、状态与bound投影。
不从JSON直接制造owned求解结果或可执行cursor；缺失原生记录保留partial/unresolved。报告显式model_relative_only，未验证来源/selector chain及外部builder效果。
58项针对性通过（20.58s），独立58项通过（20.15s）；修复后六文件276项相关回归通过（122.60s，exit 0），限定pre-seal findings闭合。
详细合同、命令和hash见`docs/model_spec/rq2_grid_evidence_replay_v1.md`。现有episode、hourly transaction与两个selector源码未改。
下一项先接reference/actual专用stage及选择链重审，再完成全episode归档、无solver重放和跨进程恢复；当前不能声明完整episode持久化已完成。
本轮新增的是机制开发证据，非真实运行观测；完整连续输入、训练容量、恢复/right-censoring、正式规模和科学/正式运行门保持开放。


## 2026-09-20 Reference/actual选择链来源绑定重放

`selector_replay.py`已实现独立输入/policy绑定、逐级canonical模型重建、目标锁定/物理重审及完整结果身份比对；公开接口只返回诊断。
完整拒绝与partial中断分别记账；partial只验证此前prefix，不产生所选末态或恢复游标。
独立pre-seal发现partial单级及总调用数可联动改小，现按capture阶段绑定调用数并拒绝create与post-call证据混存。
修复后100项targeted通过（78.41s），独立100项通过（79.66s），finding闭合；七文件348项相关回归通过（223.48s，exit 0）。
合同、命令与开发hash见`docs/model_spec/rq2_selector_replay_v1.md`。现有episode/hourly/两类selector及原生重放核源码保持。
下一项为全episode来源绑定归档与无solver重放，连接mapping、业务动作与实际功率、预算预留及外层提交；随后验收跨进程唯一性与安全恢复。
本组件仍为DRAFT_NONAUTHORITATIVE；没有新增真实观测、正式结果或认证。完整连续输入、训练容量与策略绑定、正式规模、恢复/right-censoring及科学/运行门仍未完成。


## 2026-09-20 完整返回episode归档与来源绑定重放

`episode_replay.py`已连接独立初态/逐小时输入、reference选择链、共同映射、四臂业务动作至exact实际功率、actual选择链及外层提交的无solver重放。
完整返回链逐字段比对；partial只报告证据可达prefix，真实actual gap之后可保留未验证后缀；外层中断必须回滚且保留预留。
缺返回不能冒充合法成功或零调用；重审同小时已返回臂并核known/unknown调用及started/skipped/incomplete/unattempted库存。
最终39项targeted通过（170.63s），独立39项通过（176.58s）；限定pre-seal findings闭合。
四文件192项相关回归通过（289.75s），对应最后interrupted-error非空门和相同依赖清单提取之前的直接前驱；最终局部变更由39项完整targeted覆盖，未重跑同范围broad。
合同、精确hash与命令见`docs/model_spec/rq2_episode_replay_v1.md`。原selector重放、hourly transaction与episode coordinator源码保持。
下一必要工作为跨进程唯一执行、持久化提交及安全恢复，包含尚缺invocation journal的in-flight边界；当前不提供可执行恢复游标。
本组件仍为DRAFT_NONAUTHORITATIVE；完整数据、训练容量/固定策略绑定、正式规模、恢复/right-censoring及科学/运行门保持开放。无新真实观测、正式结果或证书。


## 2026-09-20 本地事务日志与开发恢复

`episode_store.py`已接入同一规范NTFS目录内的合作进程排他、SQLite intent/result事务、完整来源重放后的开发续跑。
调用前commit并重新打开核intent；已有intent但无result保持unknown并禁止重跑，结果commit响应丢失通过inspect与外部保留head对账。
每个新archive须延续此前已提交的exact历史和前态；复制目录、schema/源/提交链漂移、reparse/hardlink与不完整初始化均拒绝。
独立31项targeted通过（360.92s），同一最终字节三文件101项相关回归通过（562.22s，exit 0），限定pre-seal findings闭合。
覆盖真实进程竞争、五个os._exit崩溃窗、提交异常、NTFS路径及历史改写反例；进程退出测试不等于断电硬件认证。
`episode_replay._verify`现在私有返回诊断及完整重建snapshot，公开wrapper仍只返回诊断；最新source/hash与完整命令见`docs/model_spec/rq2_episode_store_v1.md`，旧验证历史保留。
本组件仍为DRAFT_NONAUTHORITATIVE，仅沿用120调用/60秒短预算；没有生产lease、正式运行授权或新真实观测。
下一必要工作为正式网络规模与continuous输入适配的仓库核查/开发；完整数据、训练容量/固定策略绑定、恢复/right-censoring及科学/运行门保持开放。


## 2026-09-20 真实来源适配与H=25构模机器证据

新增source_normal薄层，将固定RTS文件manifest、显式request/initial/carry和zero/one-based小时映射绑定；不推定初态或认证split/trajectory。
真实H=25 build-only已落盘完整输入与依赖：22275变量/28004约束、solver_calls=0。此前只有文字计数的缺口现有可重算开发记录。
此例使用热机全关/零出力/min-down age机制初态，未证明前序网络可行性，不能作为已发布normal plan或正式数据输入。
24项source适配测试与normal/grid-information相关回归共142项通过（17.06s）；产物hash/时钟/映射/非认证flags核验通过。
合同、命令、最终产物及源码hash见`docs/model_spec/rq2_source_normal_v1.md`。旧冻结文件和开发中间记录均保留。
剩余真实输入义务包括power-block来源/split/trajectory映射及normal assignment；158 UID选择器规模、训练容量、完整恢复与科学/正式运行门仍开放。

独立pre-seal最终复跑24项通过（2.04s），限定范围findings闭合；最终构模JSON与runner/adapter/计数模块及40个依赖源码hash独立核验匹配。详细证据见`rq2_source_normal_v1.md`，无official gate变化。


## 2026-09-20 公开边缘连续窗口提取

新增source_window，复用已有continuation审计，按显式split/raw起点/长度及power seed提取唯一连续chain窗口，保留原始CSV值及训练归一化依据。
真实power seed20260822的holdout链从4440开始；split边界4392周边排除小时不能补造。workload holdout继续使用training peak，>1值不裁剪。
四份独立25h power/workload training/holdout样例已create-only落盘并从源重建逐字段一致；不声明同钟或已注册coupling，不生成可执行episode。
三文件64项相关测试通过（4.39s），已有输出覆盖尝试exit2且hash不变，diff检查通过。合同/命令/产物hash见`docs/model_spec/rq2_source_window_v1.md`。
下一项连接power窗口身份到normal assembly/carry，再按登记机制处理workload功率映射。真实normal assignment、158 UID执行规模、训练容量、恢复及科学/正式运行门保持开放。

公开来源窗口独立pre-seal完成：同范围64项通过（4.42s），四份记录完整来源重建及身份hash独立匹配，限定范围无开放实质finding；正式门不变。


## 2026-09-20 电力窗口与normal来源绑定

新增power_normal_binding，从外部assembly/window/config身份重建两端并核split、seed、trajectory、raw/continuous小时、timestamp、系统负荷及RTS源manifest。
真实25小时来源对应已落盘：最大系统负荷差0.0 MW，solver_calls=0。CLI预审发现的现场身份自比较已修为必填外部expected assembly pin，首次派生记录保留。
五文件164项回归通过（18.81s），产物身份/源码hash/时钟与非认证flags核验通过。详见`docs/model_spec/rq2_power_normal_binding_v1.md`。
本层只证明来源对应；初态仍为机制声明，未证明前序网络可行、normal赋值或事故dispatch。
下一项为workload→业务功率机制映射与coupling合同；真实normal assignment、158 UID执行规模、训练容量、完整恢复与科学/正式运行门仍开放。

电力窗口/normal绑定独立pre-seal最终18项通过（1.56s），外部pin finding闭合，最终产物/core/test/runner hash核验一致；限定范围无开放实质代码finding，正式门不变。


## 2026-09-20 workload数值投影与精确功率接口

核查真实1632小时：普通float(raw)*250在training599/816、holdout592/810个in-range小时不满足CommonRequestMapping精确十进制恒等式；精确十进制乘积再投float对应553/543，报告分开公式和计数。
新增显式half-even数值投影，保留raw与有符号误差；不放宽旧接口，不自动clip。250MW/12dp仅为开发声明，816training+810holdout投影后精确等式成立，6个holdout原>1保持unresolved。
四文件97项回归通过（14.36s），含独立Decimal全1632行oracle；source-bound checked诊断重新生成与落盘逐字段一致，diff检查通过。
详细合同、命令、最终hash与中间记录边界见`docs/model_spec/rq2_workload_projection_v1.md`。原数据和旧协议保持。
正式精度/功率映射与raw>1策略尚未注册；CFE/coupling、业务恢复合同、真实normal赋值、执行规模及正式门继续开放。

workload数值投影独立pre-seal最终19项通过（0.22s），两项findings闭合；全源精确等式/误差/6项超界及两类计数独立复算一致，最终产物与源码hash匹配。正式门不变。


## 2026-09-20 独立来源显式配对与CFE请求暂存

新增source_pair，外部pin重建同split的power/workload独立窗口，显式relative-offset机制配对；normalization绑定原训练来源、投影/功率规则。
复用完整既有CFE target缺口公式，不乘occupancy或截断请求；grid0明示待reference填写的空槽。两个raw时钟分别+1保留各自前边界，不声称同钟。
任一小时projection未解决则顶层hours=null，全部诊断行保留。training25h正例staged，holdout1190..1214含5个超界的25h例unresolved。
两份DRAFT声明和create-only诊断已从源完整重建相等；五文件114项相关测试通过（17.06s），hash与diff检查通过。见`docs/model_spec/rq2_source_pair_v1.md`。
下一项绑定pair动态baseline到normal request；旧常量250MW构模例不能替代。真实normal赋值、规模执行、训练容量、恢复与正式coupling/科学门仍开放。

source_pair独立pre-seal三文件54项通过（5.46s），两份JSON/声明/pair identity及实现hash匹配，限定范围无开放实质finding；114项broad采用主线程证据，正式门不变。


## 2026-09-20 配对动态baseline与normal输入

新增pair_normal_binding，外部pair/assembly身份重建后复用power来源核查，逐小时精确校验normal DC baseline=pair投影MW=occupancy*U；私有快照隔离caller变更，未解决pair在网络来源前拒绝。
真实H25先derive候选身份，再用外部保留pin verify并构模，22275变量/28004约束、solver_calls=0；动态baseline为0.0093335315–0.02631222675MW，原250常量声明保留。
该范围是所选开发窗口/线性机制结果，不是功率标定、正式代表样本或履约证据。两阶段完整输入与pair逐小时等式已核验。
五文件152项回归通过（17.84s），模式/pin/产物hash及diff检查通过。详见`docs/model_spec/rq2_pair_normal_binding_v1.md`。
下一项需合法normal赋值及current连接；H25变量与158 UID selector调用数仍超既有短预算，正式规模合同与科学/运行门保持开放。

动态normal绑定独立pre-seal限定范围无开放实质finding，最终两阶段产物/身份/输入/模式flags复核一致；独立44项对应新增2项CLI测试前库存，最终152项由主线程覆盖。正式门不变。


## 2026-09-20 连续真实规模执行合同草案

新增`docs/model_spec/rq2_continuous_scale_execution_contract_v1.md`，把前置normal、逐小时reference/actual与完整任务资源分开。
代码核查确认episode预留不含normal及构模/审计/归档；solver TimeLimit总和不等于wall-clock、内存或存储上限。
保留158 UID选择语义时H25四臂预留19900次，加一次normal为19901次；这是完整路径计数，不是实测耗时或成功保证。
下一实现明确为normal-only后继入口：外部输入/规模/资源pin、完整原生证据、normal.optimal及无错witness后才接prepared/current。
草案列出规模、求解与进程时间、RSS/存储、许可/pilot、未知调用及六步验收义务；不扩展旧GridDevelopmentBudget或EpisodeBudget。
本轮只有文档设计及源码/产物hash/计数核对，没有solver、代码行为变更或正式门变化；所有后续实现/真实规模pilot证据仍待补齐。


## 2026-09-20 独立normal短执行内核

新增`normal_execution.py`及规格`docs/model_spec/rq2_normal_execution_v1.md`，实现外部input/execution/实际scale绑定的单次normal执行，复用原canonical模型和原生证据核心。
保留normal.optimal且完整witness无错的接受门；可行但未最优、资源超限及返回后身份漂移保留证据并拒绝接受，缺raw的中断调用数保持unknown。
新预算独立于旧GridDevelopmentBudget，旧selector/episode上限不变。资源记录为同步observed wall、Windows进程生命周期peak working set及core数值payload大小；不是强制终止或完整归档门。
结果明确hard_resource_limits_enforced=false、durable_invocation_tracking=false、public_source_binding_verified=false；完整结果identity绑定raw/witness、资源及错误字段。
当前只推进了normal-only内核，真实来源接入、独立进程/持久化监督、完整归档资源验收及真实规模normal验证仍待补齐；正式实验门保持开放。

独立normal内核最终四文件216项回归通过（41.52s），独立54项targeted通过（18.54s）；完整result identity与core字节命名两项pre-seal findings闭合。
最终source/test hash与命令见`docs/model_spec/rq2_normal_execution_v1.md`；旧candidate/episode源码hash保持，diff及新文件空白检查通过。该证据仅支持tiny同步内核，正式门不变。


## 2026-09-20 公开来源与normal执行连接

新增`source_normal_execution.py`与规格`docs/model_spec/rq2_source_normal_execution_v1.md`，把已核验assembly/pair动态baseline接入独立normal内核，前后从源重建绑定。
连接层独立核assembly/pair/binding/input/kernel/source execution外部pins，重算绑定内容摘要；检查内核成功标志与raw/witness/调用/状态一致。
post-source失败保留内核证据并拒绝外层接受；无完整内核返回仍记调用数unknown。来源报告以不可变JSON保存，完整返回有内容identity。
此层仍无独立进程/持久化intent/完整归档资源监督；旧kernel及来源适配源码保持。真实H25用来源重建测试在kernel边界停止，没有真实RTS求解。
下一步先核查已有transport_v5所属子进程监控和episode_store事务日志的复用适用性，旧冻结资源阈值/receipt/授权不继承；再补normal监督与真实规模验证。

来源连接层最终独立覆盖32项（31项17.65s及真实H25来源边界1项103.14s，均exit0），主线程相关五文件124项通过（24.17s）。
assembly/pair直接pin、绑定正文摘要及内核成功证据一致性findings闭合；最终hash/命令见`docs/model_spec/rq2_source_normal_execution_v1.md`。
H25仅完成来源连接验证，数值内核在测试边界停止；没有真实网络normal赋值或正式运行，监督/持久化/真实规模/科学门继续开放。


## 2026-09-20 Normal一次性开发调用日志与监督复用核查

新增`normal_store.py`，复用旧episode的NTFS路径/文件身份/合作进程排他原语，独立normal schema绑定完整运行请求和源码。
intent经SQLite DELETE/FULL事务提交并重新连接读回后才调用source-normal；已有intent禁止重试。完整encoded result及identity有独立字节门、提交与读回。
重开可用外部genesis/current head核对丢失返回；只提供returned_record_unreplayed诊断，不恢复owned游标、不认证native来源或数值结果。
原normal/kernel/source执行模块及旧episode存储源码保持；当前仍为同步执行，真实RTS求解与正式门未变化。
独立复用核查确认旧transport_v4/v5缺明确HANDLE ABI、存在PID二次打开窗口且没有父死亡保护；这些原语不能直接继承到新normal监督器。
下一项为显式wintypes、同一保留HANDLE及Job/释放握手的normal进程监督，再补完整资源/结果重放验收；旧冻结阈值、源和结果保留。详见`docs/model_spec/rq2_normal_store_v1.md`。

Normal日志最终独立19项通过（26.06s），相关55项通过/1项未重复H25（55.94s）。create/head模式finding闭合，四个os._exit窗、跨进程排他、readback/提交响应丢失及完整record门有开发证据。
最终source/test hash和命令见`docs/model_spec/rq2_normal_store_v1.md`；旧episode_store及source execution hash保持，diff通过。独立进程监督/父死亡保护、数值replay、真实规模和正式门继续开放。


## 2026-09-20 Normal 开发子进程所有权原语

新增`normal_process.py`与`docs/model_spec/rq2_normal_process_v1.md`，使用显式WinAPI ABI和创建时JOB_LIST绑定，持有同一process HANDLE，挂起核查后单次释放；Job非继承且kill-on-close，提供每进程commit门与短时deadline终止。
真实短子进程测试覆盖父死亡三个窗口、异常退出、后代终止、内存分配拒绝、旁观进程不受影响及创建后中断句柄回收；没有solver或真实电网求解。相关process+store回归41项通过（27.47s）。
这只完成监督链底层所有权原语，尚未连接normal专用worker/持久化请求与结果核对，也未补Job总内存/系统commit储备、数值重放和真实规模验证。正式门保持开放；旧冻结源、结果及未提交文件保留。


Normal进程原语独立pre-seal限定范围无开放实质代码finding；规格中崩溃窗口措辞已按实际注入位置修正。最终22项独立targeted通过（1.04s），源码与测试hash见`docs/model_spec/rq2_normal_process_v1.md`。后继worker仍须补请求/环境身份绑定、同线程或并发合同、整Job静默后读取工件以及资源/日志/数值重放验收；不能把进程原语测试升级为完整监督或正式运行通过。


## 2026-09-20 Normal worker 与一次性日志连接

新增`normal_worker.py`，已把显式输入/运行pins、受限环境、挂起Job worker与原normal_store连接：父目录排他、request及launch intent持久化、worker exclusive claim、normal intent/result日志、整Job静默后parent readback。normal_process draft补同线程校验、显式环境、Job总commit与quiesce。
worker正常退出且有完整记录仅标returned_record_unreplayed；零退出无结果、超时、中断和提交后异常退出均不升级成功，也不自动重试。下层normal_store/source execution/kernel及旧冻结transport未变。
主线程process+worker+store相关回归68项通过（57.92s），含tiny 1秒/1线程HiGHS、三类intent/result崩溃窗、worker重复claim、环境漂移及未静默禁止读结果。正例来源边界为明确synthetic stub；固定worker入口另验证真实来源缺失拒绝，未执行RTS求解。
下一项为持久化normal结果的独立数值重放；系统commit储备、父进程/整个任务资源与磁盘验收、真实规模normal/current/四臂及科学注册门仍开放。详见`docs/model_spec/rq2_normal_worker_v1.md`。本轮非正式开发，不产生seal/receipt/正式运行授权。


Normal worker连接最终相关回归69项通过（62.41s），最新24项worker独立targeted通过（34.95s）。实际argv及摘要已加入launch并由worker核对sys.orig_argv，claim/Observation绑定launch摘要；旧进程规格明确区分历史快照与当前合同。限定范围预审finding已修复；完整资源验收、独立数值replay及真实规模证据仍待补齐，详见`docs/model_spec/rq2_normal_worker_v1.md`最终验证记录。


worker监督后续补齐两项实测证据：Job合计内存160/256 MiB成对控制，以及worker已提交intent后的集成父死亡窗口。新增3 cases主线程6.57s、独立6.54s均通过；限定范围pre-seal findings闭合。它们补充此前69项相关回归，仍不构成normal数值重放、真实规模或正式门通过。最终source/test hash及精确命令见`docs/model_spec/rq2_normal_worker_v1.md`。


## 2026-09-20 Normal 保存结果独立数值重放

新增`normal_replay.py`与`docs/model_spec/rq2_normal_replay_v1.md`：以外部record/result/store/replay/input/execution pins核对持久化内容，前后重建来源绑定，固定normal模型复用既有纯数值replay核，复核赋值/目标/残差/界投影，重新计算完整normal witness并核对接受标志。store入口要求独立保留的当前结果head，不以genesis替代。
初步targeted29项通过（49.87s）。生成tiny记录后禁止solver factory、normal/source执行入口，重放无native求解；重算哈希的赋值/目标/资源/标志篡改仍不能接受。partial/timeout/缺返回保留未决状态，不恢复执行游标、不认证原生来源或最优性。
旧normal/source/kernel/store/worker/native replay源未修改。相关回归与独立预审继续核验，正式门保持开放；完整资源、真实规模normal/current/四臂、恢复/风险/科学注册仍待对应证据。


## 2026-09-20 Normal 数值重放最终开发验证

normal_replay 已补齐资源拒绝的精确计数、保存计时的 float 类型与偏序、lifetime peak 单调性、spec/budget/scale 编码类型，以及 admission/native/canonical 构模计时数量检查。保持成功标志并重算哈希的篡改反例也被拒绝；来源后检失败在来源恢复后仍保持 unresolved。
最终四文件相关回归 177 passed in 148.23s；独立 targeted 46 passed in 82.15s。限定范围 pre-seal findings 已闭合，完整命令和最终 source/test hashes 见 `docs/model_spec/rq2_normal_replay_v1.md`。旧 normal/source/store/worker/native replay 文件哈希保持。
以上支持 tiny 合成网络及显式来源 stub 的记录一致性，不认证 native 执行历史、资源测量或真实 RTS 求解，不生成 seal、receipt 或正式授权。
下一必要工作为整个 normal 任务的资源验收：父进程输入准备/归档/重放预算、系统 commit 储备、临时文件与归档磁盘边界及故障停止规则。已有 worker 的子进程 Job 限制和单条 payload 字节门不能替代这些项目；真实规模 normal/current/四臂、恢复/右删失及科学参数注册门继续开放。


## 2026-09-20 Normal 主机资源余量观测原语

新增 normal_resources.py 和 docs/model_spec/rq2_normal_resources_v1.md：固定 Windows ABI 观测系统 commit 与 caller-available 磁盘余量；明确追加需求/储备，同卷需求合计、储备取最大、采样可用空间取最小。外部 identity 绑定目录 dev/ino/volume GUID、预算与源码，前后检查；失败不返回 sufficient 报告。
相关 resources/process/store 回归 82 passed in 29.79s；独立 targeted 35 passed in 1.86s，限定范围无开放实质代码 finding。测试包括真实只读 Windows 调用和目录替换，以及模拟边界、配额可用量不足与 API 故障；没有 solver 或磁盘/内存压力运行。
本项仅补只读观测及声明比较，未接入 worker，未创建资源预留或硬配额。下一项是完整 normal 任务监督连接：内部固定调用 observer，覆盖输入准备、执行、审计、归档及重放，明确父进程与子进程预算、专用临时目录、持续观测/停止及写入失败保留规则；不能信任 caller-supplied observation。真实规模、科学注册与正式运行门保持开放，旧冻结代码、结果及未提交文件保留。


## 2026-09-20 整任务来源准备入口与监督范围核查

新增 normal_task_inputs.py 及规格 docs/model_spec/rq2_normal_task_inputs_v1.md，以有界三文件声明与独立 assembly/input/pair/binding/scale pins 重建完整来源输入；保留机制初态和 build-only 角色，实际重建 binding，前后核声明及依赖。准备结果沿用 owned construction，不能直接构造或 dataclass.replace；不形成执行授权。
最终相关回归 99 passed, 2 deselected in 21.55s；独立短测 33 passed, 1 deselected in 4.17s。最终真实 H25 来源准备单独 1 passed in 52.13s，内部准备50.381511秒，solver factory禁止调用；assembly/binding保持原固定产物身份，未重新构模或获得真实normal赋值。两项限定pre-seal findings已闭合，最终哈希/命令见规格。
监督核查确认旧worker的输入deepcopy/encode/store初始化位于Job外，replay也未纳入。既有scale execution contract已补两阶段task设计：受限execution/archive child，全Job静默后保留结果pins，再起独立replay child；尚缺task process owner、wire-level pin捕获、固定runtime reserve采样/停止、私有scratch及phase日志故障验证。旧60秒process/worker和30/60秒kernel预算保持；不得把一次准备耗时当引擎pilot或调阈值依据。正式实验门仍开放，旧冻结结果与未提交文件保留。


## 2026-09-20 Normal 整任务进程监督原语

normal_task_process.py 已实现独立任务预算、固定 host reserve 采样、deadline/资源/API/身份失败停止，以及整 Job 无活动成员和直接子进程已退出的共同确认；记录 process/Job peaks，不推断 solver 状态。运行中只比较 reserve，避免重复计入已分配需求。公开 normal_task_child contextmanager 覆盖初始化、交接和 finally 清理，直接构造拒绝。

主 targeted 34 passed in 6.78s；task process/process/resources 相关回归 97 passed in 7.81s；独立 targeted 34 passed in 5.91s。初始化前后与 base constructor 返回中断、父死亡、资源竞态等限定范围 pre-seal findings 已闭合。最终 source/test hashes 和命令见 docs/model_spec/rq2_normal_task_process_v1.md。旧 normal_process 字节与 60 秒限制保持。

本项尚未接入 phase intent、来源准备、normal execution/store 或 replay。下一项为整 Job 静默后 controller 有界读取并独立保留归档 lineage pins，再连接 execution/replay 两阶段，避免在 controller 重建完整 assembly。磁盘是采样式停止而非硬配额；完整任务故障验收、真实规模求解、四臂恢复/右删失及科学注册门继续开放。没有正式运行，旧冻结协议/结果和所有现有未提交文件保留。


## 2026-09-20 Normal 归档身份有界捕获

新增 normal_archive_capture.py 与规格 docs/model_spec/rq2_normal_archive_capture_v1.md。Controller 可在独立确认 Job 静默后，复用旧合作式 lease，在同一只读 SQLite 事务中核精确 schema/header/intent，分块哈希 opaque record，沿旧公式保留 current head 和 record SHA；result identity 仅保留 external claim，交原 replay_normal_store 核验。此入口不加载完整 assembly/赋值，不把不透明字节一致性提升为数值或 native 认证。

数据库/metadata/record/lock 有明确读取边界；残留 sidecar/reparse、来源/文件漂移、扫描/分块 deadline 和中断均拒绝返回 pins。无 result 仅 unused/unresolved_intent，不推断原生调用次数、不重试。只读指数据库连接，原 lease 仍 r+b 打开锁文件；deadline 是合作式检查，不是硬实时 I/O 保证。

capture/store/replay 相关回归 94 passed in 235.45s；之后补 lock/sidecar 边界，最终 targeted 31 passed in 30.07s，独立 targeted 31 passed in 31.66s。限定范围 pre-seal findings 闭合；最终 source/test hashes 与命令见规格。旧 normal_store、normal_replay、episode_store、normal_process 源码哈希保持，未启动真实 RTS 求解或正式实验。

下一必要工作为 compact request 与两阶段 phase controller/worker：把来源准备、normal 执行/归档放入受限 Job，持久化 intent/launch/claim，Job 静默后捕获 pins，再启动独立重放 Job。需同时补私有 scratch、父进程预算与准备/执行/结果/重放各故障窗口；claim 来源与 Job 静默不能由本 capture 返回值自证。真实规模 normal/current/四臂、完整恢复/右删失和科学注册门继续开放，旧冻结协议、结果及现有未提交文件保留。


## 2026-09-20 Normal compact request 与两阶段固定 worker

新增 normal_task_worker.py 和规格 docs/model_spec/rq2_normal_task_worker_v1.md：小型 typed request/64 KiB phase packet 不携带 assembly 或赋值，绑定来源/normal/replay pins、环境、实际模块和 Python 可执行文件。worker 验证 controller 预存 intent/launch 与实际 PID/creation FILETIME/argv/cwd/environment 后才 exclusive claim，再进入固定 prepare→旧 store execute 或重新 prepare→旧 replay 路径。完整 replay 诊断经字节门/fsync/readback 后才写 small completion；异常保留 intent/claim，不能自动重试。完成记录仍是 worker 声明，不是 controller 数值验收。

相关 task_worker/task_inputs/oldworker 回归 81 passed, 1 deselected in 170.68s；之后补准备后运行上下文复核，最终 targeted 26 passed in 78.71s，独立 targeted 26 passed in 76.31s，限定范围 pre-seal findings 闭合。测试包括显式 tiny 来源 stub 的 execute→capture→独立 replay（replay 禁止 solver），运行上下文漂移、写入失败、丢失 completion，以及真实固定 argv 挂起 Job 的缺失来源负例。真实入口短测试初始被 host commit 准入拒绝，收紧本测试 process/Job 上限后通过；不能推断真实规模资源充足。最终 hashes/命令/准确证据边界见规格，六个复用模块字节保持。

下一项是父 controller：外层排他、phase 顺序、专用 scratch、父进程/Job/磁盘预算、release 前持久化 intent/launch、Job 静默后的独立小文件与 capture/report 核验，并补各父死亡/写满/SQLite/fsync 窗口。当前尚未有完整任务 supervisor 或真实 RTS 求解，normal/current/四臂真实规模、完整恢复与右删失、科学注册及正式启动门继续开放。旧冻结协议、结果和现有未提交文件保留。


## 2026-09-20 Normal 整任务顺序 controller

新增 normal_task_controller.py 与 docs/model_spec/rq2_normal_task_controller_v1.md，连接现有 compact worker、受限 Job、opaque capture 与 numerical replay。外层 lease、专用 scratch、release 前 intent/launch、进程身份和整 Job 静默核验、独立保留 pins、完整有界报告及 replay 后第二次 capture 已接通；报告复读与 archive pins 共同检查最终归档一致性。成功持久文件仅为最终写入前验证快照；API 在最终写入/回读与 elapsed 检查后才返回开发流程完成。数值报告继续区分 accepted/unresolved/inconsistent，全部正式权限标记为 false。

资源合同保留 process/Job commit 限制、host reserve 采样、父进程 lifetime working-set 观测与有界目录盘点；没有硬磁盘配额或整任务资源认证。故障保留已有 intent/claim/store/report，不自动重试。测试使用明确 tiny synthetic 来源与真实 Windows Jobs；未修改入口的缺失来源负例另测。真实公共数据、机制参数、synthetic fault injection 分开标注。

本轮曾完成 26 项基础测试、56 项故障扩展测试；最终源码、相关回归、独立 targeted 计数与 hashes 以 controller 规格的开发验证记录为准。公共数据交付包 6 个输出绑定、复合诊断包 7 个文件哈希和 8 个复用模块源码哈希核验一致。连续多日、恢复债务、四臂及拒绝动作/诊断已有开发产物继续复用。

下一必要工作为真实来源 normal 整任务受限端到端验证，以及 normal witness 到 current/episode 的输入与时序交接；不能把 normal terminal carry 当成 incoming origin。真实规模 full-UID selectors/四臂资源、完整恢复与右删失、风险分母和科学注册/正式启动门仍开放。本次不变更旧冻结协议或结果，不清理现有未提交文件。


Controller 最终验证补记：相关回归 186 passed in 289.44s；最终单时钟判定修复后定向 5 passed, 56 deselected in 27.79s；独立最终 targeted 61 passed in 133.65s。首次定向复测遇到实时 host commit 余量拒绝，原预算重跑通过，详情见规格。限定范围 pre-seal findings 闭合，不关闭真实规模、整任务资源或正式门。最终 source/test hashes 见 docs/model_spec/rq2_normal_task_controller_v1.md。


## 2026-09-21 真实来源 H25 整任务首次短验证与诊断缺口

已新增固定开发声明 configs/rq2_normal_task_h25_development_v1.DRAFT.yaml 与薄入口 experiments/audit_rq2_normal_task_v1.py；入口默认只读，显式开发调用绑定 exact YAML/script SHA。主/独立声明测试均7项通过；沿用原机制输入，固定HiGHS单次1秒/1线程，Job/process各768 MiB，未扩展科学或正式预算。

首次实际调用已终态，controller为unresolved_task_attempt/execute，25.562秒；子进程exit1，整Job静默true。仅保留request/intent/launch/claim及观测，没有normal store/completion/capture/replay。process/Job峰值接近声明cap，runtime host reserve没有拒绝；但无child traceback，不能认定具体异常/limit触发，也不能推断solver_calls=0或数学不可行。此次不重试、不换root、不放宽预算。完整22工件hash索引在 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/summary.json，合同和日志位置见 docs/model_spec/rq2_normal_task_h25_development_v1.md。

当前下一必要工作已收敛为独立零solver来源准备诊断：同source pins和768 MiB上限，记录prepare/assembly/binding阶段与有界异常栈，先区分来源准备失败与后续执行失败。诊断不会追认原attempt确切异常。normal真实来源成功、current/episode交接、四臂/恢复/右删失、资源与科学注册/正式启动门继续开放。旧冻结协议/结果、已有未提交文件和失败attempt全部保留。


## 2026-09-21 来源准备探针定位身份编码 MemoryError

独立零solver prepare probe已执行一次并终态；保持原source-request pin与768 MiB process/Job cap，117秒phase+3秒quiet。实际11.016秒exit1、Jobquiet=true，无host reserve/API error；保留阶段before_prepare→source_assembly_enter，捕获本次probe的MemoryError，栈为continuous_grid_normal.normal_input_identity→_digest→_encode。详见 docs/model_spec/rq2_normal_task_h25_development_v1.md 及 results/tables/rq2_normal_prepare_probe1_non_authoritative/probe.summary.json。13项新probe证据另存prepare_probe1_evidence.json；原attempt1及22项hash均保持。此结果不追认attempt1异常，不认证cap唯一因果或数学不可行。

据此新增独立identity_stream.py原语，流式处理dataclass/序列，mapping/set保留旧repr排序与局部物化。内容字节/hash差分与合成内存分配测试26项通过；与旧normal相关回归108 passed in14.98s。它尚未接入任何执行路径，合成编码峰值改善不等于真实H25资源通过。旧normal源码将自身hash纳入依赖，因此后继接入必须显式绑定新实现并保留旧声明/结果，不能静默更新原pins。

下一必要工作为受限真实来源下验证新编码的身份等价性和内存表现，再设计明确绑定实现的接入；来源准备、normal/replay/current/四臂真实规模与恢复/右删失、科学注册和正式启动门继续开放。


流式原语最终补记：独立相关回归108 passed in14.70s，限定pre-seal无开放实质finding；source/test hashes及命令见docs/model_spec/rq2_identity_stream_v1.md。独立核验确认原22项及新probe13项bytes/hash均匹配。后继先清点source assembly/validate、pair binding、normal execution/store/replay全部身份调用点，设计显式绑定新原语与adapter bytes的后继合同，再开展真实H25身份/资源验证；不把局部替换当作完整接入，不复用旧execution pin宣称新实现已执行。


## 2026-09-21 流式来源组装后继与全链清点

已新增独立 source_normal_stream.py（DRAFT_NONAUTHORITATIVE），在外部 implementation pin 下复用来源校验/loader及原输入验证，流式计算完整年度输入摘要；新类型分别保留 normal 内容、旧 assembly 内容对照、新实现和新 assembly 身份。旧代码、旧执行 pins、失败 attempt 和 probe 保持，不能用新候选冒充旧执行记录。接入清单已覆盖 prepare、pair/power binding、kernel build、execution/store/replay，以及 common_request_adapter/grid_information/outage_trajectory，详见 docs/model_spec/rq2_source_normal_stream_v1.md。

主相关回归165 passed in17.91s，含33项新适配器测试；原 attempt 的22项、probe的13项文件bytes/hash核验一致。独立审查提出的loader原对象冗余引用已在hash前释放，并用weakref测试验证。本次仅完成来源候选层，尚未接入整任务，未执行真实H25或solver。下一必要工作是独立受限零solver H25来源组装的内容对照与资源验证，再依清单接通后继链；完整prepare/normal/current/四臂资源、恢复右删失、科学注册及正式启动门继续开放。


## 2026-09-21 真实 H25 流式来源组装验证完成

独立流式来源候选已取得真实数据证据：probe2保留完整8784小时RTS数据，25小时请求对应raw0..24/source1..25；normal内容摘要d9959966…与旧assembly内容reference626f7dbe…均复现，新assembly身份689ac1bc…独立记录。source阶段8.862秒，进程10.89秒exit0、Job静默true，51次采样；process/Job commit峰值339828736/341061632 bytes，低于原768 MiB cap，working-set峰值362663936 bytes，无reserve/API error，solver_calls=0。机制初值与workload-power映射标签保持，不转为真实观测。

先前probe1在来源开始前exit1；只读复算定位到环境dict插入序导致父子进程身份不同。保留v1/probe1全部字节，v2只修复环境指纹重建并验证实际键值，独立55项通过。完整证据与边界见docs/model_spec/rq2_source_normal_stream_v1.md；probe2 root为results/tables/rq2_stream_source_probe2_non_authoritative，13工件hash索引为results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_source_probe2_evidence.json。

下一必要工作已从“验证来源流式编码”推进到后继power/pair binding与prepare整链接入，须保留独立实现pins并核验重复重建/快照的资源。此次只证明一次来源候选内容复现与受限进程观察，未证明完整prepare、normal执行/replay、current/四臂资源、完整恢复或右删失口径；科学注册与正式启动门继续开放。原22+13+11项历史工件及新13项bytes/hash均核验一致，未清理仓库。


## 2026-09-21 流式 binding 与 prepare 整链接入完成（开发态）

已新增pair_normal_stream.py与normal_task_inputs_stream.py，贯通pinned机制声明→流式来源组装→来源重建→power窗口对应→pair业务baseline→完整prepare。来源重建的owned快照供power和baseline共用，省去额外年度assembly deepcopy；旧内容报告canonical JSON与原saved binding逐字节核验，新source/binding/prepare指纹独立绑定。旧full-input hash/binder不在新prepare路径中，旧执行链未被修改。

相关回归140 passed,1 deselected in19.52s；独立binder+prepare targeted45 passed in14.71s，限定pre-seal无开放实质finding。排除项为旧uncontained真实H25准备测试，未用tiny结果声称真实资源通过。规格、命令、hash与边界见docs/model_spec/rq2_normal_task_inputs_stream_v1.md。原22+13+11+13项工件bytes/hash保持。

下一必要工作为同768 MiB开发预算下的一次受限零solver真实H25完整prepare验证，重点观察caller assembly与rebuilt同时存在的峰值，再接normal execution/store/replay及current/四臂。科学参数仍按机制假设标注；来源/prepare开发进展不关闭恢复右删失、风险分母、科学注册或正式启动门。


## 2026-09-21 真实 H25 完整流式 prepare 验证完成

受限零solver探针已终态成功：prepared_content_reproduced，errors=[]，完整8784小时数据保留，旧normal/assembly/binding内容全部复现，并单独记录新prepare/binding identities。prepare本体31.440253秒，进程33.734秒exit0、Job静默true，156次采样；process/Job commit峰值474931200/476151808 bytes，working-set峰值496750592 bytes，无reserve/API error。原768 MiB上限保持；initial state/workload-power等机制假设仍未变成真实观测。

probe主相关114项、独立69项通过后运行一次；15项证据索引为results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_prepare_probe1_evidence.json，详细命令、hash和分段耗时见docs/model_spec/rq2_normal_task_inputs_stream_v1.md。历史22+13+11+13项与本次15项bytes/hash均匹配，旧失败记录/源码全部保留。

下一必要工作推进到normal模型build/audit与数值执行的流式后继，覆盖内部旧normal identity调用，随后连接store/replay/controller与current/四臂。此次只验证完整输入准备，未求解normal或验证assignment，whole_task_resources_verified/formal_result均false；恢复右删失、风险分母、科学注册及正式启动门继续开放。

## 2026-09-21 流式 normal 模型与同步内核开发

新增 continuous_grid_normal_stream.py 与 normal_execution_stream.py，保持旧模型和数值门，另绑新实现及执行身份。合成 H1/H25/H49 的完整变量、约束线性系数与目标逐项对比一致，assignment 故障与原生求解失败语义验证通过；旧执行 pin 不能授权新内核。两项新模块及旧模型/旧内核/identity_stream 相关回归共242 passed in63.40s。详见 docs/model_spec/rq2_normal_execution_stream_v1.md。

本轮仍为 DRAFT_NONAUTHORITATIVE，真实来源证据止于完整prepare；新内核尚未接入来源执行/store/replay/controller，未证明真实 H25 assignment 或整任务资源。下一必要工作为消费独立新 source/prepare/binding pins 的来源执行后继，随后完成持久化和独立回放。历史五批74项工件bytes/hash保持一致。科学注册、恢复右删失及正式启动门保持开放。

独立只读 R3 pre-seal 审查：两新文件80 passed in32.28s，未发现需返工的实质finding；同步检查不能替代Job硬资源限制，外层来源绑定与整任务资源仍待验证。此次无official verdict/receipt。


## 2026-09-21 流式来源执行与声明入口开发

新增 source_normal_execution_stream.py 和 normal_declared_execution_stream.py，接通外部 pinned request→完整流式prepare→source/pair重建与binding→normal kernel→返回后声明及实现链复核。tiny三小时合成网络经过实际HiGHS求解，objective=120、terminal carry.source_hour=3；公开loader/package仍为synthetic fixture，不能视为真实RTS规模或业务观测。

新入口要求独立的新source/binder/assembly/binding/request/kernel/source execution pins，旧内容reference不授权新执行。post-source或post-declaration失败保留已返回数值证据及调用数，缺完整owned返回保持unknown，无自动重试。详见 docs/model_spec/rq2_source_normal_execution_stream_v1.md。

下一必要工作为把声明入口接入已有一次性intent/result日志的流式后继，并实现嵌套证据独立replay，再接controller/worker Job监督。真实H25证据仍止于prepare，whole-chain资源、current/四臂、恢复右删失、风险分母、科学注册和正式启动门继续开放。旧五批74项诊断工件bytes/hash一致。

最终相关回归201 passed,1 deselected in155.96s，排除旧未受Job监督的真实H25测试；独立只读R3 pre-seal审查无开放实质finding。详细测试与工件SHA见上述规格，未生成official verdict/receipt或正式运行授权。


## 2026-09-21 流式声明一次性日志开发

新增 normal_declared_store_stream.py，接入完整声明执行入口。日志只持有小型pinned request，在独立intent COMMIT及readback后才运行prepare/source/kernel，保存完整DeclaredStreamingNormalResult嵌套证据。沿用NTFS lease和SQLite事务合同，新schema/application ID与旧日志分离。首轮19项通过，覆盖四个真实进程退出窗口；新增声明漂移、wrong返回、intent早于prepare和完整wire核验，详见 docs/model_spec/rq2_normal_declared_store_stream_v1.md。

当前日志只提供一次性调用与内容完整性，numerical_evidence_replayed/native_execution_authenticated/formal_result仍false。下一必要工作是独立重建并回放三层nested result的流式replay，再接worker/controller Job监督与真实H25资源验证。旧五批74项诊断工件bytes/hash一致；current/四臂、恢复右删失、风险分母、科学注册和正式启动门继续开放。

主相关回归81 passed in202.15s，独立新日志26 passed in100.65s；限定R3 pre-seal审查无开放实质finding。源码、测试hash及完整命令见日志规格，未生成official verdict/receipt或正式运行授权。


## 2026-09-21 流式声明日志独立回放开发

新增 normal_declared_replay_stream.py，从独立pinned request重建prepare/source/binding，解析声明→source→kernel三层wire，零solver复核原生数值、完整assignment/witness、调用记账和timing/peak/payload。store入口要求独立current head，genesis不授权数值回放。新增拒绝词表与静态错误投影、prepare role消费门，修复伪造降级拒绝可被误判一致的pre-seal finding。详见 docs/model_spec/rq2_normal_declared_replay_stream_v1.md。

结果仍区分archive consistency与原生/测量认证，native_execution_authenticated/resource_measurements_authenticated/resume_authorized/formal_result均false；历史动态异常只能核记录相容性，不认证其实际发生。下一必要工作是接入固定worker、归档捕获及controller的流式schema后继，在Job内覆盖执行与独立replay，再验证真实H25全链资源。旧五批74项工件bytes/hash一致，current/四臂、恢复右删失、风险分母、科学注册和正式启动门继续开放。

验证：78项全组通过后，末次phase审查补2项反例明确复现失败，修复后受影响16项通过；旧normal/native回放相关104项通过。各批范围、命令和最终源码/测试SHA见回放规格，不把前一候选的通过结果冒充最后修复的直接证据。

末次独立只读R3 pre-seal受影响6项通过，最终SHA一致，两轮findings闭合；未生成official verdict/receipt或打开正式门。


## 2026-09-21 流式声明归档有界捕获开发

新增 normal_archive_capture_stream.py，复用原budget和64 KiB只读分块捕获，连接新声明日志schema/application ID与declared execution pin。result claim仍opaque，必须经独立replay核验。补齐unused时header执行pin交叉核验，新增反例先复现失败再修复；双向旧新schema隔离、禁止prepare/model/solver和完整capture→replay链已有tiny测试。

相关回归91项通过后完成上述修复，最终新capture全组36项通过；旧五批74项工件bytes/hash一致。详细命令/范围/SHA见 docs/model_spec/rq2_normal_archive_capture_stream_v1.md。下一必要工作为固定worker及controller接入，必须保留prepare后求解前的packet/cwd/environment/argv与身份复核位置；当前尚未实现这一连接。真实H25全链、Job资源、current/四臂、恢复右删失、风险分母、科学注册和正式启动门继续开放。

独立只读R3 pre-seal全组36项通过，最终SHA一致，finding闭合；未生成official verdict/receipt或运行授权。

## 2026-09-21 流式固定 worker 与求解前运行态复核

新增 normal_task_worker_stream.py，把独立 compact pins、一次性声明日志和独立 replay 接入固定 execute/replay 分支。声明入口和日志的未seal draft 增加 before_source 检查位置；固定worker在 intent COMMIT/readback→prepare 后、source求解前核对 packet/cwd/environment/argv/intent/launch/claim及身份。检查失败保持 unresolved intent，不求解、不重试。旧worker/controller及冻结输入和结果不变。详见 docs/model_spec/rq2_normal_task_worker_stream_v1.md。

相关回归118项通过，另6项因新增测试漏传重开日志 required expected_head 而失败；修复测试后6项重跑通过。独立replay相关8项通过。完整命令、分批范围与当前SHA见规格，不把此记录写成最终124项整组通过。五批74项历史工件bytes/hash一致。

下一必要工作是流式controller后继：消费新的declared/source/native嵌套报告，保留两Job顺序、静默后独立双capture及完整资源门。真实H25观测仍止于完整prepare，尚无新全链assignment或整任务资源证明；current/四臂、恢复右删失、风险分母、科学注册与正式启动门保持开放。

独立只读R3 pre-seal审查最终worker全组29 passed in125.44s，journal callback定向2 passed,26 deselected in6.39s；最终源码/测试SHA一致，无开放实质finding。该结论不认证Job membership、整Job静默或资源上限；controller接入和真实H25全链仍待完成。未生成official verdict/receipt或运行授权。

## 2026-09-21 流式controller与真实H25全链开发观测

新增 normal_task_controller_stream.py，完成declared/source/native三层报告核验、顺序两Job、静默后独立双capture和完整报告复读。pre-seal发现未知/重复错误及遗漏native错误投影的降级报告漏洞，四项反例先复现失败再修复；最终报告23项、controller与runner68项、相关134项通过；独立报告/双Job24项及runner7项通过，finding闭合。详见 docs/model_spec/rq2_normal_task_controller_stream_v1.md。

随后新目录真实H25单次短开发验证完成：总274.39秒，execute151.094/replay119.812秒，均exit0且整Job静默，Job commit峰623742976/624693248 bytes，低于原805306368上限。capture前后pins一致，replay archive_consistent=true/errors为空，但数值仍unresolved：native calls=1、solution_count=0、aborted/maxTimeLimit；normal总耗时67.5576574秒超过60秒门。没有有效assignment或terminal witness，不能推断数学不可行，也不报告全四臂/恢复/工程认证。初态和业务功率映射仍为机制参数。

旧五批74项工件保持；新增结果索引 stream_task_attempt1_evidence.json 绑定54项，SHA4f5c61bc8f4ebfa615448cfbbb29c45ae25409e8d290c8583847ae9aff001f1c。原始观测、预算和解释见 docs/model_spec/rq2_normal_task_stream_h25_development_v1.md。相关代码与声明现被真实工件绑定，后续使用明确后继，不覆写本次记录。

下一必要工作：定位normal preflight/pipeline和末端检查的时间开销，保持全部身份/数值/资源门；随后取得有效normal assignment，再接current/episode。whole_task_resources_verified仍false；完整UID/four-arm、恢复右删失、风险分母、科学注册及正式启动门继续开放。


## 2026-09-27 真实H25零求解组件成本定位

normal组件探针已完成：最终相关193项通过，独立审查发现并闭合父进程汇总前后实现漂移窗口，两项反例先失败后通过。一次真实H25测量保留完整8784小时来源和原768 MiB上限，正常退出且Job静默，86.125秒，Job commit峰476012544 bytes，solver_calls=0，model_builds=1；normal/assembly/binding内容复现。详见 docs/model_spec/rq2_normal_component_cost_probe_v1.md。

完整input identity两次分别10.223881/9.739884秒，model build10.610566秒（含内部校验），完整prepare47.835529秒。下一必要工作为保留逐字节编码与全部检查位置的身份编码性能后继；本次测量未细分验证/递归编码/SHA成本，不能直接外推旧67.56秒或声称60秒门已过。尚无有效normal assignment，随后仍须完成current/episode与完整UID/four-arm资源验证。

29项证据索引 normal_cost_probe1_evidence.json 位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative，SHA7f0d5fa4fb3fce23588bbb117bfa319ca3abdb1f987e609ff6a240ac924a9e50。六批历史128项索引绑定、公开数据交付包7文件、复合诊断7文件与16依赖核验一致；连续多日、恢复债务、四臂、拒绝动作与诊断已有产物继续复用。机制初态与功率映射仍非真实业务观测；恢复右删失、风险分母、科学注册及正式启动门继续开放。


## 2026-09-27 身份编码后继的真实等价与性能对照

新增identity_stream_fast.py，保持原JSON字节、float hex与repr排序，完整重算验证/依赖，不缓存输入或摘要。相关新旧identity/cost回归157项通过，独立identity41项通过。新增受限对照probe相关170项及独立差分14项通过；旧实现和既有工件全部保留。

真实H25一次零solver对照已完成：四次old/fast内容摘要一致；旧identity9.834936/9.786799秒，新6.865299/6.754984秒，本次耗时减少30.19%/30.98%。Job98.625秒、exit0且静默，commit峰475328512 bytes，仍在原768 MiB上限内。数值模型仍使用旧kernel，未验证新kernel或60秒门，也未产生assignment。

详见 docs/model_spec/rq2_identity_stream_fast_v1.md；31项索引为 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/normal_identity_comparison_probe1_evidence.json，SHA08eee9f3134b3f82e6eb59a3c5fd920fb087e99178b3b16979a1f08d0166d316。下一必要工作为接入独立normal模型/内核后继，保留全部身份复核和数值/资源门，再验证完整执行链。有效normal解、current/episode、完整UID/四臂资源、恢复右删失、风险分母、科学注册及正式启动门仍开放；机制初态与业务功率映射仍非真实观测。


## 2026-09-27 快速编码接入normal模型、内核与声明入口

新增continuous_grid_normal_stream_fast、normal_execution_stream_fast、source_normal_execution_stream_fast和normal_declared_execution_stream_fast四个独立后继。新CONTRACT、owned result类型与execution pins区分实现；保留模型全矩阵、全部身份复核位置、数值/资源门、source前后绑定与求解前callback。来源prepare/binder继续复用现有stream路径。旧源码、配置和八批188项历史工件bytes/SHA保持。

新旧模型/kernel相关204项、来源/声明/prepare/binder相关115项通过；随后新增callback失败窗口四项，定向9项通过，未声称最终119项单次整组通过。独立模型/kernel31项、来源/声明4项及新增callback4项通过，pre-seal测试覆盖缺口闭合。tiny完整声明链得到objective120、terminal source_hour3，仅为显式合成来源；详见 docs/model_spec/rq2_normal_execution_stream_fast_v1.md。

下一必要工作为新类型的持久化日志和独立replay后继，随后连接固定worker/controller并做真实H25受限验证。尚未运行真实fast kernel，不把此前编码30%改善外推为60秒门通过或有效normal assignment；current/episode、完整UID/四臂资源、恢复右删失、风险分母、科学注册和正式启动门继续开放。机制初态与业务功率映射仍非真实观测。


## 2026-09-27 fast日志、回放、归档与固定worker接入

新增normal_declared_store_stream_fast、normal_declared_replay_stream_fast、normal_archive_capture_stream_fast与normal_task_worker_stream_fast独立后继。新schema/application ID/owned types与旧链隔离，intent先于prepare、完整三层数值回放、current head要求、opaque有界capture和prepare后source前运行态复核保持。旧文件与八批188项工件bytes/SHA一致。

日志/回放首轮108项及后加隔离定向6项通过；capture首轮37通过1项测试fixture失败，修正多余fixture依赖后最终全38项通过；worker首轮29项及后加旧request type定向1项通过。分批计数不混写为最终一次全组结果。独立日志/回放7项、四个真实进程窗口4项、capture4项、worker关键链8项及旧type1项通过；限定pre-seal审查无开放实质finding。详见 docs/model_spec/rq2_normal_persistence_stream_fast_v1.md，含命令、准确时间及最终hash。

下一必要工作为fast controller消费新worker/request、capture和三层replay报告，保留两Job顺序、整Job静默后双capture与原资源门，再做真实H25受限开发验证。当前仍只有tiny正例和真实固定argv缺失来源负例，未运行真实fast kernel或取得有效normal解；不能从编码改善推断60秒门通过。current/episode、完整UID/四臂资源、恢复右删失、风险分母、科学注册及正式启动门继续开放，机制参数继续与真实观测区分。


## 2026-09-27 fast controller 与真实 H25 单次验证终态

fast controller/runner 已接通新 worker、双 capture 和三层 replay；最终相关回归 92 passed in 223.37s，独立 pre-seal 定向 9 项及 34 项通过。一次受限 H25 开发任务已结束，execute/replay 均 exit 0 且 Job 静默，归档和来源回放一致。normal 63.5284186 秒超过原 60 秒；1 秒 solver 调用返回 aborted/maxTimeLimit、solution_count=0，无 assignment/witness，仍为 unresolved，不能解释为数学不可行。

API 返回 completed_development_replay_diagnostic，落盘 observation 为 validated_before_final_observation_write，分别保留。新 76 项证据索引 stream_fast_task_attempt1_evidence.json 的 SHA256 为 91dda12ffceb2463b3fa1fda666ede79d23d0b888953a223e3e3eb1d1ca94a69，位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative；旧八批 188 项 bytes/SHA 重核一致。详情见 docs/model_spec/rq2_normal_task_stream_fast_h25_development_v1.md。整任务资源、native authentication、formal/security 门均未解除；机制初态与业务功率映射不是真实观测。

下一必要工作改为进一步定位 normal 身份复核/构建/加载耗时，并独立诊断 1 秒求解无可行解；保留原限额和复核点，在明确后继中开发。本次绑定代码/配置/结果保留，已有连续多日、债务、拒绝动作、四臂及回放组件不重复开发。有效 normal、真实 current/episode、完整 UID/四臂资源、恢复右删失、风险分母、科学注册及正式启动门继续开放。


## 2026-09-27 身份分段定位与数值映射编码对照

真实 H25 零 solver 分段测量已完成：validation 0.0039583 秒、dependencies 0.0165303 秒、encoding+digest 4.7174440 秒，优先优化编码有实际依据。新分段工具 100 项、相关旧工具/fast 编码 136 项通过，独立窄测 8 项及 33 项结果索引审计闭合。详情见 docs/model_spec/rq2_normal_identity_breakdown_probe_v1.md。

新增 identity_stream_numeric 仅特化 exact primitive-key/float-value 字典，保留完整 repr 排序、finite/float.hex、旧类型回退与所有 validation/dependency 复核，无缓存。新旧编码相关 118 项通过，独立新 51 项及 2000 个随机映射字节/摘要对照一致。真实对照 probe 首轮多余参数错误已修复，最终 156 项及独立 4+28 项通过。

一次真实零 solver 对照取得 fast 5.4537921/5.1988746 秒、numeric 4.3547956/4.2227902 秒，单次局部观测下降约 20.15%/18.77%，所有输入摘要与模型结构保持。Job 88.078 秒、exit 0 且静默，commit 峰 474370048 bytes；仍使用 fast 模型，尚未验证 numeric kernel 或 60 秒门。37 项索引 normal_numeric_identity_probe1_evidence.json 的 SHA 为 7ce289bed9a74d99e1e39fc495f8f8813e06443e6ff5f0eb25a7349b57ec4dfe，位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative。详见 docs/model_spec/rq2_identity_stream_numeric_v1.md。

下一必要工作为 numeric 编码的独立 normal 模型/kernel 后继及完整链验证；1 秒求解无可行解仍单独 unresolved。机制初态与业务映射仍非真实观测，有效 normal、current/episode、完整 UID/四臂资源、恢复右删失、风险分母、科学注册和正式启动门继续开放。既有多日/债务/拒绝动作/四臂产物及全部历史协议、代码、结果保留。


## 2026-09-27 numeric 完整执行链与 H25 开发终态

numeric normal 模型/kernel/source/declared、持久化/独立回放/capture/worker/controller/runner 后继均已接通。完整矩阵、所有身份复核点、旧机制与资源/数值门保持；numeric fallback 依赖显式绑定。root 分组终态为179、121、118、71、61、33 passed，独立 pre-seal finding 闭合；不是单次全组统计，也不构成 official review 或正式授权。

一次 numeric H25 开发任务已完整结束，normal 53.8714377 秒，本次未触发原60秒超时；native仍为1 call、aborted/maxTimeLimit、solution_count=0，无assignment/witness，数值状态保持 unresolved。execute/replay147.25/121.656秒，均exit0且Job静默；双capture和零solver replay一致。不同运行时点的53.87与旧63.53秒不可用来证明受控性能提升或一般资源保证。

新99项索引 stream_numeric_task_attempt1_evidence.json，SHA d5679002d9c4a388a4c955eb4a95096321169196eb26bf3c1a266d46180ad983，位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative；自包含11个历史索引映射，旧334条bytes/SHA保持。详细测试、命令、预算、记录和解释见 docs/model_spec/rq2_normal_task_stream_numeric_h25_development_v1.md 及其引用的三个实现规格。

下一必要工作转为独立有界的native求解阶段诊断，区分model transfer、presolve和搜索；现有证据不能定位1秒无solution的内部原因，不能据此放宽门槛或宣称不可行。有效normal、真实current/episode、完整UID/四臂资源、恢复右删失、风险分母、科学注册与正式启动门继续开放；机制初态和业务功率映射仍非真实观测。所有现有未提交文件、旧协议和结果保留。


## 2026-09-27 native 求解阶段诊断

单次有界 H25 开发诊断已完成：set_instance 1.7605765秒、optimize 1.0094633秒、legacy interface 2.7725891秒；1 call，aborted/maxTimeLimit、noSolution，simplex_iteration_count=4844、mip_node_count=0。进程exit0且Job静默，60.969秒、commit峰526721024 bytes。计数器不能证明不可行，presolve/搜索细分仍未知；接口耗时不能与旧完整normal pipeline直接作性能差值。

helper/runner独立pre-seal已闭合；helper独立36项通过，补齐最终runner依赖pin后runner85项包含于215项相关回归终态。新38项证据索引 normal_solver_phases_probe1_evidence.json（SHA256 5ed4385cf074e0dc5e260a7ba11ab3c3d7ea1c6f0fd70449b303e46939f6ad89），位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative；另复核12个历史索引的433条证据一致。完整规格、预算、测试时序和结果解释见 docs/model_spec/rq2_normal_solver_phases_probe_v1.md。

当前仍缺满足原最优性和witness验收的有效normal。下一项是预先固定后继有界可行性验证的预算、成功标准及失败语义，保留原1秒探针与全部旧结果；不把到时无解当不可行，也不以incumbent代替原验收。真实current/episode、完整UID/四臂资源及正式实验门继续开放，机制初态和业务映射仍非真实观测。

本次独立只读结果审计已闭合，38项新证据与433项历史证据、进程/来源/身份/计时链均复算一致，无开放实质finding；不构成official verdict或正式实验门证据。


## 2026-09-27 五秒完整 normal 开发终态

固定5秒、1 thread的numeric完整任务已执行一次，无重试。normal51.3511618秒、errors=()，native仍为1 call、aborted/maxTimeLimit、solution_count=0，无assignment/witness。60秒normal及全部数值门保持，未解不能判不可行。execute/replay131.438/103.297秒，均exit0且Job静默，独立回放archive/source一致、errors=[]、solver calls=0；accepted_record_reproduced=false。API completed_development_replay_diagnostic与落盘validated_before_final_observation_write对应不同写入时点。

新20项与旧runner8项共28 passed（5.29秒），独立20项通过。新98项索引 numeric_5s_task_attempt1_evidence.json（SHA256 4dc646b77c9e5aa71114b577117fc6a6493976c6e0a0fc6f7d9bcdb2cca55af6），位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative；另13个历史索引/471条旧证据复核一致。详见 docs/model_spec/rq2_normal_task_numeric_5s_h25_development_v1.md。

下一步核对当前Gurobi接口与相同模型的有界交叉验证路径，复用已有adapter和旧跨引擎证据，不继续机械增加HiGHS时间。旧pilot不直接认证当前H25，正式引擎选择与正式运行门保持关闭；原机制初态、业务映射与未解状态不变。


五秒结果独立只读审计已闭合，98/98新项、13个历史索引/471条旧证据及结果解释一致。随后tiny检查定位当前Pyomo默认Gurobi接口的solution status字符串与现有严格枚举门不兼容；新增独立direct接口draft，在pytest内注入后通过原native/完整assignment/normal witness逻辑，补齐类型定义源码绑定后15项测试通过。该factory尚未集成到独立身份的H25执行与回放链，不能作为有效H25 normal或正式引擎选择证据。详见 docs/model_spec/rq2_gurobi_direct_development_v1.md；下一项为该接口的最小normal后继集成。


## 2026-09-27 Gurobi direct 完整链与许可证阻塞

Gurobi direct 的 normal/source/declared/store/replay/capture/worker/controller 后继已接通。最终分组检查为核心156、store/replay118、worker/controller/reports117、runner20项通过；capture40项在此前分组通过，独立pre-seal实质finding已闭合。共享数学模型、机制输入、容差和资源门保持，已有连续多日、恢复债务、四臂及拒绝动作实现无需重建。

固定5秒、1线程H25开发任务已执行一次：normal42.8698899秒，native调用因 `Model too large for size-limited license` 失败，并保留 `structure_options_or_version_drift`；没有assignment/witness或可行/最优证据。execute/replay122.797/102.828秒，均exit0且Job静默；零solver回放确认archive/source一致，accepted_record_reproduced=false。该失败属于运行环境/许可容量阻塞，不能解释为数学不可行或Gurobi求解性能不足。

宿主存在GRB_LICENSE_FILE指定的许可文件；当前受控environment未传入该键，继承的exact whitelist亦不允许该键。下一必要工作是显式许可证路径传递的最小后继及同受控环境容量核查；许可文件内容不进入仓库，不修改本次已绑定源码/配置/结果。现有tiny测试不足以证明许可容量。真实current/episode、完整UID/四臂资源、恢复右删失、风险分母及正式实验门继续开放；业务映射与初态仍是机制假设。

本次122项证据索引为 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/gurobi_direct_task_attempt1_evidence.json，SHA256 289173afc81967b76eeb7cbc58ed8588fd695d5313f9eda2234ecfc79d9c0da0；另14个历史索引/569条旧证据经root复核一致。详细范围和实测见 docs/model_spec/rq2_normal_gurobi_direct_chain_v1.md。

独立只读结果审计已核对122项新证据及569项历史证据一致。许可变量未传入受控child已确认；calls=1是wrapper调用前计数，不证明进入optimize。structure_options_or_version_drift是异常路径中pre_structure=None触发的次生guard标签，不是独立观测到漂移。该结果保留为环境失败，不开启正式门。

## 2026-09-27 许可修复与首份H25完整可行赋值

显式许可环境后继已完成，同受控环境22275变量/28004约束合成容量检查通过。复用既有normal内层，仅后继环境codec、worker/controller及声明runner；125项外层、20项runner、2项身份反例通过，独立pre-seal闭合。固定5秒H25首次得到完整可行赋值；零solver回放确认assignment/witness、来源及残差一致。许可阻塞在该环境已排除。

有效normal门仍开放：原生到时终止、optimal=false，所报界相对gap约0.267%；完整normal71.429665秒，超过原60秒门。下一工作针对完整赋值路径的校验开销及有界最优性，保留全部数值/资源标准，随后才推进真实current/episode。机制初态和功率映射仍非真实观测；四臂资源、恢复右删失、风险分母与正式注册/运行门不变。

详细证据见docs/model_spec/rq2_normal_gurobi_licensed_v1.md；新138项索引gurobi_licensed_task_attempt1_evidence.json位于results/tables/rq2_normal_task_h25_audit_v1_non_authoritative，SHA256 fd6d0f32a768866282b4dd2b1211c817956d4ede16daa5ca9f53847abdfdd9b2；另15个历史索引/691条证据已复核一致。

独立只读结果审计已闭合：138项新工件、691条历史证据以及赋值/witness/回放、双capture、计时与验收字段一致，无开放实质finding；不构成official verdict或正式门授权。

## 2026-09-27 结构身份等价比较

新增单次调用内变量名复用与primitive优先编码helper，保留原完整结构字段/排序/数值规则。87项组合及3项新增依赖漂移反例通过；独立pre-seal闭合。一次零solver H25构模ABBA比较的四次结构摘要与旧e18f值一致：旧1.79–1.83秒/次，新1.29–1.43秒/次。Job47.891秒、exit0且静默；只证明局部等价及本次耗时，不能外推完整normal的60秒门。

暂不为此局部收益机械后继整条执行链；下一项复用既有numeric输入身份约4.22–4.35秒/次的观测，优先降低完整编码成本并保留全部检查位置/字节。有效normal最优性、60秒及后续正式门仍开放。详见docs/model_spec/rq2_grid_structure_fast_v1.md；新118项索引grid_structure_fast_probe1_evidence.json（SHA256 fb1291f309030428ee9377c25d8593969188e55f31e51945faf33edcb574287b），另16个历史索引/829条旧证据一致。

## 2026-09-28 完整输入编码比较与执行集成

完整年度输入ABBA比较已完成，numeric约3.93秒/次、ordered约2.12秒/次，四次输入摘要一致；零构模、零solver。122项新证据及947条历史证据的独立结果审计闭合，详见docs/model_spec/rq2_identity_stream_ordered_v1.md。此局部改善支持接入完整链验证，不能直接推出60秒通过。

当前必要工作为gurobi_ordered完整执行集成：保留全部检查、源数据与机制参数、60秒/768MiB门，预先固定单次15秒求解预算；runner20项测试通过，内外层回归及独立pre-seal进行中，尚未启动新H25任务。详见docs/model_spec/rq2_normal_gurobi_ordered_v1.md。有效normal、真实current/episode及四臂完整资源、恢复尾部与正式协议门均未据此关闭。

完整集成验证及独立pre-seal现已收束，单次H25运行与零solver回放完成：normal56.4923187秒，在原60秒门内，完整赋值/witness及回放一致且errors=[]；15秒求解到时，optimal=false，gap约0.125%，normal_accepted=false。当前normal阻塞已集中到最优性，下一步针对有界求解收敛，不再新增独立编码探针；本次normal余量约3.51秒，不能直接延长求解并假定总门可过。详细状态、界和资源见docs/model_spec/rq2_normal_gurobi_ordered_v1.md。169项新证据索引gurobi_ordered_task_attempt1_evidence.json，SHA256 1aeebb6f2ea6b1416f689f232c95d2fc9b7473265f8233b0754f43b6a1810da3；18个历史索引1069条证据保持。正式门及其他科学输入缺口继续开放。

同配置单次15秒convergence诊断已完成：根松弛约0.5秒，约2秒进入搜索，终态730节点、原生SolCount=9，仍TIME_LIMIT，日志gap约0.1263%。这定位到已进入分支搜索后的有界收敛问题；尚不能归因某一具体启发式。下一项验证声明的线程并行度，保留模型与数值/资源门，不据此选择正式引擎。156项新索引gurobi_convergence_probe1_evidence.json（SHA256 008be53a6cf7593c27b5ac6903026103eeef96d45ade190d5a7aeca81d2b795d），19个历史索引1238条证据一致。细节及诊断/完整执行的计时区别见docs/model_spec/rq2_gurobi_convergence_profile_v1.md。

Threads参数=4的单次15秒诊断现已完成：仍TIME_LIMIT，原生1721节点/SolCount10，日志gap0.203%；Job62.656秒、commit峰752758784 bytes，在768MiB内。child60.0569秒属于prepare+diagnostic，不能与normal60秒门混用。参数回读不认证实际worker利用率，顺序单次结果不支持因果性能比较。该attempt未收敛，不接入完整normal链；下一步核查可行赋值warm start的输入/结构同一性、审计及累计成本前提，不重复已有连续transition/reserve envelope，也不添加会删除crossing trajectories的逐时排序。160项新索引gurobi_four_thread_probe1_evidence.json（SHA256 30bf1e3de7bea997d7418b0efd343a447a9d7f9c2b493f2f5c95b5fddc96a175），20历史索引1394条证据一致。详见docs/model_spec/rq2_gurobi_four_thread_profile_v1.md；正式门保持。

## 2026-09-28 warm start前提与资源门来源核查

零solver读取既有H25 SQLite：完整性正常，6806997-byte record的SHA256仍为2fc450ac5e19e434dcb8e2f7408b9beb442e89113e732f1d3cec63967d54173e；loaded_values为22275个唯一、有限值，与initial_values有序变量名一致。可作为候选start，不证明新调用收敛。复用来源链已有一次solver调用，必须区分新调用计数与累计来源成本；不能把离线求解结果视为免费外生观测。

进一步核实normal的30秒solver/60秒wall上限来自短开发内核，normal_accepted也不等于formal-ready。旧ordered声明及结果保留原60秒门；这一开发cap不自动成为所有正式任务的科学验收标准。现有EpisodeBudget仍最多120次/60秒solver预留，而H25全158 UID路径需要19900次加normal一次，说明完整资源合同依然是独立缺口。

当前动作调整为先形成真实规模资源方案及验收矩阵，明确normal、current/selector、全episode与预计算成本；暂不新增warm-start整条执行链或H25探针。保持gap、残差、物理约束、来源、右删失及四臂公平性，未改变任何旧预算或启动更长运行。细节见docs/model_spec/rq2_normal_warm_start_feasibility_v1.md。
## 2026-09-28 显式任务清单核算实现

新增execution_workload.py和规格docs/model_spec/rq2_execution_workload_v1.md。由显式normal/episode清单核算完整UID reference及四臂actual调用和各自solver预留；共享normal仅按明确依赖计一次，每个容量评估仍独立列项。拒绝重复ID、缺失依赖、split/输入/UID不一致和非连续或越界小时，不默认将46 cells视为完整任务数。报告回显完整声明，固定保留来源/复用、清单完整性、wall/内存/磁盘和正式注册未解项；不提供执行准入。

26项零solver针对性测试通过（1.53秒），与现有EpisodeSession._requirements及独立逐阶段枚举一致。只读核对既有source record的158 UID/25行，示例预算normal15秒、selector每阶段1秒得到19901 calls/19915秒solver预留；这不是建议预算或真实运行。进一步确认reference/actual入口只接受max_calls<=20的GridDevelopmentBudget，无法容纳160/159级，不能只提高episode cap后运行。下一项补独立真实规模selector/episode资源合同，保留完整阶段与原数值审计；旧执行类型、配置和结果未改。
## 2026-09-28 完整串行资源声明合同

新增execution_resource_contract.py和docs/model_spec/rq2_execution_resource_contract_v1.md，在显式workload清单上要求每个normal/episode都有完整wall、非solver开销、Job commit、archive/scratch、线程及模型规模上限。检查单任务预留、总wall、最大串行Job加supervisor/reserve，以及不回收scratch的全量磁盘需求。预算短缺逐项报告，完整声明可重建；declaration_consistent不表示资源实测或运行准入，三个资源验证/授权/formal标志固定false。

组合42项零solver测试通过（主代理1.59秒、独立复跑1.58秒），代码限定审查无实质finding。旧budget类型、selector、episode及结果未改。真实规模入口接入、实际模型/宿主/多卷空间核验、硬进程监督和normal最优性仍缺；下一项为保留全部UID阶段与数值审计的独立selector执行接口，先以合成例验证，不启动依赖accepted normal的真实episode。
## 2026-09-28 完整UID selector接口与合成验证

新增scale_selector.py和docs/model_spec/rq2_scale_selector_v1.md。独立预算由完整资源合同派生，保留原reference request→L1→全部UID和actual L1→全部UID；复用既有构模、canonical/native及物理/锁定审计。新结果类型与policy隔离旧入口，当前小时逐项绑定而固定policy可跨小时接续。资源派生源码纳入身份，最终状态构造失败保留已返回阶段和known calls，pipeline无完整返回仍记unknown。

最终36项通过（39.52秒）：21 UID合成reference完成23阶段、actual完成22阶段，确实跨越旧20调用cap；两类选择均验证连续两小时。此前旧selector/core及资源相关184项回归通过（69.97秒）。两项独立pre-seal finding已修复并复核闭合，git diff --check通过。未运行H25 selector/episode，也未改变旧预算或结果。

下一实施项为该内核的持久调用记账及资源监督连接，再接episode角色映射/事务；actual:0..3尚须由business arm cursor验证，normal来源/最优仍由上游证明。当前durable tracking/hard resource enforcement/formal/security均false，不能据合成接口通过启动真实完整任务。
## 2026-09-28 selector完整调用持久记账

新增scale_selector_store.py和docs/model_spec/rq2_scale_selector_store_v1.md，复用本地NTFS lease，独立SQLite schema。数值内核前持久化覆盖全部有序阶段的intent并exact回读；返回完整typed结果后归档、摘要核对并exact回读。pending_unknown不能推为零调用，重开仅允许inspection，不重试/resume。intent存在即全额charged calls/solver seconds占用，早停不释放。returned_unverified只代表记录一致，不作数值回放或原生认证；原selector返回flags保持。

最终18项通过（19.02秒），含进程intent后exit17、intent/result INSERT no-op、提交/回读/确认失败、codec漂移、结果请求错配、早停全额charge及复制root拒绝；相关复用lease回归5项通过（20.87秒），此前与selector组合47项通过（51.43秒）。两项pre-seal finding及计费字段缺口已修复，限定独立复核闭合。git diff --check通过；未修改旧core/store/结果。

下一项接进程资源监督：明确wall/commit硬限制、终止后Job静默、再检查落盘状态及归档资源；当前无硬资源执行保证、无真实H25 selector/episode或正式准入。normal最优性和科学/数据门继续开放。
## 2026-09-28 selector固定worker与Job边界验证

新增scale_selector_worker.py和docs/model_spec/rq2_scale_selector_worker_v1.md，固定CLI接收有SHA pin、类型白名单、完整字段及结构/字节上限的canonical请求，创建一次性selector store。实现pin覆盖reference selector等依赖；回执exclusive写入后核验长度、文件身份、exact回读及最终源码/请求。回执失败保留store证据，不提供重执行或恢复授权。

17项worker测试通过（16.40秒、exit0），包括reference/actual真实tiny Windows Job及回执no-op/短写/错误字节/读取失败；进程期限、reserve停止及后代静默4项回归通过（2.07秒）。两项独立pre-seal finding已修复并限定复核闭合，git diff --check通过。Job测试只证明合成小例的执行边界，不证明H25、完整资源或正式环境；输入重建不认证normal/前驱来源。

下一项为复用现有监督工具的持久父控制器：释放前启动意图与PID/creation-time登记，停止后整Job静默，随后验证回执及store；再接episode四臂角色和跨小时事务。尚未完成父控制器、真实规模全episode、normal最优性或科学/数据验收，formal门保持。旧冻结协议、结果及所有无关未提交文件保留。
## 2026-09-28 selector持久父控制器

新增scale_selector_controller.py、对应测试及docs/model_spec/rq2_scale_selector_controller_v1.md。复用NTFS lease和既有Windows Job owner，持久请求/intent后创建suspended child，PID/creation-time登记和全链检查完成才release；wait确认整Job静默后读取回执及store，核完整request、result identity/status及inspection。新root一次性，失败保留记录，不重执行。资源声明先绑定现有父目录，实际Job再绑定新建archive/scratch。

controller与worker组合23项通过（28.55秒）；独立pre-seal的早期lease异常覆盖、terminal后的检查及receipt字段inventory三项已修复，controller最终11项通过（25.10秒、exit0），限定复核闭合。git diff --check通过。状态仍returned_unverified，不是数值接受或完整资源认证；锁释放/I/O异常保留不确定性。

下一项为新ScaleSelectionResult落盘记录的独立数值回放，再接四臂/跨小时事务。旧selector_replay、episode_coordinator、hourly_transaction均绑定旧结果类型/预算，不能直接放宽旧门。父控制器整体wall/内存/目录大小验收、真实normal最优性、完整episode和科学/数据门仍开放；未启动H25或正式实验，旧冻结协议及结果未改。
## 2026-09-28 完整UID归档数值回放

新增scale_selector_replay.py、对应测试和docs/model_spec/rq2_scale_selector_replay_v1.md。在外部record SHA、实现pin及完整request下，以既有纯native replay核和固定构模函数复核每个selected阶段的结构、版本/options、赋值、界、残差、目标锁与物理witness；完整stage与最终state/result逐字节重建相等。未调用solver或放宽旧public预算类型门。unresolved只报告未重放，不生成后继；public仅返回诊断，不授予resume/native真实性/formal权限。

12项针对性测试通过（23.62秒），另21 UID/23阶段真实store回放1项通过（18.74秒）；旧selector/native replay相关158项回归通过（98.92秒、exit0）。限定独立pre-seal无待修实质finding，git diff --check通过。篡改赋值/界、partial、阶段次序/目标锁/截断前缀，即使重算摘要也不能伪造selected。

下一项为将经核验的落盘结果接入新四臂事务适配，保留旧episode exact-type门；还需跨小时链、整体资源验收和真实normal最优性。归档相对输入一致不等于真实观测、数据库来源或工程认证；科学/数据和正式运行门保持，旧协议与结果未改。
## 2026-09-28 四臂回放结果的分阶段事务

新增scale_hourly_transaction.py、测试与docs/model_spec/rq2_scale_hourly_transaction_v1.md。完整reference回放形成精确共同请求；固定NETWORK/CFE/JOINT/B6→actual:0..3，复用capacity policy产生业务candidate及实际功率请求，actual归档回放接受后才成对返回业务/电网后继。拒绝和unresolved保留旧已提交状态并halt；CFE服务适用性与物理检查分开。跨小时绑定common前驱、source audit、mapping、业务policy及actual policy。

初轮6项25.28秒通过，两小时债务累积/恢复2项18.45秒通过；与旧事务/映射组合69项75.80秒通过。独立pre-seal发现业务policy未显式固定，已补business_policy_identity和origin_identity及替换反例；修复后最终9项44.91秒通过（exit0），限定复核闭合，git diff --check通过。两个小时验证债务由1/3到2/3或在高于baseline的恢复功率下下降，原状态保持不变。

下一项为完整episode owner串接这些纯事务与受控selector执行，检查共同曝光下四个不同arm、唯一消费及全量预算，持久提交跨小时cursor。当前只有纯内存分阶段接口，未完成磁盘原子episode、整体资源或真实normal最优性；normal来源、右删失及科学/数据门仍开放。未运行H25或正式实验，旧冻结接口/协议/结果未改。
## 2026-09-28 受控四臂episode端到端开发链

新增scale_episode.py、测试及docs/model_spec/rq2_scale_episode_v1.md。新NTFS独占owner固定连续窗口、规范四臂、同源physical origin/业务机制/actual policy与资源声明，按完整reference+四actual预留calls/solver seconds。每小时先持久intent，再通过现有父控制器逐Job执行，静默后收集归档并回放；全部臂结果准备完成才写hour result并发布内存cursor。失败poison、无重试/恢复入口；halted臂跳过执行但不释放预留。

hour result持久保存五phase evidence及消费文件pin，task/archive双lease覆盖读取、pin和crosslink；实现闭包固定worker/process/resources/lease/native replay依赖；环境只保存private copy摘要，close与advance共用guard。独立pre-seal的证据关联、读取窗口、依赖闭包与环境值问题均已修复，限定复核闭合。

最终15项通过（152.28秒、exit0），含第一小时五Job、第二小时四Job（已halted CFE跳过），累计仍预留22calls/22solver seconds，JOINT债务1/3到2/3；late failure不发布小时，消费归档改动、读取至pin之间替换、传递依赖漂移和环境变化均拒绝。git diff --check通过；旧reference_selector/actual_dispatch_selector/continuous_grid_candidate完整SHA仍匹配既有记录。测试仅pytest临时目录，无H25或正式运行。

下一必要项为已落盘整episode的独立离线核验，覆盖完整输入/phase证据/跨小时cursor和未知中断，不授予resume；另有整任务wall/内存/磁盘资源验收、真实normal最优性及科学/数据/right-censoring门。合成端到端链已接通，正式就绪仍未证明，旧协议与结果保留。
## 2026-09-28 完整episode离线核验

新增scale_episode_replay.py、测试及docs/model_spec/rq2_scale_episode_replay_v1.md。外部typed输入窗口及header/有序intent/result SHA、audit实现pin共同约束只读核验；固定五phase目录，task/archive双lease核文件与controller/receipt/store交叉链，独立重算worker命令、环境/host/process身份，检查启动和正常退出记录。纯回放重建reference共同请求、四臂与跨小时状态，完整hour body须一致；不反序列化可执行cursor，不启动Job或solver。

完成小时拒绝额外/跳过却存在的task目录；末尾pending intent保留unknown并全额charge，不打开其子DB。unresolved阶段数值细节未重放，单列报告；观察窗口消费完不等于完整履约或恢复完成。

9项通过（117.43秒），含连续两小时核验及重hash篡改反例。独立pre-seal的process身份/记录一致性、子task inventory问题修复后，最终相关6项通过（40.67秒、exit0），正常前缀与5类联动重hash进程记录均覆盖；git diff --check通过。旧episode执行器与冻结成果未改，所有测试仅合成/tmp，无H25或正式运行。

下一项集中核对完整episode的整任务资源验收缺口，并接入已有资源合同；真实normal最优性、实际数据/机制参数、末端右删失和正式科学验收继续开放。现有小例执行与离线核验链已具开发证据，正式就绪仍未证明。
## 2026-09-28 Episode资源声明与采样检查收尾

现有TaskEnvelope已接入scale_episode_resources.py、episode owner和离线核验：完整窗口五phase预留、父header/小时intent/result空间、累计wall/working set/archive/scratch/tree及host headroom检查。owner和离线核验拒绝elapsed、lifetime peak、保留字节与条目倒退；host可用commit允许波动。开发规格见docs/model_spec/rq2_scale_episode_resources_v1.md。

验证：episode执行与离线核验组合29项通过（285.39秒）；单调性修复后资源边界、传递依赖漂移、在线/离线连续两小时及完整前缀共32项通过、21项未选择（118.67秒、exit0）。命令为compute Python -B -m pytest -q -p no:cacheprovider，最终选择三个test_rq2_scale_episode*_v1.py中的resource/dependency_drift/two_hour/complete_prefix。独立pre-seal代码复核已确认五项单调性修复；未产生official verdict。git diff --check通过。

本项只完成声明与采样拒绝条件，不完成整任务资源认证：父进程硬wall/commit、最终写入关闭及离线audit成本、完整任务清单与SerialResourceBudget绑定仍需证明；记录未保存历史disk free/volume requirements。hard_parent_wall_limit/hard_parent_commit_limit/hard_disk_quota/whole_task_resources_verified均为false。

当前主线状态：多日状态、恢复债务、四臂策略及拒绝动作已有开发产物，合成执行与离线回放链已具验证。下一项先核对完整任务资源验收矩阵，复用现有监督组件并明确剩余解除条件；真实normal最优性、实际观测与机制参数登记、右删失和科学验收保持独立阻塞。不得用新增局部测试替代这些条件。未启动正式实验，旧冻结协议、结果及无关未提交文件保留。

## 2026-09-28 完整资源连接核对与嵌套监督验证

已在docs/model_spec/rq2_execution_resource_contract_v1.md补完整执行验收矩阵。确认selector预算工厂能重算合同，但episode当前仅比较传入摘要相同，尚缺原始normal/episode/envelope/serial声明与实际窗口重新绑定；此项先于外层执行入口。normal_task_process的3600秒开发上限不能直接承载H25完整预留，父episode加inner Job及独立offline audit成本也不能遗漏。wall为轮询终止，不是OS硬wall quota。

新增test_nested_task_job_membership_and_outer_quiescence的正常/停止两个短案例：使用既有normal_task_child嵌套，不增加监督框架；IsProcessInJob证实inner属于outer，持有同一HANDLE核验外层停止后inner死亡，正常报告和outer/inner peak关系均检查。首轮测试专用256 MiB父导入MemoryError已定位，测试改用768 MiB process/1 GiB Job及单线程后通过；这些数值不是正式预算建议。运行代码、旧cap、冻结配置与结果未改。

验证命令：compute Python -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_task_process_v1.py。新增两项5.19秒通过；整个文件36项8.91秒通过、exit0。独立限定pre-seal未见实质finding；无official verdict或资源认证。下一项为原始完整资源声明的episode绑定及离线重算；真实normal最优性、数据/机制身份、删失及正式科学验收仍开放。未启动solver或正式实验，未清理工作区。

## 2026-09-28 原始完整资源声明绑定

scale_episode_resources新增EpisodeResourcePlan；episode owner和离线核验强制携带原始normal/episode/envelope/serial声明，在创建或读取root前重新核算。实际完整小时窗口、source audit的normal身份/split/UID/可见信息、五role预算、总调用与秒数及envelope须匹配；task Job声明覆盖父controller加inner Job，全局commit/disk reserve至少覆盖运行时reserve。header保存完整原始声明，offline从独立typed输入重算并比较，不接受仅一致的摘要。

验证：单小时五Job1项26.93秒通过；plan/resources组合35项8.38秒通过；episode与offline完整回归30项291.96秒通过。独立pre-seal发现全局reserve与局部runtime未关联，已修复并新增两反例；最终plan正反例、完整离线前缀、重hash原始plan header篡改共16项通过、12项未选择（39.30秒、exit0）。命令均为compute Python -B -m pytest -q -p no:cacheprovider，相关文件tests/test_rq2_scale_episode_plan_v1.py、tests/test_rq2_scale_episode_resources_v1.py及tests/test_rq2_scale_episode_replay_v1.py；完整回归使用test_rq2_scale_episode_v1.py与test_rq2_scale_episode_replay_v1.py。

此项证明调用者声明与实际episode内部一致，不证明研究任务全部列齐、完整normal源范围、normal复用或最优性，也不把owned source audit提升为真实观测。独立offline仍需单独资源预算与受监督入口；下一项复用既有Job原语接固定episode/audit worker及封闭transport，覆盖父进程、最终发布/关闭与离线核验成本。3600秒开发cap、真实normal最优性、数据/机制参数及右删失/科学验收仍开放。未启动正式实验，旧冻结协议、结果及无关未提交文件保留。

## 2026-09-28 Episode固定transport与执行/审计worker

新增scale_episode_transport.py、scale_episode_worker.py及对应测试；规格见docs/model_spec/rq2_scale_episode_worker_v1.md。输入固定初态/四臂/窗口/原始资源计划白名单，支持精确Fraction和finite hex float，16MiB/64层/500000节点限制；canonical roundtrip后复验初态和资源绑定，不恢复结果或可执行后继。环境值不写入packet，仅从继承环境及指定目录重建后核外部摘要。

固定CLI分别execute新episode及audit外部header/有序pins；复用既有owner与离线核验。测试中外层Job内完成一小时五phase，再另起audit Job，四条selected数值链回放，归档全部文件hash前后相同；receipt独占fsync/回读，root及外部audit pins显式关联，全部权限标志false。request、环境目录与receipt均在evidence root外，replay要求exact顶层清单。

初轮transport22项6.23秒通过，后补embedded successor/wrong contract及直接/传递源码漂移，29项7.19秒通过；worker初轮6项58.54秒通过。独立pre-seal发现reference origin可嵌入后继carry、输入/环境可混入evidence root，均已修复。最终针对性组合16项通过、38项未选择（82.43秒、exit0），包含outer execute+独立audit、路径隔离、后继拒绝、源码漂移、extra root拒绝、正常prefix与pending_unknown。命令为compute Python -B -m pytest -q -p no:cacheprovider，文件为tests/test_rq2_scale_episode_worker_v1.py、tests/test_rq2_scale_episode_transport_v1.py和tests/test_rq2_scale_episode_replay_v1.py；最终使用-k筛选上述相关项。

receipt的pins只是owner持锁时快照；关闭后仍须独立audit与进程正常退出/Job静默。测试90秒outer不代表600秒episode声明全量可覆盖，更不认证H25资源。下一项为持久外层controller的request/intent/launch/result事务，将outer预算与完整声明绑定并计入最终写入/关闭和audit成本；3600秒开发cap、normal最优性、正式数据/机制及右删失/科学门仍开放。旧冻结协议、结果及无关未提交文件保留，无正式实验或仓库清理。

## 2026-09-28 Episode execute/audit持久外层控制器

新增scale_episode_controller.py、tests/test_rq2_scale_episode_controller_v1.py及docs/model_spec/rq2_scale_episode_controller_v1.md。PipelineBudget把同一TaskEnvelope分解为execute/audit两worker、两次quiet、controller allowance、outer metadata与两个scratch；root创建前核wall/commit/archive/scratch/条目覆盖，不借全局controller_seconds。运行时独立限制controller耗时，phase host未来空间扣除已保留字节；记录采样hard wall/commit/disk=false。

两phase分别保存intent、launch、observation和外部receipt，release前持久化PID/creation-time；只有Job quiet和exact正常观察字段、receipt一致后推进。execute保存的ordered pins进入audit intent，跨phase核episode全部证据文件身份/hash；根锁由lease检查。audit完成后在读取receipt/归档前取得episode lease并保持至final，重算完整audit报告计数，独占写result后再检查。关闭异常仍尝试释放两层lease，失败不自动重试或resume，文件存在不代表调用成功。

验证：首轮1失败/7通过定位Windows锁首字节不可另流读取，改为lease核根锁后真实pipeline1项44.77秒通过。独立预审要求controller独立计时、完整条目预留、exact进程观察及finally清理，修复后19项127.97秒通过。剩余host空间修正后4项49.36秒通过；最终锁窗口修复后真实pipeline与晚期close异常2项通过、18项未选择（87.97秒、exit0），真实测试在每次audit receipt读取时断言episode lease已被持有。命令均为compute Python -B -m pytest -q -p no:cacheprovider tests/test_rq2_scale_episode_controller_v1.py；后两轮分别用-k选择real_persistent/scratch/host_demand与real_persistent/late_evidence。git diff --check通过。

当前获得的是短合成观察窗口的持久执行和独立回放，不是完整服务或资源认证。最外层controller资源仍为采样，正式长预算及3600秒开发cap适用性、真实normal最优性、完整研究清单/数据/机制参数与右删失科学验收保持开放。下一步核对真实规模执行预算与现有开发cap的具体冲突及可复用路径，不再次开发已具证据的两phase事务。未启动正式实验或长solver，旧冻结协议、结果及无关未提交文件保留。

## 2026-09-28 外层声明预算接入与主线状态

declared_task_process.py复用旧Job生命周期，新增绑定原始资源合同SHA及TaskEnvelope的预算；scale_episode_controller支持该预算的execute/audit分配并拒绝错误绑定。旧normal_task_process及3600秒开发cap保持原SHA c7c46c08297c083338cc555a887313a94cb9e767480709caa205011b6e4d080c。校验用1秒投影保留完整内存/host需求，实际child仍使用完整新预算。仅outer接入，inner phase仍是旧短预算；不能据此宣称真实长任务或整体资源已认证。

验证命令均为D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider。tests/test_rq2_declared_task_process_v1.py与tests/test_rq2_normal_task_process_v1.py共50项通过（9.46秒）；tests/test_rq2_scale_episode_controller_v1.py -k 'real_persistent or declared_outer'共4项通过、19项未选择（97.81秒）。超过3600秒行为通过时间注入测试，端到端仍为短合成案例。git diff --check通过；未启动长求解或正式实验。

当前主线：连续多日、恢复债务、四臂、拒绝动作与诊断包已有开发产物，短合成持久执行/独立回放已接通。真实H25 normal仍只有TIME_LIMIT可行解，gap约0.125%，最优性未过；完整任务规模与内层预算、实际观测/机制参数登记、右删失和正式科学验收继续开放。下一项应直接核对这些未闭合项的可执行解除条件，优先形成normal求解及参数登记的具体任务，避免继续无边界扩展执行设施。保留旧冻结协议、结果及所有无关未提交文件。

## 2026-09-28 参数登记入口与normal前置核对

已更新docs/model_spec/rq2_continuous_multiday_parameter_evidence_v1.md：逐项关联20个未识别输入、6个未注册选择与当前代码/待登记内容，纠正早期“响应/ramp/逐笔deadline尚未实现”的范围过时说明。现有机制实现可复用，实证null和正式登记缺口保持；Google绝对功率、逐job checkpoint/抢占证据不能由聚合机制补出。代码字段之外的minimum-event-power、ramp、精度及容量声明亦明确列为待登记项。

零solver机械核对通过：20行与交付unidentified顺序完全一致、6项协议集合一致、实证仍全null/协议仍unregistered、所列代码symbol存在。input_status SHA256=263643c83cf4ec60fd25fb176f50c3aae2bd7f158f8bb550fe241f3a18d88302。旧H25 replay SHA256=b1a67d96fcda78434472440b9b31ebb9028f2f14a1bf9ec5fd00b3f8cb9df8d5，accepted_record_reproduced=false、optimality_certificate=null。首轮检查因PowerShell管道中文编码导致标题匹配失败，改用ASCII锚点后通过；未改变被核工件。

明确下一项normal前置：gurobi_ordered数值内核仍复用NormalExecutionBudget的30秒单solve/60秒总normal上限，新outer接口未覆盖它。应准备显式数值预算后继及身份/回放绑定，保留旧声明、验收精度及证据；现有15秒结果不能保证长预算收敛。科学候选还需将参数取值、单位、机制身份、窗口、事件及删失分母集中登记后审阅。此次仅更新证据索引与任务定位，未注册数值、改变科学门、运行solver或清理仓库。

## 2026-09-28 显式normal数值预算及独立回放

新增scale_normal_budget/native/kernel/replay与单线程declared Gurobi adapter，规格见docs/model_spec/rq2_scale_normal_v1.md。完整原始resource plan重新核算，绑定实际normal输入摘要、完整小时和机组清单及carry split声明；spec时限必须等于NormalWork预留。保留gap1e-8、三项1e-9容差、seed0和版本，native _solve AST与旧ordered相同。wall/working-set/payload为显式数值子分配，source/归档/离线回放整体成本仍待outer绑定。

新记录具有独立type/schema，零solver回放重算赋值、界/optimal flag、witness及调用/资源记录一致性，拒绝旧类型和重hash篡改，不返回可执行carry。新全组最终43项37.00秒通过，旧normal/native replay/resource contract相关139项57.35秒通过；600秒预算仅假solver传递，真实Gurobi仅一秒上限两小时单机小例。六个旧core/adapter/config/replay文件与H25保留索引bytes/SHA一致，git diff --check通过。

已补数值内核的长声明路径，尚未接入source-bound持久worker/controller。下一项复用已有source核验与进程监督连接该新type及回放，完整分配准备/归档/audit成本；不重建数值算法或监督框架。真实H25最优性、episode内层预算、科学参数及删失登记仍开放。没有长求解、正式运行、旧冻结修改或仓库清理。

normal数值回放限定预审补充：继承raw/witness错误从按值过滤改为逐次精确消费，防止重复错误自洽重hash后仍称一致。首轮补充用例13通过/1失败，修正raw反例使其先具有完整可回放的无效赋值后，最终受影响14项通过、31项未选择（23.43秒）。原43项是该修复前全组，不混为最终45项全组。源码、测试与准确时序见rq2_scale_normal_v1.md。

## 2026-09-28 Scale normal来源连接与固定worker

新增scale_normal_source/transport/worker，规格见docs/model_spec/rq2_scale_normal_source_worker_v1.md。复用已有prepare，执行前后重建RTS/pair并核外部assembly/binding/实现pin和完整资源计划；caller检查在kernel捕获区之外，无完整返回保留unknown调用。来源回放从当前prepare的inputs重算，并末尾再prepare。transport固定类/字段/大小，worker先intent再执行，独占记录后receipt；audit持lease、核外部intent/record/执行环境pin，并在运行时阻断四个执行入口，finally恢复。

source首轮21项83.67秒通过；修复伪错误降级后组合19项75.88秒通过；旧prepare/pair/declared相关82项94.26秒通过。最终audit guard补充后执行—审计正例及四入口阻断/恢复5项48.88秒通过。准确筛选与分批时序见规格，worker测试为合成来源下直接调用入口，不是父控制器子进程验收。

真实本地H25只读prepare、新预算绑定和transport roundtrip亦通过：25小时、158UID、原输入d9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c、0 solver calls、34.9373秒。诊断packet仅内存构造，资源清单只作一致性例，未发布运行配置或取得新normal结果。

下一项为持久父控制器连接：复用已具证据的Job/intent/launch/receipt原语，将source准备、normal、归档、独立audit与关闭成本绑定同一完整声明；固定worker自身不证明这些条件。真实normal最优性、episode内层预算、完整研究清单及机制/删失科学登记仍开放。未启动长求解或正式实验，旧冻结协议/结果及无关未提交文件保留。

## 2026-09-28 Normal父控制器审计语义修复（端到端验收未完成）

scale_normal_controller.py已形成草案，复用现有进程监督和execute/audit事务。当前完成的限定修复：不完整normal返回或调用计数未知时输出normal_invocation_unknown_not_replayed，保留solver_calls与call_count_complete原值及完整reserved_solver_seconds；只有完整数值记录可进入replayed分类。父端独立调用source.audit_source，逐字节比较完整审计报告，防止嵌套native_replay被自洽改写；父端回放封住四个求解/执行入口并在finally恢复，耗时计入controller allowance。request以packet SHA进入controller identity，修正identity encoder不支持bytes的问题。

验证：D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_scale_normal_controller_v1.py，17 passed in 31.10s。覆盖missing-return、TIME_LIMIT类未接受状态分类、完整预算保留、真实一秒上限合成normal的零solver父端回放、嵌套报告篡改、四入口阻断及恢复、预算不足拒绝和identity绑定。测试没有启动父控制器子进程，不代表完整pipeline或真实规模验收。

下一项是该既有控制器的短合成子进程execute/audit联通与失败窗口测试；完成前不进入依赖它的真实长任务。真实H25最优性、episode内层预算、完整任务清单、机制参数与删失登记仍开放。此次仅修改草案控制器、其测试及进度说明；旧冻结协议、结果、公开观测及无关未提交文件保持。

## 2026-09-28 Normal父控制器短流程验收

限定pre-seal已闭合：真实Job execute/audit合成流程及5个audit失败窗口6项通过（106.30秒）；当前controller其余19项与新旧process相关50项共69项通过（47.53秒，6项未选择）。最终字节下终态前完成全链核验，跨phase保存目录/锁及文件身份，audit读取与终态写入实测持锁。规格、准确命令与证据边界见docs/model_spec/rq2_scale_normal_controller_v1.md。来源使用显式synthetic替身，native上限一秒，不改变真实H25 TIME_LIMIT或正式数据/资源门。

下一项转向实际研究任务清单及逐阶段预算核算，先判断所选预算是否触发episode内层3600秒限制，再确定必要接口变更；同时准备normal验证和机制参数/删失登记候选。完整科学协议及正式运行许可仍开放，不宣称已能开始正式实验。

## 2026-09-28 实际清单与3600秒限制核对

新增只读核算experiments/audit_rq2_current_workload_inventory_v1.py及results/tables/rq2_current_workload_inventory_v1_non_authoritative/audit.json（SHA256 648ed752cb47f1628a2895f8d751d73a6d62719064775dafd22f2bc2fa4101fc），规格见docs/model_spec/rq2_current_workload_inventory_v1.md。四个来源/配置pin通过，实际158 UID、25小时，单episode加normal共19901次完整路径预留；20项实证null及6项未注册选择保持。

3600秒限制作用于每个selector子进程，而非整窗episode。15秒/级的reference与actual solver预留为2400/2385秒；22秒/级剩余80/102秒非solver空间；23秒/级则solver预留本身超限。未测逐级非solver成本，不能把算术余量当资源通过，也不应在正式预算尚未选定时断言必须扩接口。现有normal与episode短流程继续复用。

旧36+10=46-cell数目重算一致，但不是完整episode数。当前缺连续窗口/coupling、training容量评估清单、holdout容量策略绑定、normal复用/信息声明、pilot重试清单、完整phase和回放资源分配。全实验调用和wall保持null；不以46乘H25假装完整预算。下一项为完整科学候选的参数/窗口/评分登记内容，再据其展开逐项执行清单；normal预算候选可独立准备。

运行compute Python -B脚本及runpy机械断言，生成后两次重算bytes一致，zero solver；首次runpy暴露相对__file__路径问题，改为resolve后通过。git diff --check通过。此核对未注册科学值、修改旧阈值、执行长求解或正式实验。

## 2026-09-28 连续科学参数/窗口/评分候选

新增configs/rq2_continuous_science_candidate_v1.DRAFT.yaml及docs/model_spec/rq2_continuous_science_candidate_v1.md，明确complete_preregistration=false、全部注册/执行门false。候选以自包含sealed v5作逐字段比较，提出168h观察/24h stride、birth+24机制期限、单期预算显式7倍、新46-cell身份、具名功率/CFE机制和次级有限窗口F/S/U评分；没有把20项实证null改成机制观测，也未批准这些科学选择。

独立R4设计预审推动修正：完整未来/period合同未定义，complete target保持unbound、prefix LB仅条件命题；仅观察168h，不虚构169-192h动作预算；deadline越界未偿为U，due-hour先恢复后exact检查；明确N/A、同维已证F优先、seed非等权、独立窗口初态、非rolling周预算可集中使用及新增恢复cap/损失假设。完整protocol/schema测试、training证书与holdout绑定及计算方案仍开放，不称完整pre-seal通过。

机械证据results/tables/rq2_continuous_science_candidate_v1_non_authoritative/structure_audit.json SHA256=6ba0fc07cf551a9fc1d18952849b46e8e8ffb051dca8accb8da41e9b5c4ec884，绑定candidate SHA256=2a0e7686b9f92355dc421531c2150ecab354a8106abea54c2d2c5d25259c9051。3pins、46个唯一物化新cell及实际窗口计数通过；gzip exact重算6个raw>1小时涉及holdout三个块、10/28窗口。沿用当前source_pair整窗预验证时该10/28为U质量下界，不是服务失败率。birth1/due25的已有cohort小例确认hour24删失、hour25偿还成功；零solver。

计算关键缺口：该候选全部配对为training14644/holdout14336。若每pair-cell直接跑一次现有168h四臂episode，对应90082390272/88187731968次selector调用；这仅是特定直接展开条件算术，不是全部算法下界。不能只扩超时或擅自缩支持；下一步须审计哪些计算可在相同输入/信息/策略身份下严格复用，并形成可行计算路线与完整training/holdout证书合同，再完善科学协议。旧冻结字节和结果保留，未启动正式或长solver实验。

## 2026-09-28 计算复用及容量证书绑定边界

新增docs/model_spec/rq2_computation_reuse_and_capacity_binding_v1.md及tests/test_rq2_computation_reuse_boundaries_v1.py；现有实现未改。10项通过（14.34秒）：同reference归档改变CFE/limits/due/available后publication身份不同、重建不调用solver；物理input相同但task/resource/caps变化时原record重挂被拒绝；actual角色身份、容量改变动作及同功率不同前序状态均有直接反例。核查与旧源码一致：policy只归零source_hour，source/预算/角色身份不能因物理输入相同而绕过。

在上一候选全部pair-cell路径的条件算术中，即使每pair reference跨46cell只做一次，也仅从178270122240降至143215914240次selector调用（减少900/4577约19.7%）；没有证明该跨task复用已实现或计算路线可运行。actual业务历史通过动作影响功率，完整网侧输入相同仍需分别核来源/cursor和任务证据归属。

training→holdout当前不是漏填一个certificate SHA：capacity_policy配置明确要求training_capacity_certificate=None。后继必须绑定目标/arm/cell/完整或前缀语义、training支持及证书、注册容量选择规则、固定策略、独立holdout来源/初态和B6规划/共享执行区别。完整目标未定义前不开发默认接受机制容量的适配器。现有normal最优性与全支持可行计算路线仍开放，不将窄测试写成formal-ready。

命令为compute Python -B -m pytest -q -p no:cacheprovider tests/test_rq2_computation_reuse_boundaries_v1.py；git diff --check通过。未启动长solver、修改冻结协议/产物或清理仓库。
