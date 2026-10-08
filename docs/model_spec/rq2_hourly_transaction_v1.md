# 共同小时与业务—网侧双状态事务

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE，独立pre-seal finding已闭合，修复后相关回归通过。
实现`hourly_transaction.py`，测试`test_rq2_hourly_transaction_v1.py`。
这是内存中的受控候选对象与共同提交接口；publication不是production发布、落盘事务或运行授权。

## 共同来源与一次固定的当小时输入

CommonHourCursor从origin绑定共同reference初态、数值selector policy、mapping、完整normal/prepared来源审计身份、
business source anchor及实现闭包。后续source hour/workload hour必须连续，split、outage seed、trace、
normalization与provenance不得变化，U由cursor固定而非逐小时另传。
请求入口消费已运行的owned ReferenceSelectionResult，并重新运行精确适配与来源校验；本层不重跑reference solver。
第一小时也必须匹配origin中预先绑定的reference selector/solver/budget身份。

CommonHourPublication含当前隔离网侧信息、disclosure、reference和mapping证据、完整CapacityObservation及exposure_id。
limits、deadline和available flexibility在publication中一次固定，逐臂接口不接受覆盖；raw grid/CFE请求也来自同一mapped hour。
origin并不将这些业务字段或原始split/seed传入reference选择器。
相同publication在四臂记录中使用相同exposure_id，计数时应按该ID去重；它不是经验风险分母。

共同请求与共同业务输入通过后推进reference cursor，独立于各臂是否成功。
reference未完成、映射分辨率失败或共同业务输入非法时，不生成publication，common cursor转halted，
保留最后已提交reference与source anchor；已选择但未发布的reference候选保留在CommonHourAttempt。
不同hash命名空间仍按显式pairing声明，严格split/seed/hour校验不证明真实观测同源。

## 逐臂固定策略与双提交

ArmHourCursor只从canonical零历史CapacityPolicyCursor和ActualDispatchOrigin初始化；
business anchor须等于共同anchor，actual/reference网络、normal plan、disclosure及起始小时须一致。
origin固定common origin、mapping、业务policy、actual dispatch selector/solver/budget和实现身份。
后续只消费该共同链的下一publication，拒绝重复、跳时、跨episode和策略/实现漂移。

执行顺序：

1. 从共同publication取完整CapacityObservation，调用已有advance_capacity_policy，保留immutable业务candidate。
2. candidate未提交时停止，不调用网侧selector。
3. candidate可提交时，精确重验`P_norm = baseline - grid_served - cfe_served + recovery`，再计算`P_MW = P_norm * U`。
4. 以canonical ratio构造PrescribedDcPower，调用既有actual dispatch selector；功率不由网侧优化或裁剪。
5. 全级成功且返回功率及previous-state lineage一致，才同时提供新的business cursor和actual grid state。

若网侧输入不合法或selector unresolved，result保留业务candidate、给定功率及可获得的solver证据，
`published_pair=None`，已提交的business/grid均保留原值，新coordinator cursor为halted。
候选business cursor中的committed只表示通过业务自身验收，不代表事务提交；消费方以published_pair为共同提交标志。
使用halted cursor消费后续小时被拒绝。输入链或policy身份错误直接抛出，尚未构成合法本小时尝试。

## 失败记账与四臂边界

| 状态 | 实际状态推进 | 证据含义 |
|---|---|---|
| common request/input unresolved | 不推进common reference，不发布公共小时 | 保留reference/mapping候选；不填0请求 |
| business_rejected | 两侧均不推进，不调用网侧solver | candidate_grid_service_failure单列，不能称实际物理运行失败 |
| network_input_rejected | 两侧均不推进 | 例如恢复实际功率超过connected/physical界，保留功率及错误 |
| dispatch_execution_unresolved | 两侧均不推进 | fixed-power输入身份形成后，selector执行抛出异常；调用总数可能未知，不当作零调用输入拒绝 |
| physical_network_unresolved | 两侧均不推进 | timeout/无已验赋值/后级失败，不等于数学不可行 |
| committed | 同时推进business/grid | 当前机制内通过业务与网侧验收，仍无工程/容量证书 |

