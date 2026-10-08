# 连续组合策略拒绝覆盖核对

日期：2026-09-16。性质：DRAFT开发证据索引与测试补充；不注册新策略或改变门禁。

## 当前覆盖定位（2026-09-28）

下文按日期保留开发历史，其中“下一项”不能直接当作当前缺项。B6规划拒绝后的共享后继、
显式部分响应、固定容量策略、网侧selector、业务/网络双提交及episode归档回放均已有开发产物。
规模化小时事务见`rq2_scale_hourly_transaction_v1.md`；已有模块不重复开发。

本次新增`tests/test_rq2_scale_rejection_action_semantics_v1.py`，补充两类跨层动作证据：

- JOINT/B6完整请求为grid=1/3、CFE=1/4、baseline=5/9；机制容量2/5下实际削减2/5、
  实际功率7 MW、CFE短缺11/60。网侧接受才提交这笔延期债务及CFE短缺记录；网侧未决时保留
  business_candidate，已提交两侧状态保持原值。CFE未满足量不是延期工作或永久业务损失。
- 到期小时的候选先部分恢复、再记录剩余债务为deadline miss。网侧接受才推进债务时钟；网侧
  未决时，恢复、miss和该小时都只存在于候选，原账本仍停在到期前。未观测到期不能记作已履约。

timeout反例使用合成native记录，明确验证首级通过、末级赋值/物理见证有效、终止为maxTimeLimit，
且末级唯一错误为缺少所需optimal赋值；不是数学不可行或真实事故观测。真实微型求解每级上限一秒。
这些测试约束现有事务语义，不新增F/S/U汇总器、补救策略、经验风险分母或正式认证。

最终验证：compute Python `-B -m pytest -q -p no:cacheprovider
tests/test_rq2_scale_rejection_action_semantics_v1.py tests/test_rq2_scale_hourly_transaction_v1.py`，
15项通过（78.92秒，exit 0）。独立只读限定预审的timeout原因与candidate/committed区分finding均闭合。
生产实现、配置与结果工件未改；仍缺真实normal最优性、可行全支持计算路线和完整容量/holdout证书合同。

## 已有开发与证据边界

完整读取AGENTS.md、agent.md，核对执行计划、blocker末段、连续多日开发记录、参数证据表、当前代码与配置。
现有链为boundary → multiday → debt_cohorts → four_arm_replay → causal_policy → actual_actions → recovery_controller，
并已有prefix与composite两套落盘诊断包。最新组合交付要求的下一项正是拒绝类型与实际动作语义梳理。

公开交付中的Google归一化PDU功率属于观测源值，CPU端点/小时均值/capacity积分属于派生值；
RTS-GMLC事故/CFE块属于derived benchmark。744小时同钟配对不识别真实可恢复比例、deadline或恢复headroom。
12包交付的20项未识别输入仍null、6项协议选择仍未注册。当前controller输入、期限、零历史、调用与恢复参数
均为mechanism_assumption；诊断包不提供经验风险分母或真实失败后轨迹。

## 阶段覆盖矩阵

阶段由`causal_policy._evaluate_current_hour`和`recovery_controller._recover`直接设置。
阶段是执行位置，不是互斥科学失效类别；同一阶段可包含输入、数值表示或约束问题，不能只按阶段推断物理原因。

