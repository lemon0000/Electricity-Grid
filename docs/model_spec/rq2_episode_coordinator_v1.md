# 四臂连续小时协调器开发

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE，独立pre-seal findings已闭合，相关回归通过。

实现`episode_coordinator.py`，复用共同请求、小时事务、capacity policy和两类selector。
本层不改变科学协议，不生成正式容量、风险或安全结论。

## 输入、公平性与执行

入口只接未消费的共同origin及按NETWORK/CFE/JOINT/B6顺序排列的四个owned arm origin。
重新调用小时事务初始化核验每臂来源，要求实际物理初态（含generation、availability、protocol、disclosure）、
业务physical/envelope/会计期和actual dispatch数值policy相同。容量及其声明ID可以按臂不同；
其他业务机制字段相同。容量仍是mechanism_assumption，本层未把它变成训练最优值。
B6沿用既有shared execution，尚不把B6标签当作分离规划优化及训练容量证书。

EpisodeSession持有唯一当前内存snapshot。advance只接当前小时；调用方不能传旧snapshot作为前态。
每小时执行一次reference selector、一次共同请求映射，然后逐臂调用小时事务。
停止臂单列skipped_halted_arms，不消费后续输入；共同请求链继续服务仍活动的臂。
全臂停止时episode停止。没有终端偿还、债务清零或虚构恢复小时。
四臂共享的publication/exposure保持唯一；这不定义正式经验风险分母。

## 预算与失败窗口

EpisodeBudget是显式开发预算：planned_hours最多168小时、120次预留solver调用、60个预留solver秒。
初始化在任何solver前，按planned_hours乘以n+2 reference及四臂各n+1 actual stage核验整窗最坏调用和声明time_limit之和。
整窗不适配预算则初始化失败，不能靠预期某臂提前停止通过。planned_solver_calls/seconds记录整窗资源计划。
具体实例可以更小；当前selector仍受自身规模上限约束。
各小时首次solver前，再按n+2 reference和每活动臂n+1 actual stage预留整小时调用数及声明time_limit之和。
预留永不退回，包括业务拒绝、reference失败和中断；报告实际已知调用数与预留分别保存。
初始化预算不足零调用拒绝；逐小时防御性预算检查失败则停止，不记作服务失败或数学不可行。
该秒数是solver声明上限之和，不是求解器强制终止证明、CPU耗时或整个程序wall-clock watchdog。

session使用非阻塞锁拒绝并发/重入；预留后立即设置暂时halted，写预留起的路径均处于异常记录范围。
异常（包括KeyboardInterrupt）保存当前可获reference/common/arm候选，再抛出，session保持停止。
中断的外层小时不推进共同和各臂已提交snapshot；已完成的内层结果只作候选证据。
EpisodeAttempt.outer_committed是外层提交标志；committed_arm_results及published_common_hour只暴露外层已提交结果。
arm_results保留内层候选，其自身published_pair不能代替外层标志。
若solver没有返回完整结果，solver_calls为None、solver_call_count_complete=false，known_solver_calls只表示已返回结果的累计调用。
小时事务已将dispatch_input_identity后的执行异常单列dispatch_execution_unresolved；这些臂单列dispatch_call_count_unresolved_arms，不能猜零调用。
正常结束的小时允许各臂分别成功或停止；status=advanced并不代表所有服务完成。
达到最后计划小时且仍有活动臂时，status=observation_window_complete并停止session，保留全部未偿债务。
若最后小时全部臂停止或共同请求未完成，则保留all_arms_halted/request_unresolved等具体结果。
planned_last_hour_attempted独立表示末小时已尝试；input_window_consumed要求所有计划小时共同请求均外层发布，
不表示四臂成功或完整履约。机器对象固定formal_result/security_certified=false，完整服务/训练容量/因果证书均为null。

## 证据与边界

snapshot保留全部EpisodeAttempt，其中包含求解前构造的完整EpisodeHourInput、reference结果、共同映射/发布尝试、各臂业务及网络证据、
已停止/未尝试臂、保守资源预留和错误。返回结果的前态、臂、policy、publication和exposure需逐项匹配。
started_arm_ids记录已调用的臂；arms_without_complete_result记录已开始但没有通过外层lineage核验的完整返回；
unattempted_arms只列尚未开始的活动臂。合法owned但lineage不符的返回保存在unaccepted_arm_result。
共同publication的完整业务条件必须匹配EpisodeHourInput，不能仅凭共同reference身份接受另一组limits/due/available。
原生solver赋值、物理约束和各stage最优性仍以已验收的小时事务及selector受控构造为信任边界；本层检验协调输入与状态链。
source/runtime身份在入口及最终候选snapshot构造后的提交前核验，最终检查失败保存候选并保持外层前态。
snapshot与attempt为受控不可变对象；session禁止copy/deepcopy/pickle。
本层排他性仅在单个内存对象内成立；另建session或进程仍可能重复运行。
跨进程lease、完整序列化与无solver重放/恢复尚需后续实现，不能用业务prefix代替完整链。
初态、normal提前可用性、request、deadline、headroom和mapping仍须按真实来源或机制声明分别记录。
正式规模、训练容量绑定、完整恢复/right-censoring、科学协议及运行授权门保持开放。

## 验证

首轮15项通过（28.73s），补整窗/中断语义后21项通过（27.91s）；后续两文件50项（63.72s）及51项（63.57s）通过。
这些是开发中间版本记录；最终代码另加完整共同输入替换和失败库存测试。
最终固定字节独立pre-seal：episode 31项通过（44.69s），hourly transaction 23项通过（32.10s），均exit 0。
独立提出的整窗预算、候选与外层提交区分、完整输入、lineage和最终身份重验问题已闭合；限定范围无开放实质finding。
最终固定字节九文件相关回归：323 passed in 170.08s，exit 0；git diff --check通过。
没有official review receipt或formal-ready结论。

测试命令前缀：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`。
两项targeted为`tests/test_rq2_episode_coordinator_v1.py`与`tests/test_rq2_hourly_transaction_v1.py`。
相关回归另含actual_dispatch_selector、common_request_adapter、reference_selector、continuous_capacity_policy、
continuous_aggregate_response、continuous_prefix_handoff与business_grid对应的`test_rq2_*_v1.py`。
真实微求解每次1秒/1线程；无formal/seal/production manifest、下载或付费查询。

开发SHA256（非production seal）：

- source：`18b703ed033c8f1012a9725207dc2f27fb0d18e6c1c28f9558f3f0b62ba89725`
- test：`5a9cd7947f1a43918dbaac0bff1b193a9683725b7bdb0c37427207f9b60e7f3a`


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
