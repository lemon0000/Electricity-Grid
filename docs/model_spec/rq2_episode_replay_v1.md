# 连续episode来源绑定归档与重放

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE，限定开发验证完成。

`episode_replay.py`保存完整EpisodeSnapshot，公开重放接口仅返回diagnostic。
独立输入包括未消费的共同origin、四臂origin、有序EpisodeHourInput tuple、reference selector/spec/budget和EpisodeBudget。
expected_sha256须独立传递；expected_input_identity由上述独立输入计算，并与归档中的输入身份核对。
导出接收的input_identity只作为声明，导出本身不认证来源；来源核对发生在重放时。

## 完整返回链

- 用既有EpisodeSession构造器重验公平初态、策略及整窗预算；不调用advance或求解入口。
- 逐小时重验来源、clock、baseline、会计输入，从当前活动臂推导资源预留。
- 用selector专用重放重建reference结果，复用publish_common_hour重算映射与唯一公共publication。
- 各臂独立执行业务纯核，按exact action计算实际MW功率，再将这一功率作为actual selector重放的独立输入。
- 业务拒绝不增加dispatch；完整网侧未解决记录重现为未解决；仅双侧成功时更新业务与网侧状态。
- 重算每小时调用数、started/skipped/unattempted库存、外层提交和最终snapshot，逐字段canonical比对。

实现不替换共享模块globals，不注入归档末态，不调用live小时事务或episode advance。
重放使用私有临时typed结果连接纯核，公开诊断不返回任何session/cursor/snapshot。
两个小时的重复验证不代表完整履约；归档中的未偿恢复债务原样保留。

## 中断与证据缺口

完整selector拒绝记录可重放；缺失返回、partial原生记录或外部中断只给partial_episode_evidence。
报告分别列出verified_hour_count、verified_arm_result_count、business_power_bindings_verified和unverified_attempt_count。
这些计数及selector_diagnostics描述首个证据缺口前的验证prefix；power计数可包含首个缺口臂已核的业务功率。
同小时其余已返回臂还会独立重审以核调用和执行库存，但不扩大公开prefix计数，不推进外层状态。
archive_reproduced=false，reproduced_snapshot_identity为空；不把缺失调用数填零，不模拟未知异常。
partial之后的原归档后缀保留且标为未验证；不得从该前缀恢复执行。
仅actual缺返回/partial且该臂fail-closed、其他臂使小时advanced时允许保留未验证后缀；reference未解决或外层中断必须终止。
缺失reference/common/arm返回必须对应outer interrupted，不能通过删除成功对象伪造partial。
partial调用库存逐项核known_solver_calls、总调用数是否未知、dispatch未知臂及started/skipped/incomplete/unattempted；
有返回的partial selector调用数经选择链重审后仍计入known，未返回的调用不填零。
外层interrupted必须无后缀、outer_committed=false、总调用数未知，末态common/arms回滚到此前状态，预留保留。
partial中断原因、未接受候选及未知执行范围不声称已重现；已核source输入身份不代表这些记录真实性已认证。

attempt_in_progress与budget_exhausted snapshot缺少对应invocation journal，当前明确拒绝导出/重放。
create-only写入限定_non_authoritative.json；不提供atomic publication、fsync、跨进程lease或安全resume。
所有native_execution_authenticated、formal_result、security_certified、resume_authorized固定false；容量、完整服务及因果证书为空。

## 验证及后续

最终39项targeted通过（170.63s）。四文件相关回归192项通过（289.75s，exit 0），
该回归对应`7e725125ec050109252d2fcfe6ecc7809b27d7e6083f8edf3cb3dde7691002db`源码；
之后仅补interrupted error非空检查、提取相同source closure清单并增加fresh-import测试，最终targeted已覆盖。
测试命令前缀：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`。
targeted为`tests/test_rq2_episode_replay_v1.py`；相关回归另含selector_replay、hourly_transaction、episode_coordinator对应的`test_rq2_*_v1.py`。
测试覆盖真实两小时链、拒绝/中断、partial调用与执行库存、联动篡改、新进程重放和fresh-import闭包。
重放测试禁止原生求解及live selector/episode执行入口；初始测试轨迹只用每次1秒/1线程的微型开发求解。
选择链重放、小时事务及协调器的源码hash保持原值；git diff --check通过。

开发SHA256（非production seal）：

- source：`1540428df4aa3d473d43ed2d03327def9849994b45df2e6fa8b1994cdfc52e82`
- test：`68296b849298705500c2502b0cf5b6a73521c75f38c8e4821b52dd1d2588e5cc`

独立最终39项targeted通过（176.58s，exit 0），限定pre-seal无开放实质代码finding。
审查发现的partial分类、外层提交/回滚、调用库存及interrupted错误记录缺口均已修复并复核。
最终源码未重复同范围192项回归；直接前驱的相关回归与最后局部检查变更后的完整targeted分开保留。
随后补跨进程唯一性/安全恢复与正式规模。
完整数据、训练容量和固定策略绑定、恢复/right-censoring及科学/运行门仍开放。


## 2026-09-20 本地事务日志与开发恢复

`episode_store.py`已接入同一规范NTFS目录内的合作进程排他、SQLite intent/result事务、完整来源重放后的开发续跑。
调用前commit并重新打开核intent；已有intent但无result保持unknown并禁止重跑，结果commit响应丢失通过inspect与外部保留head对账。
每个新archive须延续此前已提交的exact历史和前态；复制目录、schema/源/提交链漂移、reparse/hardlink与不完整初始化均拒绝。
独立31项targeted通过（360.92s），同一最终字节三文件101项相关回归通过（562.22s，exit 0），限定pre-seal findings闭合。
覆盖真实进程竞争、五个os._exit崩溃窗、提交异常、NTFS路径及历史改写反例；进程退出测试不等于断电硬件认证。
`episode_replay._verify`现在私有返回诊断及完整重建snapshot，公开wrapper仍只返回诊断；最新source/hash与完整命令见`docs/model_spec/rq2_episode_store_v1.md`，旧验证历史保留。
本组件仍为DRAFT_NONAUTHORITATIVE，仅沿用120调用/60秒短预算；没有生产lease、正式运行授权或新真实观测。
下一必要工作为正式网络规模与continuous输入适配的仓库核查/开发；完整数据、训练容量/固定策略绑定、恢复/right-censoring及科学/运行门保持开放。