| 位置/情形 | 当前动作与状态 | 现有验证入口 | 仍需补齐的语义 |
|---|---|---|---|
| primary `input_validation`：gap/split/provenance错误 | 保留最后共享/规划状态；停止，无补救 | controller `test_input_or_planning_rejection_does_not_activate_recovery`；causal `test_invalid_observation_is_input_rejection_not_service_failure` | 有效连续来源证据；不能虚构缺口小时或把输入故障记作服务失败 |
| primary `policy_decision`：完整调用超过baseline、B6 effective分解不一致 | 停在上个验证小时，无planned/accepted step，无补救 | 本次新增`test_rq2_continuous_rejection_coverage_v1.py`的5个参数化例 | 超baseline须先定义实际服务/失效合同；数值分解异常须独立诊断，不能静默裁剪或改阈值 |
| B6 `separate_planning`拒绝 | 不提交分离候选；不进入旧actual-action/controller后继 | controller `test_input_or_planning_rejection_does_not_activate_recovery` | 共享实际动作选择、原规划拒绝归档与新的完整策略身份；现有支持不足以判断是否存在合法共享动作 |
| primary `physical_execution`或`shared_execution`拒绝 | 同一原观测触发共享机制；通过原包络才提交 | controller `test_48h_composite_has_unique_exposure_and_preserves_original_rejection`、`test_full_call_failure_cannot_be_repaired_or_counted_as_validated` | 已覆盖指定固定规则，不覆盖所有实际运行处置；触发并不保证可继续 |
| recovery `input_validation`失败 | 不选择动作；保留上一实际状态，后缀不消费 | controller `test_invalid_suffix_identity_stops_before_decision`；组合包source-gap场景 | 仍需合法来源，不是第99小时已经服务 |
| recovery `recovery_decision`失败 | 保存错误，无新ActualActionRecord，状态不推进 | controller `test_recovery_decision_failure_preserves_error_and_last_actual_state` | 表示/决策失败的独立诊断；当前不搜索替代动作 |
| recovery `actual_validation`失败 | 保存已尝试动作与unassessed；不提交 | 组合包hard-call场景；actual-action非法功率/分配测试 | 不能裁剪硬网络/CFE请求或引入未定义救援资源使轨迹继续 |
| 显式actual action缺失（None） | `missing_actual_action`，不推进到期时钟 | actual-action `test_missing_action_leaves_due_hour_unobserved_and_blocks_suffix` | 需明确动作；None不同于合法零恢复 |
| 合法零/迟到恢复，unknown deadline，观察结束 | 合法小时可推进；永久保留miss，unknown与right-censored分开 | controller known/late/limit测试；composite evidence/censoring测试 | 不是拒绝阶段；不能据成功提交推断按时完成，不能据无未来观测清除债务 |
| 非法typed对象或halt后再次advance | 接口抛错，不保证生成科学记录 | controller单观测及停止断言 | 不把任意Python异常当作已观察服务失败 |

测试简称分别对应`tests/test_rq2_continuous_{recovery_controller,causal_policy,actual_action_contract,composite_diagnostics}_v1.py`。
这是一张阶段与代表情形矩阵，不宣称穷举所有数值/包络失败组合。

## 本次补充与下一开发边界

新增测试直接调用现有组合接口：先接受一小时，再在第二小时送入四臂各自超baseline请求或B6容差分解异常。
断言原观测保留、shared/planning状态和policy_id不变、submitted=2但validated=1、禁止建立实际后继、禁止消费第三小时。
旧测试已覆盖input/planning拒绝及recovery决策失败；这里补足primary决策失败在组合层的直接验证。
新增文件复用既有合成fixture，没有修改已绑定的旧测试、实现、配置、manifest或结果包。

后续应先设计B6 separate-planning拒绝后的独立机制合同，再考虑实现：

1. 从最后已提交共享物理/cohort状态和同一拒绝观测出发；原分离规划及拒绝永久归档。
2. 明确是否永久切换共享规则，并赋予独立完整policy身份；结果不能写回原B6策略。
3. 继续满足完整请求、事件/预算/债务及恢复双侧头寸；同小时拒绝/补救只计一个输入。
4. 用合法后继与仍无法履约两类手算例、未来后缀扰动和分块一致性验证；无法证明不变量时升级。

以上是待设计项，不是对已有触发规则的变更或授权凭证。扩展属于R3，需按agent.md第7节开发与独立审查。
真实deadline/恢复参数、四臂非零carry-in、异质deadline、多period预算、损失/抢占、split/coupling和正式planner仍开放。
底层multiday已有完整aggregate非零carry-in小例，不能把此能力说成四臂/cohort初始化已经实现。

