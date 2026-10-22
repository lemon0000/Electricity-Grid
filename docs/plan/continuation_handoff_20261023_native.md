# C原生P1受控开发交接

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。接续[纯数值接口交接](continuation_handoff_20261023_numeric.md)及[公共包计划](staged_deliverability_c_public_numeric_package_plan_v1.md)。用户已确认保留公共网络方向；两母线保持机制回归。目标“推进计划”继续active。

## 当前实现与证据

新增[后端](../../src/staged_rts24_highs_backend_v1.py)保持原Pyomo模型、min目标/offset、连续列、规范化A与对角Hessian约定，固定HiGHS1.15.1、QP额外regularization0、必要容差及单线程。保存API trace、完整原生数组/枚举/info、run flags与log_file pin；父子两端均通过原pure importer重编译并独立审计，任何不完整绑定/提取/发布均为transport未决。fake API与解析点不是公共数值结果。

[受控runner](../../experiments/staged_rts24_native_probe_v1.py)固定P1：on_time/early/full_temporal，真实前史-2起至2的五小时实际前缀最多21点；随后工程前后h=1/2 normal C及最低索引branch/generator F/raw共10点。共31次上限（16QP/15LP），零重试、reserve不退还。成功满包有124次模型编译、62次import；静态次数不冒充实测。实际轨迹原观察末端8不截短，已接受前缀、数值未接受输入、missing_input及右删失分开。任何必要失败均不再开始新点。

[新guard](../../src/staged_rts24_process_guard_v1.py)复用旧原子Job-list创建，保留成员HANDLE并按PID/creation FILETIME确认身份。真实反例显示active=0早于孙进程终止信号；现要求所有已持有HANDLE signaled、active=0、PID list空且历史TotalProcesses==保留身份数。采样遗漏短命进程会unknown，不伪造quiet。真实嵌套Job及故意漏成员的普通检查覆盖闭合与拒绝；旧所有权原语字节未改。

完整命令与结果、失败历史及PRE_SEAL findings见[开发核验记录](../../results/tables/staged_rts24_native_v1_non_authoritative/development_checks_01/development_checks.json)和[验证说明](../../results/tables/staged_rts24_native_v1_non_authoritative/development_checks_01/validation_report.md)。旧B1–B3的118个保存文件、42仓库pin、7选定外部、C/build/causal、旧journal 531/558007B与138/286322B以及numeric检查点均保持。受控解释器无psutil，新的静态bookend直接复现旧文件核验与版本规则，仅读历史psutil metadata，不启用或导入user-site。

## 注册与运行边界

[开发注册](../../results/tables/staged_rts24_native_v1_non_authoritative/registration_v1.json)绑定13个新/复用源、旧runtime/config/input、选定应用文件、环境、DAG及预算。其exact SHA见开发记录；native_authorized=false。**未创建p1_01，未构造真实Highs对象，未调用solver或启动长实验。** 没有production manifest/lease、seal、official verdict或receipt。

停止帽为原生5秒、单点进程10秒、外部worker wall300秒/无进展30秒、采样全树RSS1GiB、每进程commit1GiB/Job commit2GiB、输出64MiB/5000文件；fresh20秒，历史成员HANDLE1024上限。31×10>300，均为独立停止帽，不是预计时长。launcher此前只读注册/旧工件核验另属准备成本。观测为selected inclusive calls，排除自身写入和末manifest/completion，非全OS I/O；流捕获限Python和HiGHS log_file。受控保存/归零失败及缺诊断按unknown保留，不延长、不恢复、不补造finish/fresh。

下一步仅在用户对这个exact P1作出专项授权后，且登记SHA/源/环境仍匹配时，执行一次[launcher](../../experiments/staged_rts24_native_launcher_v1.py)；命令需要`--execute-p1 --registration-sha <已核exact SHA>`。注册/开发审查不授予该权限，当前不要执行。若有新代码/输入/环境或范围，先重审并用后继记录保留原绑定。

公共点/g、真实dual/日志与保存成本、完整139、F/X反事实任务时序、C整体性能及D/E点数/资源仍OPEN。可独立推进保存成本后继，合并同append重复pack/inventory；保留删除检测、完整闭包、unknown与fresh等价，不重跑旧attempt或外推192h。

新对话先读本页、AGENTS.md、agent.md第7–9节、C范围/公共包/P1合同和blocker，刷新Git与活动进程；复用旧核验，不恢复任何attempt。本检查点Git提交号以远端读回为准。
