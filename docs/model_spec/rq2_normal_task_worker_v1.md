# Normal compact task worker v1

状态：DRAFT_NONAUTHORITATIVE。已实现小型请求和固定 execute/replay worker 入口；完整 phase controller 尚未实现。本模块不启动子进程，不确认 Job 静默，不分配资源预算，不发布正式结果。

## 请求与身份

NormalTaskRequest 仅含 NormalTaskSourceRequest、source request pin、solver specification、原 NormalExecutionBudget、normal/source-execution/replay pins 与两个完整归档字节门。没有 assembly、assignment、terminal carry 或执行游标。来源准备仍调用原 prepare_task_inputs。

Codec 使用精确 dataclass 字段 inventory、递归构造四种输入类型及 canonical JSON byte roundtrip。Python JSON 保留 int、float 和 bool 区别，identity 直接绑定 canonical bytes；不以 Python 数值相等代替 wire 相等。旧 worker 的类型 allowlist 不扩展。请求及完整 phase packet 各受 64 KiB 门；record/replay payload 门分别显式声明，上限 256 MiB。

task_identity 在 claim 前检查 source preparation、normal execution 与 replay pins，绑定请求、实际输入/重放/归档/旧 codec/进程/lease 模块路径与字节、自己的字节，以及 Python 可执行文件路径与字节。source execution identity 依赖 PairDeclaration，在子进程完成来源准备后、创建 store 或 replay 之前重新计算。

phase packet 绑定 root、phase、request、task identity、显式环境和 replay pins。execute 的 replay_pins 必须为 None；replay 必须给出完整 store/current head/record SHA/result claim 四字段 pins，具体 current head 语义由旧 replay_normal_store 验证。返回的 packet bytes 不加载来源文件或模型。

## Controller 前置与一次性入口

Controller 尚待实现；以下是 worker 必须验证的前置，而非它自己事后补写：
1. 在 non_authoritative root 写 packet 与 phase intent，并 fsync/readback。
2. 创建挂起的受限 Job child。
3. 在 release 前写 launch，绑定 packet/task identity、PID、creation FILETIME、argv hash、root/scratch dev+ino，再 readback。
4. Release 后，worker 校验上述文件才写 exclusive claim。

固定 argv 为隔离 Python 的固定模块入口加 packet path/digest。worker 用当前进程 pseudo-HANDLE 实测 creation FILETIME，并核实际 PID、sys.orig_argv、cwd 和完整 os.environ。cwd/TEMP/TMP 必须同指 phase 专用目录；这只证明路径声明一致，目录排他、磁盘限制及父死亡仍由 controller/Job 保证。

读取 packet/intent/launch 均 canonical、有界、single-link，并保留身份。claim 使用 xb、fsync、readback；任何残留 claim 均禁止重复进入来源准备。发生错误时保留 intent/claim/归档，直接传播原异常，不尝试可能掩盖原错误的二次诊断写入。缺 claim 或缺 completion 不证明原生调用次数，controller 必须保留已有 intent 的 unresolved 状态。

## 两阶段行为

Execute：重新 prepare 来源，核 source execution pin 和 phase 文件，创建固定位置 normal_non_authoritative 的原 DevelopmentNormalStore，调用一次 execute。原 store 提交并重新读取完整结果后，worker 才写小 completion；其中 store/head/record/result identity 均为供 controller 核验的声明。

Replay：从同一请求重新 prepare，不传递 assembly。调用原 replay_normal_store，以独立保留的 current head、record SHA、result claim 核输入及数值，并额外核 store identity。完整 canonical replay 诊断先通过 max_replay_bytes 门并 write/fsync/readback，然后才写小 completion，绑定诊断摘要、字节数及诊断状态。

两阶段 completion 都包含原 packet/task/launch 身份，并明确 numerical_acceptance_by_controller=false、formal_result=false。controller 必须在 Job 静默后独立检查小文件与完整诊断；不能凭零退出或子进程成功字符串接受结果。完整诊断已写但 completion 丢失时仍不得自动重试。

来源准备之后、结果写入之前及完成之前都检查 phase 文件与 root/scratch identity、实现身份，同时重新核 cwd、完整 os.environ、sys.orig_argv、PID 和 creation FILETIME。准备期间的运行上下文漂移会在创建 store/replay 前被拒绝。依赖旧合作式本地文件合同，不防同权限恶意 ABA、伪造内容或绕过函数；单个 worker 不提供跨进程排他或完整资源保证。

## 验证边界

大多数测试用显式 tiny 来源 stub，模拟 controller 的运行上下文：execute→有界 capture→独立 replay，replay 禁止 solver；测试 claim 重复、环境/argv/PID/FILETIME/path/intent 漂移、prepare 中断、source pin、fsync、归档门及 completion 丢失。

另有真实固定 argv 的挂起 Job 子进程测试：controller 测试代码先写 intent、创建挂起 child、写真实 PID/FILETIME launch、release；在固定的缺失来源请求下，观察到 worker 写 claim、非零退出、没有 normal store/completion，以及整个 Job 静默。它证明固定 worker 与进程监督的失败连接，不将退出码解释为特定故障认证，不证明真实来源正例或 RTS 数值结果。未运行真实 RTS 求解或正式实验。

后继必须实现外层 lease、私有 scratch、phase 顺序、父进程及两 Job 预算、停止后的独立 capture/诊断验收，以及准备/normal intent/result/replay intent 各父死亡、写满/SQLite/fsync 故障窗口。


## 开发验证记录（2026-09-20）

相关回归命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_task_worker_v1.py tests/test_rq2_normal_task_inputs_v1.py tests/test_rq2_normal_worker_v1.py -k "not real_pinned_h25"`，81 passed, 1 deselected in 170.68s。随后按独立 finding 补运行上下文 postcheck 和三个准备期漂移反例；最终 targeted 同解释器/选项、仅 task_worker 文件，26 passed in 78.71s。

真实入口测试的初始 1 GiB Job 追加需求被 host commit 准入拒绝，当时只读观察 available=(9024681-8817483)*4096=848683008 bytes，未创建子进程。将这个仅缺失来源的短测试上限收紧到 process 256 MiB/Job 384 MiB，保留真实 observer 与 32 MiB reserve 后，单独 1 passed, 22 deselected in 10.71s；后续完整 targeted 和相关回归均覆盖该预算。没有放松旧 kernel 或正式预算，也不由此推断真实模型资源充足。

最终 source SHA256：`adcb8d7be6e1aa3ccd56ea641399d0c96525c8d4a4be5b23ed46e59e99bcfad0`；test SHA256：`e430f0cc35d80c1a0d995350730a07a19ed63ffbdda8c147e0e00a1c8db98ab9`。六个复用模块 normal_task_inputs/normal_task_process/normal_archive_capture/normal_store/normal_replay/normal_worker 字节保持。独立最终结果另记。


独立最终 targeted：26 passed in 76.31s，source/test hashes 与上列一致；准备后运行上下文 finding 已闭合，限定 worker/packet 范围无开放实质 finding。该复核不构成 official verdict、seal 或正式运行授权。计划、blocker、正式准备记录和规模执行合同已同步；最终 diff/UTF-8/whitespace 与无残留测试进程检查通过。
