# Normal 任务进程监督原语 v1

状态：DRAFT_NONAUTHORITATIVE。`NormalTaskChild` 只管理一个任务子进程及其 Job，
尚未接入 compact task packet、阶段日志、normal execution、归档 pin 捕获或独立 replay。
不会因进程零退出而接受数值结果，也不生成正式运行授权。

## 所有权与复用

以 composition 复用原 `normal_process.DevelopmentNormalChild` 的创建时 JOB_LIST、
挂起创建、KILL_ON_JOB_CLOSE、非继承 HANDLE、process/Job commit 限额及 quiesce。
旧文件、`wait(max_elapsed_seconds<=60)` 及其调用者保持原义。
新层不调用旧 wait，只对已保留的 process HANDLE 短轮询；不按 PID 重新取得控制权。
旧 private ABI 的实际路径与字节纳入新 identity，变动必须重新审查。

wrapper 先保存预分配的 inner owner，再显式调用 base constructor，避免 base 已取得 HANDLE、
但 wrapper 尚未完成赋值时异步中断导致泄漏。Base 的 `_owner` 设置早于任何 native handle acquisition；
早期校验失败可清空尚无 owner 的对象，已设 owner 的失败必须走原 close 回收。
创建线程/PID 检查、单次 release、单次 wait、禁止 copy/deepcopy/序列化均保持。
唯一公开创建入口为 `normal_task_child(...)` contextmanager；直接构造 `NormalTaskChild` 拒绝。
factory 调用本身不取得 HANDLE；进入 context 后，在 generator 的 try/finally 内预分配 owner、
初始化并 yield，finally 负责 close。初始化完成但尚未交给调用者的中断也有清理路径；
close 容忍尚未设置第一个字段的 owner。调用方必须用 with 管理生命周期；测试中的
丢弃 entered manager 回收只验证当前 Python 的 generator finalization，不是跨运行时及时回收保证。
未调用 wait 的 context 退出以 kill-on-close 清理，不产生静默报告。

## 独立预算与身份

`TaskProcessBudget` 明确 max_elapsed_seconds、sample_interval_seconds、process/Job commit bytes、
max_quiescence_seconds。开发入口上限分别为 3600 秒、1 秒、5 秒；数值须有限且正，
字节须 exact positive int，Job cap 至少覆盖 process cap。
3600 秒是新任务原语的操作上限，不是原 solver/worker 阈值放宽，也不构成长任务或正式运行授权。
本轮测试仅运行短子进程；超过 60 秒的路径以注入 elapsed offset 验证。

`task_process_identity` 绑定 argv、可执行文件路径及内容、cwd、显式 environment、TaskProcessBudget、
外部 host resource identity、本模块及实际 process/resources/local 模块路径与内容。
host identity 已绑定完整 HostResourceBudget、目录 dev/ino、卷 GUID 和资源观测实现。
cwd/TEMP/TMP 必须指向同一现有显式目录，并被 host disk demand 覆盖；host additional commit
至少覆盖 Job cap。此检查不能代替 controller 自身内存预算或证明目录已经排他/私有。
后继 controller 仍须创建并持有专用 scratch 身份和 outer lease。

argv 的绑定不认证其引用的任意 script 内容；固定任务入口/packet/模型来源须由上层另行绑定。
所有检查采用合作进程和磁盘实现假设，不认证运行时 monkeypatch、token impersonation 或恶意 ABA。

## 准入与运行观察

创建子进程前固定调用 `normal_resources.observe_headroom`，要求 additional+reserve 足够。
创建已经消耗一部分资源，因此 release 前和运行中只对同一固定 observer 的原始测量比较 reserve：
commit available 不小于 commit reserve，各卷 caller available 不小于该卷合并 reserve。
不使用运行时报告中的 `observed_headroom_sufficient` 或追加需求错误决定停止，避免重复计入已分配资源。
没有公开 observer callable 或 caller-supplied observation 接口。

运行采样保存成功样本数、commit 和各卷 caller available 的低水位、最后储备错误及受限异常类型名。
每次采样重新检查目录、卷、资源与进程实现身份；采样失败停止，不填补虚构测量。
运行储备检查不保证未来剩余计划仍可分配，也不持有系统资源预留。

## 退出、停止与竞态

