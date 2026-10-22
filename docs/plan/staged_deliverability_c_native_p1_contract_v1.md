# C原生P1后继开发与有界校准合同

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。接续[公共数值包计划](staged_deliverability_c_public_numeric_package_plan_v1.md)及[纯接口检查点](continuation_handoff_20261023_numeric.md)。本轮先实现并仅作无solver普通检查；具体native运行须在本合同/实现/测试稳定并独立审查后，另获用户对P1的一次专项授权。不得由开发、文件、CLI flag或PRE_SEAL结果推导用户授权；没有production候选、lease、receipt、seal或formal运行。

## 固定问题与DAG

公共配置及原Pyomo模型不变。P1固定on_time/early/full_temporal，真实前史first=-2起至h=2，观察末端仍为8；五小时实际路径最多21点。随后h=1/2分别normal C和最低索引选定branch/generator的F/raw，共10点。合计最多31次（QP16/LP15），全部串行、零重试；实际已知策略停止或任何必要数值未决均终止依赖后继，保留较短接受前缀和package incomplete。

调用DAG为源/环境与旧工件核验→原公共fixture→逐小时P0→实际事故raw（若有）/恢复min/max→固定策略→策略后actual零额外削减→原点/经济/child独立audit→journal读回采用→两帧代表合同→finish→trusted binding→关闭→一个顺序fresh只读replay→完整state/summary/audit比较→源/旧工件末核→报告及稳定终态。fresh不调用数值后端。child身份只在父点/KKT之后形成，actual只在动作之后形成；不预填未来BoundQuery SHA。

每个point在父端先独占reserve ordinal，再启动子进程；reserve即消耗31上限，启动失败/超时不归还、不重试。另记run-invoked、run-returned、独立imported数量与fresh启动次数；不能把reserve当成已执行solve。点子进程用原typed CAS装载query，重编译问题并核SHA，返回完整原生数组和状态，先保存raw，再消费为原PointEvidence。父端重新编译并独立import，不信任子进程自报成功。

开发注册记录位于`results/tables/staged_rts24_native_v1_non_authoritative/registration_v1.json`，保持`native_authorized=false`。独立外部SHA参数绑定该记录；launcher在创建attempt前核exact compute解释器路径/字节、完整schedule及源码/config/input/选定应用文件/受控环境、旧工件；worker复核并以原fixture重建schedule一次。point/fresh仅核注册文件SHA/header与解释器，不重复生成完整schedule；point再把request的pins SHA与注册pins绑定。动态actual也必须满足已注册objective和parent request identity，仅动作power及父完整点相关的最终身份留待因果产生。文件与CLI参数不能授予运行权；它们不是production manifest/lease或seal。

旧工件bookend直接核已保存的字节与固定源/角色集合；不导入旧诊断程序。受控解释器禁用user-site，旧诊断所需psutil仅从历史安装位置读取唯一同版本distribution的METADATA/RECORD/WHEEL并绑定，不启用或导入该包。新核验与旧import式核验的prior/两core/numeric记录逐字段比较；B1–B3源漂移和build自描述遗漏均拒绝。历史pretty JSON按其已提交SHA原字节解释，不改写成新协议canonical格式。

31是native尝试上限。成功点各有父显式、子显式、子importer、父importer四次编译，满路径为124次模型构建、62次import；raw/status门先失败时较少，不填造未执行次数。注册准备、launcher完整核验及worker各调用一次schedule，各产生两次full compiler和五次selective compiler；真正代表合同另有两次full compiler，前缀/审计/两个reopen还有其必要的selective重审。每进程观察器保存attempt/returned/raised、selected编译/构模/绑定/生命周期/audit/CAS读写、原生构造与inclusive计时；嵌套时间不能相加，hard kill缺观察文件是unknown。reopen作用域禁止新构模、native及CAS发布；输出fresh报告在reopen返回之后。普通检查验证这些门，不把静态倍数当实际计数。

固定顺序为整个实际前缀在先、代表合同在后；任何必要数值失败后本attempt停止所有新point，包括独立兄弟/下一帧，仅保存和只读fresh。部分已成功合同行逐行保留。reference数值不完整时不捏造HourEvidence：当前观测及每点raw另存为`numeric_unresolved_observed_current_inputs`，与journal只表达接受前缀的missing_input终态分开；已观测未决不能被finish隐藏。

## 后端与状态

Highs对象构造与solver API调用仅在显式native point入口；worker/fresh为既有runtime identity会加载highspy入口，fresh仍是零构造/零solver call。普通数值测试使用fake API，另一次只读类元数据核对未创建任何实例。绑定当前highspy版本、Python、源码/二进制及选定依赖；不是全系统生产环境封印。固定min目标、原offset、continuous列、规范化A、None界±inf以及Hessian半系数约定，不变更正则项或科学验收限。选项、版本/枚举、完整原序row/column值/dual、objective、info与运行时间保存。

