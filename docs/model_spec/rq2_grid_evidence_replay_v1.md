# 原生求解记录落盘与模型相对一致性重审

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE，独立pre-seal findings已闭合，修复后相关回归通过。

`grid_evidence_replay.py`是完整episode持久化/无solver重放的必要前置接口。
已有`GridSolveEvidence`中的optimal、assignment_valid、residual不能从JSON直接转为owned求解结果；
本模块保留原始记录并从调用方独立给定的canonical模型重新计算这些字段。
它不返回GridSolveEvidence、ReferenceSelectionResult、ActualDispatchResult或可执行cursor。

## 证据边界

公开接口接受builder及独立给定的input_identity/purpose/specification/budget和expected_sha256。
input_identity在本层仅是外部元数据pin：本层不证明builder由该input导出。
报告固定model_relative_only=true、source_input_binding_verified=false、selector_chain_verified=false。
因此replay_consistent只表示在调用方给定模型下，保存记录的已验证部分一致，不能用它推进episode状态。
后续仍须selector-specific wrapper从独立typed输入构造模型，验证prior objective锁、stage链、policy及来源，
再完成reference→mapping→business→actual→episode的全链重放。

external digest仅检测与调用方独立保留bytes的一致，不是原生solver真实性签名。
native_execution_authenticated、formal_result、security_certified固定false；最优性与不可行性证书均null。
native infeasible/零解只重现原生状态解释，不产生数学不可行证书。

## 重审内容

1. canonical JSON及准确字段表、typed scalar、无重复键/非有限JSON常量；外部摘要、purpose/input及执行元数据匹配。
2. 重新构造模型，检查规模、structure、initial/preload、声明选项及runtime版本；实现身份覆盖完整本地依赖闭包。
3. 对单解记录，再次构造fresh canonical模型，并要求结构和初值不变。
4. native variable/objective名字唯一且属于完整canonical库存；仅按原核允许的fixed/unused规则重新生成completion。
5. loaded必须等于native+canonical completion。重新赋值，核固定值、约束残差、整数残差及目标值，并核native objective。
6. 从typed solver/termination/solution状态、solution count和原生LB/UB重新计算原核optimal/native_infeasible标志，
   与保存字段比对。不会仅用保存的optimal=true通过审计。

模型相对重审返回诊断。complete_native_record且replay_errors为空时replay_consistent=true；
这也可能是可信重现的timeout、零解或不可行赋值记录，不表示求解成功。
canonical_assignment_valid、optimal_flag_reproduced等字段分别表达重新计算出的赋值和原生状态标志。
若原生记录不完整或含无法重放的执行异常，则scope=partial_execution_evidence、replay_consistent=false；
保留recorded_execution_errors和可重新核验的赋值，不猜原生调用、不填补缺失bound，也不升级为可执行状态。

## 文件与执行

export/write只接受本地owned GridSolveEvidence。落盘文件必须以`_non_authoritative.json`结尾，使用create-only，
不覆盖已有文件；读取拒绝symlink/非普通文件，校验独立摘要和canonical bytes。
写入不是production原子发布或跨进程lease；中断产生的partial文件保留，并由摘要/解析失败拒绝。
replay模块自身不创建solver、不运行优化；solver_calls_by_replay_module固定0。
通用builder是调用方代码，其外部行为未被验证，external_builder_effects_verified=false，不能声称整个call chain零solver。
真实reference/actual stage测试使用受控构模函数，并禁止capture solver调用；另有有副作用builder反例验证此边界。
本层尚未保存/恢复完整episode，也未关闭完整连续输入、训练容量、恢复/右删失或科学协议门。

## 验证记录

初版测试因引用旧fixture不支持的fault名字出现3个测试失败，已更换为实际支持的native故障注入。
随后34项通过（12.65s）；加入fresh model、真实completion及依赖闭包后40项通过（20.48s）。
上述为开发中间版结果，旧模块源码保持不变。
修复前六文件264项相关回归通过（128.35s）。随后独立审查发现等值int metric/completion、native solver额外字段
及通用builder零调用表述的问题，已收紧typed字段/库存并区分模块自身与外部builder效果，增加针对性反例。

修复后58项针对性通过（20.58s）；独立固定字节58项通过（20.15s），均exit 0，限定范围无开放实质finding。
修复后六文件相关回归276项通过（122.60s），exit 0。episode/hourly/reference selector/actual selector源码hash与前轮一致，未修改其语义。
git diff --check通过。测试命令前缀：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`。
targeted为`tests/test_rq2_grid_evidence_replay_v1.py`；相关回归另含reference_selector、actual_dispatch_selector、
continuous_grid_candidate、continuous_prefix_handoff、episode_coordinator对应的`test_rq2_*_v1.py`。
真实微求解每次1秒/1线程，重审测试显式禁止capture求解入口；测试临时文件仅在pytest/system tmp。
无formal、seal、production manifest/receipt、下载、付费查询或仓库清理。

开发SHA256（非production seal）：

- source：`fb78087629c16987086d0c163e8cc86566512491be2de95fb4c7925959bca586`
- test：`f621e53abef5157e0de23f79dba8551aba350970c86c22f8f04d3428a1e1a53e`

## 下一连接项

先由reference/actual专用重放接口绑定独立typed inputs及policy，从已验证的完整native记录重做stage exact/lock/gap审计，
再按完整stage链重算选择结果。单stage一致或未认证native infeasible不能产生可执行后继。
然后连接共同映射、逐臂业务和网络事务、episode预算/失败库存与外层提交，并以完整归档逐字节比对。
中断或缺失原生返回只重放到证据可达边界，保持外层前态和未知调用数；不重跑solver去填补历史。
跨进程排他性及安全恢复仍在完整重放之后验收，当前不提供恢复入口。


## 2026-09-20 Reference/actual选择链来源绑定重放

`selector_replay.py`已实现独立输入/policy绑定、逐级canonical模型重建、目标锁定/物理重审及完整结果身份比对；公开接口只返回诊断。
完整拒绝与partial中断分别记账；partial只验证此前prefix，不产生所选末态或恢复游标。
独立pre-seal发现partial单级及总调用数可联动改小，现按capture阶段绑定调用数并拒绝create与post-call证据混存。
修复后100项targeted通过（78.41s），独立100项通过（79.66s），finding闭合；七文件348项相关回归通过（223.48s，exit 0）。
合同、命令与开发hash见`docs/model_spec/rq2_selector_replay_v1.md`。现有episode/hourly/两类selector及原生重放核源码保持。
下一项为全episode来源绑定归档与无solver重放，连接mapping、业务动作与实际功率、预算预留及外层提交；随后验收跨进程唯一性与安全恢复。
本组件仍为DRAFT_NONAUTHORITATIVE；没有新增真实观测、正式结果或认证。完整连续输入、训练容量与策略绑定、正式规模、恢复/right-censoring及科学/运行门仍未完成。
