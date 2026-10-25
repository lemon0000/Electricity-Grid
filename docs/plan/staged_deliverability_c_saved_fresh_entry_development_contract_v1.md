# C：F actor 真实文件入口开发合同

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[外部调用交接](continuation_handoff_20261025_saved_fresh_invocation.md)，起始HEAD `eb770f276e6b8c3bd0fc293b6deca8a13b933269`。root唯一writer，只读PRE_SEAL；原三draft可迭代，已有snapshot/失败/历史字节保持。SF49集合、科学adapter、原F范围/预算、P1、旧guard/outer及全部门禁保持。本轮不执行actual saved F、solver或正式运行。

当前parent/fresh/controller仍通过`EXE -B -s -c`自导入ENTRY。直接运行ENTRY文件时，Python的首个search path为experiments目录，`__main__`也不同于canonical module；因此不能直接替换argv字符串并认为入口已连接。本轮把ordinary actor切换为`EXE -B -s ENTRY --ordinary-entry`及固定角色/参数，source/runtime/实际argv验证后建立唯一ROOT search path和同一module alias，复用原业务与Job/quiet路径。broker及通用stage小probe的旧`-c`路径保留为独立ordinary范围。

## 闭集与顺序

- 参数顺序、数量和角色固定；parent/fresh携带context path/SHA、tree SHA、channel name/nonce，supervise携带context path/SHA、mailbox/request/ACK SHA、channel name/nonce。无任意module/function/factory参数，重复、缩写、unknown和非规范标量拒绝。builder为纯内存函数，最后逐token比较独立重建argv。
- default main对空/畸形/旧scientific argv非零退出，不attach/create/output。普通入口只收ROLE_PROBE_SCHEMA和pytest专用输出。原scientific argv_for/validate_actual_entry/execution_context不放宽，actual _create_role_owner仍关闭。
- parent/fresh先读context并验证source/executable/environment、output/tree和实际main/argv，再Open-only attach stage channel。controller先核闭集语法，Open-only读取真实mailbox/绑定/已ACK request/context，重建完整argv并完成source/main验证，之后才写进度、return或构造下一actor。
- 子进程在项目/science import前核`__main__` file/spec、argv与orig_argv、EXE实际path/bytes/Python version、cwd和ENTRY source pin；不声称Python执行stdlib前的自认证。父端spawn前已有source与CreateProcess exact输入绑定。
- 初始sys.path不接受空/relative/ROOT别名；仅允许实际script目录和compute环境下的绝对路径。验证后将script搜索项替换为精确ROOT、唯一放首位并冻结完整tuple。canonical ENTRY名只指向同一main对象，另一个对象已占用即拒绝。后续path/module/argv漂移在下一次受保护RoleStore操作或proof书挡时停止，不宣称异步实时监控。
- Bootstrap proof只作应用自检诊断：parent/fresh写原events target，controller带入原外部return；不新增F target、不替代kernel owner、独立OS command-line或完整runtime closure。transport名称/nonce是绑定标识，不是秘密或同用户敌手认证。全局与局部F verified保持false。
- executable在ordinary域仍只声明path/bytes/version；其file identity不是本轮独立采用结论。一次reservation/constructor、固定closed case故障、所有原quiet/close/原错/secondary规则保持。

bootstrap自身直接复核`parent/fresh→ROLE_PROBE_SCHEMA`与`supervise→INVOCATION_SCHEMA`配对、DRAFT authority、scope/repo和五个全局及三个局部gate均false，不能把调用方先前的间接检查当作当前许可。preimport扫描观察sys.modules中可解析的module file路径及src/experiments/tests/pyomo/highspy名称；除同一main对象外，具file路径落在ROOT内的模块或这些namespace均拒绝，proof记录实际扫描结果及该扫描口径。无file元数据的动态exec/同用户主动改写仍不构成完整runtime closure或敌手认证。

五个新增ordinary fresh故障case固定为`entry_alias_occupied/entry_alias_drift/entry_path_drift/entry_orig_argv_drift/entry_repo_module`；只在ROLE_PROBE_SCHEMA选择，不是CLI factory或scientific分支。它们须在stage attach/应用frame前拒绝，仍由原outer owner证明完整quiet。

## 活跃console image与退出分类

本轮角色回归曾在预期G3注入之前因`root_exited_with_descendants`停止，原失败及15个O文件保存；完整quiet不把该旧epoch改写为成功。该记录只证明残留成员分类未决，不追认它的image或具体API失败原因。为避免只能在退出窗口临时取image，四个exact内部label（role_graph_parent/fresh、invocation_broker/controller）且无外部owner_factory时，内部使用原OwnedChild的私有subclass；原Job/HANDLE/close完全复用，real_owner仍按未注入factory的原物理语义，不凭任意subclass获得。

subclass先成功调用原sample，原RSS/PID/commit返回不变；只对本次PID集合中、已有retained PID/creation/HANDLE且仍live的非root成员查询kernel image，每identity最多一次。key/原HANDLE/status/query时刻及一份≤4096字符SystemDirectory/conhost路径纳入创建线程commit；negative/unresolved保持，查询失败不认可，不新增HANDLE/无限重试。terminal仍要求唯一remaining PID、唯一原identity/同HANDLE/valid signal；当前image成功却不符则永久未决，当前image因Win32错误不可读时才可凭同一live positive缓存分类。未知/额外/非conhost仍失败，完整quiet/all signaled/active0/close始终是后置条件。

watch/状态机/record字段及旧guard不改。terminal_system_helpers.observed_at仍是root exit后的分类时刻，不伪装成更早image采集时刻；record本身不独立证明live cache的查询时间。覆盖条件用injected unit owner/classification和实际native handle/close证据分别标明；不通过Suspend系统console线程或伪造kernel PID sample强制制造窗口。真实root-exit残留helper窗口的强制正例若未观测，保持该证据边界OPEN；它不由normal完整图或manual分类替代。

## 验证及预算

新的successor普通开发预算300s：pytest实际累计≤240s、collection/静态/保存核验≤60s；先登记nodeids及各组帽，单组≤45s；必要affected修复先登记剩余预算、单组≤30s，无自动actor重试。首次保存核验在修改canonical源码前执行并保存，后续用其exact snapshot/原日志/输入pins解释历史，不用已变canonical代替冻结源码。

覆盖正常parent/fresh/controller直接文件运行、ROOT/module alias与sys.path固定、argv/orig_argv/source/EXE/env拒绝、错误顺序/重复/unknown/角色/path/nonce/SHA、attach前拒绝、科学schema/default main拒绝、闭集factory/一次reservation、应用proof与父端捕获匹配，以及原真实外部Job/阶段/quiet/失败发布回归。每次pytest保存三源码snapshot、原始stdout/stderr、source首尾书挡和终态。只使用已有ordinary fixture、8s context及15.3s外部descriptor；不放宽阶段或内存/输出帽来获得通过。

本轮只证明ordinary actor的文件入口；actual saved owner、完整调用计数/最大合法context及四record编码、180s整链、arming/host最终分配硬中断、科学采用和资源/正式准入继续逐项闭合。源码已经存在或ordinary完整图成功均不授予真实F启动权。