固定HiGHS1.15.1：LP simplex、QP qpasm，`qp_regularization_value=0.0`；kkt/primal/dual/optimality各1e-8，threads1、parallel/presolve off、random_seed0。QP内部regularization是加到Hessian的额外项，0在允许范围内；不能让后端额外正则化改变已声明目标。来源为[版本化官方选项定义](https://github.com/ERGO-Code/HiGHS/blob/v1.15.1/highs/lp_data/HighsOptions.h#L1284)。所有选项逐一set/get并核状态/类型/值，真实API若不接受则未决，不自动替换。

只接受明确kOk接口返回、kOptimal、必要primal/dual有效、完整有限数组及原独立audit。任何warning/error、limit/interrupt/infeasible/unbounded/unknown、缺dual、数值/绑定/audit漂移均无可用点并停止；没有独立ray/certificate，不推断数学不可行。不按结果换符号、选项、后端、阈值或问题。

actual/F允许明确primal-only：raw中保留原生无效dual字段，规范snapshot仅在dual_valid=false时置两个空tuple，仍不生成最优性证书；valid=true时完整校验。原生NaN/Inf原样语义标记保存，不能转成零或合法证据。

## 所有权、资源与停止

输出预留`results/tables/staged_rts24_native_v1_non_authoritative/p1_01`，当前不得创建或运行；授权后由launcher独占创建，一次attempt，不覆盖、不恢复。所有开发测试在pytest临时目录。复用原[Windows所有权原语](../../src/rq2_joint_deliverability_boundary_v1/normal_process.py)，原子Job-list建子进程、suspended校验后release；launcher在Job外。所有子孙都受kill-on-close约束，读结果前确认整个Job active=0；查询/归零失败保留unresolved，不宣布清理成功。

原生单点time_limit=5秒，含解释器/装载/导出/求解/提取/保存的点进程上限10秒；总wall300秒、无进展30秒、采样Job全树RSS1GiB、输出64MiB/5000文件，0.2秒观测；fresh最多20秒，启动前后记录进展以留出外层余量。所有权原语另施加每进程1GiB、Job2GiB的commit保护，commit与RSS分开报告，不互当同一测量。31×10秒>300秒，故这些是独立停止帽，不能保证31点全部完成或据此估计公共wall。环境固定单线程；无有效进展、资源/依赖漂移、任一必要点失败均停止并保留现场，不顺延。

watchdog异常和正常root退出均quiesce整个Job，保留启动、事件、每点request/raw/result/log、journal及可信prefix；退出后复查wall/存储并预留终态文件。硬kill没有可信failure witness时，不补造finish或接受尾部final/pending，fresh按现有规则拒绝。真实阻塞磁盘/掉电与保存失败仍不等于被OS测试完全代表。

本开发的OS反例发现active=0可早于孙进程HANDLE的终止信号。新guard自创建起保留root及采样确认成员的HANDLE，以PID+creation FILETIME去重、逐一IsProcessInJob防PID重用；最多1024个历史HANDLE。终止与全部等待共用一个最多5秒截止，随后要求全部HANDLE signaled、Job active=0、PID list空，且生命周期TotalProcesses恰等于已保留的不同成员数。采样间出生又退出而遗漏HANDLE、失败关联或任何查询/关闭失败均产生unknown；不以空列表补回历史覆盖。本机快速Python入口确有Total=2/retained=1的实测unknown，不能把非零退出当quiet。真实nested Job、观察窗口内的孙进程及故意漏掉短命孙进程分别验证闭合/拒绝；这只覆盖相应OS路径。依据为[异步终止契约](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess)、[生命周期会计](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information)与[嵌套Job会计](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)。

数值未决仅限保存raw/log完整、原生clear成功、Job已归零且父子双方独立重现必要数值门未通过的分支；不得将依赖、绑定、接口提取、CAS/日志发布或cleanup未知改写为数值拒绝。transport异常直接退出，不追加finish或fresh；每次成功提交前缀的trusted binding另存，供诊断而非恢复。finish自身发布未决同样停止。native raw在非零退出后仍读取并累计已见run flags，缺raw不报告零调用。

worker观测文件成功发布后才生成绑定它的completion；该观测snapshot明确排除自身写入、终态manifest全树扫描与completion发布，也不覆盖所有stdlib/OS I/O。launcher保留自己的stdout/stderr及终态记录；受控路径的异常写入failure，诊断写入本身失败时仍以非零退出。精确root/path验证前、无法建立可信日志目录的bootstrap异常仅作为外部非零退出，不承诺逐点raw或日志存在。300秒计时从外部supervise开始，包含worker解释器、观察器、运行与收尾；launcher此前的只读注册/旧工件核验另属准备成本，不据此宣称完整命令的硬实时上限。采样RSS不保证捕捉两采样间尖峰；无RSS样本记unavailable，Job peak commit独立保留。

日志范围为Python stdout/stderr重定向与HiGHS固定log_file；不承诺捕获绕过Python的CRT/Win32直接stdout/stderr、崩溃dump或OS诊断。缺raw/result、非零退出及不完整诊断仍按transport未决处理。未来校准若出现关键直写，需在后继补齐捕获，不据普通fake API检查宣称真实native日志完整性。

## 完成本开发所需证据

普通检查必须直接覆盖新backend、runner和monitor：LP/QP数组/界/offset/Hessian、所有选项/status失败、原生raw保留、必要dual和版本错误、reserve不返还、父/child identity与重新import、固定DAG/31上限、fresh禁止backend、超时/无进展/RSS/storage/终态超限、worker先退留下孙进程、原子ownership与cleanup错误。R3只读sol_reviewer进行PRE_SEAL审查。旧B1–B3、C/journal/numeric绑定字节首尾核对。

即使开发检查通过，公共数值/g、完整139、完整F/X反事实时序及C/D/E资源仍OPEN。P1仅为真实后端与公共整链代表成本的有界校准，不能替代P2或三方法主比较。真正运行前将exact源码/config/input/environment、DAG与预算存入启动记录；用户专项授权仍独立必需。