CFE-only的grid_service_applicable=false，grid_service_failure及candidate_grid_service_failure均为None。
其实际功率仍有单列物理检查，失败不改写为grid义务失败；是否进入正式D_C仍待科学协议决定。
其他臂的grid_service_failure只在双提交后报告；失败尝试的业务短缺保留candidate字段。
CFE短缺、期限、逾期及债务沿用业务record，成功提交也不等于所有CFE/恢复义务完成。
本层复用已有四种arm_id的CapacityPolicy，不求解训练D_N/D_C/D_B/D_J；B6标签不代表本层重建了分离规划最优模型。

## 执行与证据边界

该层是不可变内存接口。调用者仍可保留旧cursor并创建分支；尚无外部attempt ledger、进程lease、
持久化恢复或排他性“只发布一次”机制，不能声称阻止旧origin重试或跨进程重复计数。
下一四臂runner必须固定唯一公共链，核对所有arm配置与公平输入，并维护证据计数及落盘重放。
业务prefix单独导出不含共同来源完整链，不能替代保存CommonHourPublication、ArmHourResult及其身份。

继承的selector预算是逐次/逐小时开发预算，不是整个多日/四臂运行的总资源上限或wall-clock watchdog。
reference最多18个UID、actual最多19个UID，正式规模、normal发布与数据供应仍须后续验收。
所有初态、U、调用与恢复条件仍为机制；actual指候选执行状态，不是真实运行观测。
正式结果、因果、容量、安全和数学不可行证书均未产生。

## 验证记录

初版14项targeted通过（31.14s）；随后将limits/due/available统一固定到共同publication。
该修订的测试进程在会话中断后handle不存在，未取得可引用最终结果；已重新验证当前文件。
新增完整共同输入、分块一致性、origin数值policy及fresh-import闭包检查后，18项targeted通过（26.32s）；
八文件287项相关回归通过（128.63s，之后新增测试前，源码相同）。随后补恢复超connected limit与reference timeout，
两项单独验证通过（6.78s）。独立pre-seal发现共同发布在适配返回后缺少提交前实现身份重验；
已在publication/cursor构造前补重验，并新增contract/implementation漂移两类故障注入。
修复后22项targeted通过（27.43s）；独立复核22项通过（27.26s），finding闭合，限定范围无开放实质finding。
修复后的八文件相关回归完成：291 passed in 128.23s，exit 0。
微例包括G=15、U=45的1/3请求、三臂通过而CFE-only网络未完成、业务短缺零solver调用、
网侧末级timeout不提交债务、reference在单臂halt后继续，以及恢复功率超过baseline仍按actual MW检查。

测试命令前缀为`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`。
targeted为`tests/test_rq2_hourly_transaction_v1.py`；相关范围另含actual_dispatch_selector、common_request_adapter、
reference_selector、continuous_capacity_policy、continuous_aggregate_response、continuous_prefix_handoff、business_grid
对应的`test_rq2_*_v1.py`文件。真实微型求解每次1秒/1线程；未启动formal或生成production manifest/receipt。
此前22项针对性/291项回归对应开发SHA256（非production seal）：

- source：`b82a556275e70fffaa462cff2e72dbfc16841534141ab9c4aa024cf00611c0bc`
- test：`ef1fe068ddd82f3ec5a8da492ee559f7bf15d440fcf025b1de334ba69817849a`

后续四臂episode集成中发现selector执行异常可能被误标为输入拒绝，已在dispatch输入身份形成后、selector调用前
切换为dispatch_execution_unresolved，并新增故障注入测试。该分支保持两侧状态不推进，完整solver调用计数不能从缺失结果推断。
本次开发SHA256：source `18bffb4a316ea0b21e01a8614ed34b21e738d2423c6fa8d207d987046f995725`；
test `c26f314ffd06107772fef91e5336461acd1f4e7dab84433e308622848f9568f7`。
当前修订验收与episode一起记录在`rq2_episode_coordinator_v1.md`；此前291项不是该新增分支的验证证据。
