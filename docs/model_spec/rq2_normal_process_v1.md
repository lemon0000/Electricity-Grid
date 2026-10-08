# Normal 开发子进程所有权原语 v1

状态：DRAFT_NONAUTHORITATIVE。仅用于新 normal 监督链的 Windows 底层开发；
没有 production lease、manifest、seal、receipt 或正式运行权限。

**当前合同入口：**本原语已在同一个未封存 draft 中接入 worker，并增加显式环境、Job 总 commit、
thread-id 所有权及整组静默核查。当前接口、边界和验收见
[Normal worker 与一次性日志连接](rq2_normal_worker_v1.md)及本文末尾“后续 worker 连接开发”。
下列“范围与接口”至旧哈希记录是**初次原语交付时的历史快照，不是当前接口说明**；
其中“尚未连接”“仅 PID”“无 Job 总内存门”等表述只描述初次交付状态。

## 范围与接口

`normal_process.DevelopmentNormalChild(argv, cwd=..., max_process_commit_bytes=...)`
创建无窗口、无继承句柄、处于挂起状态的子进程。显式 executable 必须为已存在的绝对路径；
argv 经 Windows list2cmdline 编码，未经过 shell。调用者必须在同一线程中使用 context manager，
创建后立即进入上下文，不复制或序列化所有权对象。
同线程是合作调用方前提，代码只强制创建进程 PID 所有权，不提供并发调用锁。
CreateProcessW 的环境参数为 NULL，继承父环境；本原语尚无显式环境清单或环境身份绑定。

`release()` 只允许一次；`wait(max_elapsed_seconds=...)` 使用创建前启动的 monotonic deadline，
开发 deadline 限于 60 秒以内。到期后终止整个所属 Job，并等待直接子进程退出；
确认终止最多再等 5 秒，未确认则抛错。因此 deadline 不是总返回时间的硬上限。
`close()` 关闭 Job，终止存活成员并释放线程和进程句柄；关闭不等待全体后代退出。
正常退出状态只叫 `child_exited`，保留非零 exit code，绝不等同数值接受或数学不可行。
即使进程在 deadline 检查时已经退出，也须由上层另审计完整 wall-time 接受门。

这是底层进程原语，目前没有接入 `normal_store` 或公开来源 worker。
上层仍须绑定请求/代码身份、持久化父子执行证据、核对 exit code 与日志、重放数值结果。
该类本身不限制命令所做的科研动作，不提供运行授权；本轮测试只执行短 Python 合成程序。

## 所有权与创建窗口

使用显式 `ctypes.WinDLL` / wintypes ABI、`STARTUPINFOEX` 和
`PROC_THREAD_ATTRIBUTE_JOB_LIST`，在 CreateProcessW 创建时就将进程加入预设 Job。
Job 开启 `KILL_ON_JOB_CLOSE`，句柄不继承且 Job 无名称；不开放 breakaway。
创建后核对 Job membership 及所有句柄的 non-inheritable 状态，再允许 release。
创建时间、等待、exit code 均使用创建时返回的同一个 process HANDLE；PID 仅用于诊断，
实现没有按 PID 再次 OpenProcess。Job 自身句柄负责整组终止与 peak commit 查询。

`PROCESS_INFORMATION` 在原生调用前即由对象持有；原生创建成功但 Python 尚未完成句柄赋值时的
异常也可回收返回句柄。父进程在创建返回、挂起或运行阶段异常死亡，最后一个 Job 句柄随之关闭。
能力依赖 Windows 10+ 的 Job-list 接口；调用失败即停止创建，不降级到先创建后加入 Job。
当前 ABI 尺寸与真实进程测试证据来自 Windows x64，其他架构尚未验证。

