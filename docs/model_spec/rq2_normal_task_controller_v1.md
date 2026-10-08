# Normal 整任务顺序控制器开发规格

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE。限定本地开发任务，不生成 seal、official review receipt 或正式运行权限。

## 输入与顺序

`normal_task_controller.supervise_normal_task` 接收固定 worker 的小型 typed request、独立 controller identity、显式 environment 和 typed budgets。先拒绝未知嵌套类型和回调对象，再经 plain wire 复制声明；父进程不构造 assembly 或赋值。保留旧 numerical kernel、store、worker、process、replay 的接口和限制。

新目录必须以 `_non_authoritative` 结尾；外层合作式 lease 排他占用。已有目录一律拒绝，包括失败与部分完成目录。分别创建 execute/replay 专用 scratch，cwd/TEMP/TMP 一致，记录目录身份。过程顺序为：

1. 预存 controller request/intent，再写 execute request/intent/supervision。
2. 创建挂起的受限 Job，保存实际 PID、creation FILETIME、argv 与目录身份，然后 release。
3. 核验确切进程观测类型、身份、退出、整 Job 静默及权限字段，再核 claim/completion。
4. 用独立有界 capture 取得 opaque archive pins，持久保存 supervision 与 retained pins。
5. 独立 replay Job 从同一小型声明重新 prepare，重建输入并执行原 numerical replay；不运行 solver。
6. replay Job 静默后，读取完整有界报告，检查 canonical 字段、类型、身份、嵌套诊断和三态一致性。
7. 第二次 capture 使用相同完整预算，要求全部 archive pins 与第一次相同；随后再有界复读报告。

两次 capture 均保留实际预算、输入 pins 和 capture identity。capture 的 result identity 是待重放核验的声明；capture 本身不证明数值正确或 Job 静默。小 completion、零退出和子进程成功字符串均不能独立成为结果验收。

## 资源与时间语义

初始额外 commit 需求为两阶段 Job cap 的最大值加父进程独立余量；顺序阶段不相加。运行期采样只检查 reserve。每阶段记录实际时间预算与 host demand，预留后续 Job、两次 capture、静默和父侧尾部时间；不足时停止推进。

Job 配置 process/Job commit 限制。父侧 lifetime peak working set 是当前父进程整个生命周期的观测，不是本任务独占内存，不是硬 RAM 上限。目录流式扫描有 entry、单文件和每区域 logical-byte 上限；拒绝 reparse、硬链接及非预期归档文件。磁盘余量采样、logical bytes 与 payload gate 均不是硬物理磁盘配额。

总 elapsed 在阶段与读取/写入边界检查；同步 I/O 不可被这些检查硬实时抢占。最终文件只保留写入前验证快照，成功快照状态为 `validated_before_final_observation_write`；其 elapsed 和 `pre_final_observation_task_logical_bytes` 截止于最终文件写入之前。只有最终 write/fsync/readback 后 deadline 仍通过，API 才正常返回 `completed_development_replay_diagnostic`。快照存在不证明最终写入后检查或函数返回已完成，也不提供恢复权限。

## 结果与失败语义

API 的 completed 仅表示开发诊断流程完成。报告另保留 `replayed_accepted_normal_record`、`replayed_unresolved_normal_record` 或 `inconsistent_normal_record`，以及 errors 和 `accepted_record_reproduced`。这个布尔值描述原 accepted 记录是否被重放复现，不代表新的 native execution 认证。

任何进程、来源、工件、预算或一致性失败都停止后续阶段；保留已有 intent/claim/store/report，不重试，不由缺失记录或退出码推断数学不可行。失败诊断写入也失败时传播原异常；KeyboardInterrupt 等中断通过 context/finally 关闭 Job/lease。父死亡依赖已有 KILL_ON_JOB_CLOSE；关闭句柄本身不作为已静默证明。

`whole_task_resources_verified`、`hard_disk_quota_enforced`、`native_execution_authenticated`、`formal_result` 始终为 false。合作式本地文件与代码身份检查不防同权限恶意伪造、ABA 或绕过入口。

## 验证边界与后继

正例使用明确 tiny synthetic 来源引导，执行两个真实 Windows Job，独立 replay 禁止 solver。另保留未经引导修改的固定入口缺失来源负例。父死亡覆盖 prepare、normal intent、normal result 和 replay prepare 四个窗口。伪造观测/摘要/报告、归档漂移、写入失败与 deadline 反例属于故障注入，不是真实公共数据观测。

真实公开 RTS 来源准备已有独立开发证据；本控制器尚不提供真实 H25 求解正例或全四臂资源证据。后继需完成真实来源 normal 的受限端到端验证及 normal witness 到 current/episode 输入的时序交接，保持 terminal carry 与 incoming origin 区分。完整 UID selectors、四臂固定策略、恢复尾部/右删失、风险分母和科学注册/正式启动门继续开放。

## 开发验证记录

解释器与固定选项：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`。

初稿 controller targeted 为 26 passed in 131.99s；补类型/身份/两次 capture/篡改和 deadline 故障后为 56 passed in 204.97s。

相关回归命令追加以下文件：`tests/test_rq2_normal_task_controller_v1.py tests/test_rq2_normal_task_worker_v1.py tests/test_rq2_normal_archive_capture_v1.py tests/test_rq2_normal_task_process_v1.py tests/test_rq2_normal_resources_v1.py`，结果 186 passed in 289.44s。这次 controller source/test SHA256 分别为 `7636fbf067fc294c6cd9b9caf16755b9bb476f67e012eabc6ef1868ff061fd80` / `52840face639475d1b5fc7269a8b54ee8884ae6afcb10a850da49569a2895566`。

随后只修改最终 elapsed 判定和返回记录使用同一时钟读值，补跨界时钟反例。最终定向命令追加 `tests/test_rq2_normal_task_controller_v1.py -k "deadlines_and_retained_write_failure or two_real_jobs"`：5 passed, 56 deselected in 27.79s。第一次定向复测曾出现 3 failed, 2 passed, 56 deselected，均失败于实时 host headroom 初始准入；未进入对应故障路径。确认无残留测试进程，后续只读 commit available 为 `(10083966-9733951)*4096=1433661440` bytes，同预算重跑通过。没有降低 reserve 或替换真实 observer；不能由此推断真实规模资源充足。

最终 source SHA256：`071c4a2c6832fa6db3c50618df0d44ac5e3084aca335422abea550f4edb26ce3`；test SHA256：`751fe213b200d327c736c7a4fbb634b958a94a21ccb3039d239ad171f321d927`。

normal_task_worker、normal_task_process、normal_archive_capture、normal_task_inputs、normal_process、normal_store、normal_replay、episode_store 八个复用源码哈希保持。公共数据交付包 summary 的六个 output bindings 与复合诊断包七个文件的 bytes/SHA 核验一致。


独立最终 targeted：61 passed in 133.65s，source/test hashes 与上列一致。限定 controller 范围 pre-seal findings 已闭合，未发现剩余实质 finding；不是 official verdict、seal、receipt 或正式运行授权。独立复核时规格 SHA256 为 `6d07bd68346ff56da27d18f534ef66b547f843d213913d6b72d355c0c87deaa6`，此后仅追加本验证记录。