计时起点位于 wrapper 构造开始，覆盖准入、创建、挂起等待、release 与轮询。
超过 deadline 时保守停止；同步 OS/资源 API 本身不能由这层抢占，故这不是硬实时 wall-clock 保证。
release 后调用方须立即进入 wait；本原语没有后台 watchdog，未进入 wait 期间不会自主轮询。
sample_interval_seconds 是两轮之间的 HANDLE wait 上限，不含本轮同步采样开销，不能声称实际样本间隔严格不超过它。
采样轮的主原因优先级为 deadline、observation failure、reserve breach、direct child exit；
同时观测到的 resource/exit/deadline marker 保留。退出后仍进行一次资源/身份观察；
不能用“已退出且 code=0”掩盖终端资源检查失败。

所有正常返回都先调用整个 Job 的 quiesce，再确认直接子进程 HANDLE 已 signaled。
真实故障测试发现 ActiveProcesses==0 可能先于 HANDLE 信号，因此两步共用同一清理 deadline，
不能把第一步单独当作两项都已完成。之后在 Job HANDLE 仍打开时查询 process peak 与 Job aggregate peak。
自然退出时也终止残留后代。静默、HANDLE、peak query 失败均抛错；不会返回 quiet=true 的诊断。
BaseException 重抛并 close Job；close 的 kill-on-close 不等于本次已经确认整个 Job 静默。
后检身份失败保留停止原因或改为 post_process_identity_failed，不升级为成功。

`TaskProcessObservation` 是进程诊断，不是执行 capability。whole_job_quiescent 只描述这次
确认结果；job_commit_limits_configured 不证明某次退出由内存限制触发。
hard_disk_quota_enforced、whole_task_resources_verified、numerical_evidence_verified、formal_result 均 false。
报告没有 solver 调用数推断，deadline/资源失败均不能解释为数学不可行。
后继仍须在 release 前持久化 phase intent/launch 身份，并在正常 wait 返回后核查结果工件。
磁盘采样是观察式停止，不能阻止采样间写满磁盘；SQLite/native/日志写失败的保留规则尚待接线。

## 验证范围

真实短进程覆盖自然/非零退出相关路径、储备不足、API/身份失败、deadline、终端竞态、
残留后代静默、BaseException/静默和peak查询失败、跨线程、父进程突然退出、构造中断窗口。
两个各分配 16 MiB 的同时存活成员验证 Job aggregate peak 大于单进程 peak。
初始与运行余量边界由明确低层观测 stub 注入；父死亡例使用真实只读 host observer。
没有 solver、真实 H25 运行或正式任务启动；没有磁盘压力/真实 quota 验证。


## 2026-09-20 Task process 最终候选验证

公开入口 normal_task_child 使用 contextmanager，使初始化与 owner 交接处于 finally 清理范围；NormalTaskChild 直接构造拒绝。新增初始化前后中断、factory 惰性及 entered manager 回收测试。主线程 targeted 34 passed in 6.78s；task process/process/resources 相关回归 97 passed in 7.81s。

命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_task_process_v1.py tests/test_rq2_normal_process_v1.py tests/test_rq2_normal_resources_v1.py`；targeted 使用其中第一个测试文件。

source SHA256：`c7c46c08297c083338cc555a887313a94cb9e767480709caa205011b6e4d080c`；test SHA256：`58ff916bc49d75ba828b96ce8c64e1ad404ef0479c0903403b9f309233f64c54`。旧 normal_process SHA256 保持 `ffc487c05c72d00a7c2e8d7515a29f16a3d0c8ac3f0efa6cdba36bbcea34d44f`。独立最终复核另记；此处仅为开发候选证据。


独立最终 targeted：34 passed in 5.91s；上述 source/test bytes 不变。限定范围 pre-seal findings 已闭合，不构成 official verdict、seal 或正式运行授权。计划、blocker register 与正式实验准备记录同步；后继为有界归档 pin 捕获及 execution/replay 任务连接。

## 2026-09-28 嵌套Job复用验证

新增两项短测试覆盖inner所属outer Job及持有HANDLE的退出核验，正常完成和外层deadline终止均通过；所有相关36项通过（8.91秒、exit0）。独立限定pre-seal未见实质finding。仅测试文件增补，旧source与cap不变；原test SHA为历史版本，本次完整资源边界和测试专用内存诊断见rq2_execution_resource_contract_v1.md末尾。未形成whole-episode资源认证或正式运行授权。