此方案依据 Microsoft 对 [创建时绑定 Job](https://devblogs.microsoft.com/oldnewthing/20230209-00/?p=107812)
及 [JOB_LIST 属性](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)
的说明。它避免传统 create-suspended / assign 两步之间父死亡产生的孤儿窗口。
保证针对合作调用方；不防御同权限恶意代码主动复制 Job 句柄、修改 Job 或结束监督进程后篡改工件。

## 资源证据边界

`PROCESS_MEMORY` 限制每个 Job 成员的 committed virtual memory；超限可使内存分配失败，
不必然终止进程，也不等于 working set / RSS 上限。
`job_peak_process_commit_bytes` 来自 Job 维护的 PeakProcessMemoryUsed，表示成员进程中的最高峰值，
不是轮询最大值、不是全部进程内存总和。见 Microsoft 的
[扩展 Job 资源结构](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)。
当前没有 Job 总内存门、系统可用 commit 储备采样、CPU 线程门或磁盘门，不能声称完整资源监督已完成。
不继承旧 transport 的 8/2 GiB、5 秒阈值。正常终止的进程同样可能经历分配失败；上层必须审计结果。

返回 `ProcessObservation` 仅是开发诊断；`numerical_evidence_verified=false`、`formal_result=false`。
不据退出码、Job memory 事件或超时推断 native 调用数、最优性、数学不可行、工程安全或完整恢复。

## 验证与后续

针对性测试使用 pytest tmp 中的真实短子进程，覆盖：挂起期间不执行、单次释放、
超时仅终止所属 Job、非零退出、真实内存分配拒绝、KeyboardInterrupt/SystemExit/普通异常释放、
父进程在原生创建成功返回后但构造器接管前/挂起/运行三个窗口 os._exit、直接子进程退出后的后代清理、
membership 核查失败、创建失败、原生返回后中断的两个 HANDLE 回收、x64 结构布局和高位 HANDLE。
没有 solver、真实电网运行或生产目录写入。测试通过只证明上述原语范围。

下一步将 normal 专用 worker 与一次性日志连接，补完整资源接受门和数值重放，再推进真实规模验证。
旧冻结 transport、normal 数值内核、source execution 与 normal_store 本轮均不修改。

验证命令：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_process_v1.py tests/test_rq2_normal_store_v1.py
```

相关回归 41 passed（27.47s）；独立 targeted 22 passed（1.02s）。随后仅将测试 PID 通知改为
临时文件写完后 replace，避免测试读取到空通知；主线程最终 targeted 22 passed（1.01s）。
独立审查指出的崩溃窗口措辞已收窄到实际测试的“原生成功返回后、构造器接管前”。
独立审查是 non-authoritative pre-seal，不产生 official verdict 或运行授权。
最终测试字节另经独立 22 passed（1.04s）；限定范围 finding 已闭合。

源码 SHA256：`6c50ce35bc0e938b094b1ae9c983f8275414eab9cc60cf258d9ffbf33cd6d9f2`。
测试 SHA256：`c464c59d6aa13903f2a95c9a4e0271f8afd81c6e4e73e2721071579e2e0ac32f`。
旧 normal_store / source execution 分别保持 `a79d766c08970875e8b65e5afc30ee7288d98bcc88a5474e9b5d7f7eace754f4`
与 `56a59908c99b5da24047bdd4c93478da6576b9224ca91e2994bc60cad79d57cf`。

## 后续 worker 连接开发（2026-09-20）

上文为初次原语交付记录。本 draft 后续为 `normal_worker` 连接新增可选显式 Unicode 环境、
可选 Job 总 commit 限制、同线程强制校验和 `quiesce(max_seconds=...)`。
quiesce 终止剩余成员并查询 Job accounting ActiveProcesses，只有为零才返回；超时抛错。
worker 在此返回后才允许父进程重开 normal 日志。单独调用旧 wait/close 仍不提供全组静默证明。
参数未提供环境/总内存门时保留原语原有调用行为；worker 强制提供这两项。
完整合同及最终测试记录见 `rq2_normal_worker_v1.md`；上述旧 source/test hash 是先前交付的历史记录。