### 后续开发更新（2026-09-16）

上述矩阵描述旧controller的覆盖范围，旧实现与诊断保持不变。新增独立B6策略草案及实现
`b6_planning_recovery.py`，在separate_planning/shared_execution拒绝后从同小时最后共享状态
永久切换固定共享规则；原B6拒绝与规划归档，新policy_id不覆盖D_B。
18项针对性测试通过，独立pre-seal审查完成且限定范围无阻塞实现finding；具体合同及验证见
`docs/model_spec/rq2_continuous_b6_planning_recovery_v1.md`。
此项只补齐一种机制后继，输入/决策故障和完整请求仍不满足包络的小时继续未评价。

### 其余拒绝的实际处置合同缺口

以下为下一轮设计输入，不是已注册策略；错误字符串只是定位入口，不能直接充当科学失效分类。

| 尚未闭合的情形 | 必须补的动作证据或语义 | 当前可报告范围 |
|---|---|---|
| source gap、split/provenance不一致 | 有效连续观测及合法同split身份；若缺失期间有动作，须有对应来源及状态递推证据 | 输入拒绝、最后验证状态；不能生成缺口期间风险分母 |
| B6 effective分解不一致、保守恢复表示失败、allocation超过已有债务 | 数值表示与分配原因审计；修复须保持原阈值和守恒并使用新版本 | 决策/表示错误；不能当作物理服务失败或用裁剪掩盖 |
| 完整调用超过baseline | 明确需求、实际功率、已实现削减和未满足调用的分账；硬网络调用必须继续满足，无法满足时需独立安全处置合同 | 当前策略未生成合法动作；不能自动设功率为0并视作履约 |
| 完整调用超过duration/rest/event/energy/debt或call限额 | 区分合同柔性、非合同业务损失和额外资源；明确实际服务及网络平衡、损失是否永久、后续恢复义务 | 固定策略动作被拒绝；不能推断所有策略数学不可行 |
| 恢复headroom不足或deadline到期 | 合法零恢复可推进；保留到期短缺，继续跟踪债务；若允许任务失效/丢弃，须定义损失记账与债务结转 | 逾期与未偿债务；目前不允许到期自动清债 |
| 显式实际动作缺失 | 提供具名因果规则或有来源的实际动作，包含功率、恢复和cohort分配 | unassessed；缺失不同于合法零动作 |

业务丢失不是恢复能量，不能把“到期未完成”直接写成debt归零。若未来引入永久损失，应先定义逐笔
`历史延期工作 = 已恢复工作 + 剩余债务 + 明确永久损失`及与实际功率的换算，再建立新的验证器。
现有无损失模型保持原守恒；公开CPU/PDU配对没有观测到这些处置或损失，不能标作经验运行策略。

### 显式部分响应补缺（2026-09-16）

新增`rq2_continuous_partial_response_v1.md`及`partial_response.py`，补齐完整请求超baseline或包络失败后的
显式请求/响应分账。原请求与拒绝不变，只有执行响应量创建债务；未满足CFE调用不等于lost work。
grid短缺只保留通过业务校验的candidate并停止，不能继续物理状态；grid足额而CFE不足可提交带CFE短缺的机制状态。
来源/表示错误、缺失或非法动作仍停止。37项新增测试、7文件186项相关回归通过；独立pre-seal复核已确认数值finding闭合，fresh相关186项通过。
核对formulation §10后，永久业务损失引擎不作为当前主线补救：核心实验默认ell_drop=0，敏感性须另行注册。
该接口不自动选择动作；完整固定策略、训练容量绑定及完整时序包络仍待补齐。

### 后续网侧执行拒绝语义（2026-09-19）

