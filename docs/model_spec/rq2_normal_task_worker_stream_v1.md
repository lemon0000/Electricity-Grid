# 流式声明固定任务 worker

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE。

`normal_task_worker_stream.py` 是旧固定 worker 的显式流式后继，旧 worker、controller、
冻结配置和诊断结果保持原字节。当前连接范围为 compact request → execute journal →
opaque capture → 独立 replay；完整顺序 controller 仍待接入。

## 请求与运行边界

`StreamingNormalTaskRequest` 明确携带旧来源内容 reference 与独立的新
request/assembly/binding/source implementation/binder implementation/kernel/source execution/
declared execution/replay pins。小型请求与 phase packet 都有 64 KiB 上限；
身份计算不准备年度数据、不构建模型、不求解。schema 与固定子进程导入路径区别于旧 worker。

worker 核对 cwd、environment、argv、PID/creation time、根目录和 scratch 身份，以及
controller 预存的 intent/launch，独占持久写入 claim 后才进入任务。execute 分支创建声明日志，
在日志 intent COMMIT/readback 后才准备输入；准备及声明/pin 复核后，进入 source 求解前
再次运行固定 postcheck。之后保留原有末端复核与 completion 写入。

为提供该位置，两个尚未 seal 的 draft 模块
`normal_declared_execution_stream.py` 与 `normal_declared_store_stream.py` 增加
可选关键字 `before_source`。它只用于调用者提供的运行态检查，不进入持久化 header/result，
不替代任何输入、数值或身份门，也不作为认证证据。固定 worker 始终传入自己的 postcheck，
其实现由 task identity 绑定。此检查异常在 source-return 捕获范围之外传播；日志保留
unresolved intent，不写返回结果，不自动重试。非 callable 在消耗 intent 前拒绝。
模块源码变化自然改变声明执行、journal、replay 和 task 身份；以前的 draft pins 不授权新实现。

replay 分支从相同独立 pinned request 重建输入，要求独立 current head/record/result pins，
复核捕获的 store identity，再写完整三层诊断报告。外层 completion 只记录报告摘要和状态，
不得代替未来 controller 对完整报告的检查。

## 验收范围

tiny synthetic source 测试覆盖完整 execute/capture/solver-forbidden replay、精确类型和 pin、
claim 前九类漂移、prepare 中 packet/cwd/environment/argv/intent/launch/claim 漂移、
检查失败后 source 调用为零及日志禁止重试、prepare/中断/fsync/输出预算/写入故障。
另有真实 suspended Windows Job 测试，仅证明固定进程握手到来源重建失败路径；
子进程没有 synthetic loader，不能将该负例当作真实来源执行正例。

真实 H25 观测仍止于完整流式 prepare；本模块没有提供真实 H25 assignment、两 Job
完整资源证明、current/四臂或恢复末端可履约认证。机制初态和工作负载功率映射继续明确标注。
科学注册、右删失、风险分母及正式启动门保持开放。

## 验证记录

首轮 worker 26 passed in104.55s；之后增加三项运行态漂移及明确的 source 零调用/日志断言。
最终相关回归和独立 pre-seal 结论另行记录，首轮结果不代替最终候选验证。

相关回归命令：
`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_task_worker_stream_v1.py tests/test_rq2_normal_declared_execution_stream_v1.py tests/test_rq2_normal_declared_store_stream_v1.py tests/test_rq2_normal_archive_capture_stream_v1.py`。
结果118 passed、6 failed in350.59s；六项均为新增测试重开日志时漏传 required expected_head，
漂移拒绝与 source 零调用断言此前已通过。测试改为执行前保留独立 head 后，
同解释器/pytest参数运行 worker 文件 `-k runtime_changed`：6 passed,23 deselected in34.46s。
此为分批验证，不声称最终124项整组重跑。

同解释器/pytest参数运行 `tests/test_rq2_normal_declared_replay_stream_v1.py -k "owned_record or missing_source_return or post_declaration_failure or fabricated_declared_rejection"`：
8 passed,72 deselected in56.81s。覆盖正常完整回放、缺失返回、历史末端拒绝和伪造拒绝。

当前 SHA256：

| 文件 | SHA256 |
|---|---|
| normal_task_worker_stream.py | b7c4c900b0dbdf6745070fe44a06fa80751de36b174beee3b3cdc9020ec5ae92 |
| normal_declared_execution_stream.py | 5c926d631a0b179f8cf5e50d851e0cc849b03fdbb5e6a97a3977a27d66d75b23 |
| normal_declared_store_stream.py | d848e264210f56a1ce98782aa57d058208f10555b7f9e71534965c9c185ec0a0 |
| test_rq2_normal_task_worker_stream_v1.py | b71f76f66634994b3765a0c8fe75f86c502086eda46db837fdf237a9a0501d24 |
| test_rq2_normal_declared_store_stream_v1.py | 55445912ad0fc8dc3dfd4ae6484375b05e529a0d1f4a04f51352eaefb170160a |

旧五批74项索引工件bytes/SHA一致，旧worker/controller SHA保持原值；`git diff --check`无错误。
这些为未seal开发记录，不构成official verdict/receipt或formal-run authority。

独立只读R3 pre-seal审查最终worker全组29 passed in125.44s，journal callback定向2 passed,26 deselected in6.39s；最终源码/测试SHA一致，无开放实质finding。该结论不认证Job membership、整Job静默或资源上限；controller接入和真实H25全链仍待完成。未生成official verdict/receipt或运行授权。