固定业务功率网侧已有当前小时审计、短求解及数值dispatch选择，见`rq2_actual_dispatch_selector_v1.md`。
actual selector保持功率不变，来源/身份/预算错误在求解前拒绝；timeout、缺界、物理或目标锁定残差越门时
保存证据但不产生已选择后继。全部级通过仅提供网侧candidate，不自行提交业务cursor或偿还债务。
46项针对性、220项相关回归及独立46项验证通过，限定pre-seal无开放实质finding。
因此“业务动作合法而网络未完成”的停止语义已有网侧执行基础；业务/网络双提交与四臂绑定仍需连接，
停止后的后缀不能作为已观察服务失败或成功分母。上述动作均为机制开发，未增加真实运行处置观测。

### 共同请求来源与分辨率拒绝（2026-09-19）

`common_request_adapter.py`已补G/U精确Fraction适配、正小请求活动阈值拒绝及分离/合计调用活动不一致拒绝。
通过normal/prepared/current审计绑定严格检查业务split、outage seed和绝对小时，normalization身份及baseline也需一致。
这些拒绝不生成mapped hour，不将缺失或被消去的正请求改成0；reference未完成时raw请求仍为空。
38项targeted/223项相关回归通过，独立38项验证及来源finding闭合，见`rq2_common_request_adapter_v1.md`。
业务prefix可以精确重放1/3，但与reference来源的联合提交仍待小时事务完成，不据此增加经验风险分母。

## 本轮验证

解释器：`D:/Miniconda3/envs/compute/python.exe -B`。测试关闭pytest cache，临时产物只在pytest/system tmp。
新增测试针对性结果：`5 passed in 0.17s`。相关四文件回归：`68 passed in 13.08s`，实际命令为：

```text
python -B -m pytest -q -p no:cacheprovider tests/test_rq2_continuous_rejection_coverage_v1.py tests/test_rq2_continuous_recovery_controller_v1.py tests/test_rq2_continuous_actual_action_contract_v1.py tests/test_rq2_continuous_composite_diagnostics_v1.py
```

独立只读R0核验执行以下既有入口，三条均exit 0；prefix/composite完整重放匹配：

```text
python -B experiments/prepare_rq2_public_data_delivery_v1.py --verify-existing
python -B experiments/export_rq2_continuous_prefix_diagnostics_v1.py --verify-existing
python -B experiments/export_rq2_continuous_composite_diagnostics_v1.py --verify-existing
```

| 现有交付 | 本轮核验 | summary SHA256 |
|---|---|---|
| public data | 12包、261字段、744小时/31 blocks；raw>1仍6条，model_ready=false | `53b898e30d807b3b532cfaed78de20fdb0653fa53817f65fcc5a6a5d78483586` |
| prefix | 24组合、1038记录 | `ec92fd16ad16ab0a6912ea43fe71a937ad0d123e94deed3dc3d9b43d10a9df2a` |
| composite | 32组合、1330记录 | `b0fbb242d226d00941f1e07fe173c95e5736c444007578261134805eb947f4bd` |

R0核验不是独立R3/R4 official审查，未生成receipt或改变门禁。
未运行solver、下载、付费查询、formal、seal或清理仓库；未重跑旧v5的Windows symlink验收，保留其历史未验证状态。


## 2026-09-20 小时事务验证与下一步

共同小时与业务/网络双状态事务已完成DRAFT开发，见`docs/model_spec/rq2_hourly_transaction_v1.md`。
共同请求未完成不填0；业务拒绝不调用网侧求解；网络输入拒绝或求解未完成保留候选证据，两侧已提交状态均不推进。
CFE-only物理检查与grid服务义务分别记账。独立pre-seal发现的共同发布前实现身份重验缺口已修复并复核闭合。
修复后22项针对性通过（27.43s），独立22项通过（27.26s），八文件291项相关回归通过（128.23s，exit 0）。
下一项为四臂连续运行协调：公平初态与固定策略核验、唯一公共链、整段预算、完整证据持久化与重放。
当前仅为内存事务；训练容量绑定、正式规模、连续输入、完整恢复/right-censoring及科学/正式运行门仍未完成。


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
