# 流式 normal 整任务控制器

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE。

`normal_task_controller_stream.py` 接入流式固定 worker、声明日志和有界归档捕获，
保留旧控制器的顺序、预算和失败保留语义。旧控制器、旧配置和已索引结果保持原字节。
它只接收小型声明与外部 pins；父进程不构造年度 assembly 或 assignment。

## 顺序与证据消费

持久化 controller intent 后，在挂起的受限 execute Job 中完成固定 worker 握手；
整 Job 静默、退出和 claim/completion 核验后，独立只读 capture 并保留当前 pins。
随后在新的 replay Job 中独立准备输入、进行零 solver 数值回放。静默后读取有界完整报告，
再次 capture 比较所有归档 pins，并复读报告核对身份和摘要。已有目录拒绝，不恢复或重试。

报告入口严格解析 `DeclaredNormalRecordReplay` 的完整 typed wire，再校验嵌套
`SourceRecordReplay` JSON 及 native replay JSON 的完整字段、标量类型、身份、调用数、
assignment/witness、数值测量、最优与不可行标志和权限字段。
两层报告均绑定同一个 record/result/replay identity。声明层 assignment/witness 必须与来源层
相等，来源错误必须完整投影到声明错误。最终三态为 accepted、unresolved、inconsistent。
三层 replay 错误只接受各自有限静态词表；native_metadata/assignment_replay 可携带非空
异常文本，仍只检查诊断形式，不认证异常实际发生。重复错误和重复异常阶段拒绝，
native 错误必须完整投影到来源层，来源错误再完整投影到声明层。
来源成功但声明末端失败可保持 unresolved；缺来源返回不能被当作 accepted。
旧报告 tag、未知字段、伪造成功摘要和类型混淆不能通过完整报告门。

completed 只表示开发诊断流程完成，不保证数值 accepted。
`whole_task_resources_verified`、`hard_disk_quota_enforced`、
`native_execution_authenticated`、`formal_result` 仍为 false。
合作式身份检查不防同权限恶意替换或绕过入口。

## 资源与失败

沿用 process/Job commit cap、阶段 deadline、host reserve、父进程 lifetime peak、
目录字节/entry 限制及两次完整 capture 预算。顺序 Job 的额外 commit 需求取最大值，
不相加。目录 logical bytes 与余量采样不是硬磁盘配额；同步 I/O 不由 Python deadline
硬实时抢占。最终 observation 文件仍是写入前验证快照，API 只有在写入后 deadline
通过时才返回 completed，不将快照存在当作完整返回证明。

保留 prepare、normal intent、normal result、replay prepare 四个真实父死亡测试窗口，
KILL_ON_JOB_CLOSE 后用已持有进程 HANDLE 确认测试子进程退出。失败留存已有意图、归档
和报告，停止后续阶段；非零退出、timeout、无返回均不推定数学不可行。

## 验证

主解释器与固定选项：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`。

- `tests/test_rq2_normal_task_controller_stream_v1.py`：61 passed in177.53s。
- `tests/test_rq2_normal_task_controller_stream_reports_v1.py`：19 passed in17.35s。
- `tests/test_audit_rq2_normal_task_stream_v1.py`：7 passed in2.47s，只读声明测试。

以上为首轮候选。pre-seal发现未知/重复错误及缺失native错误投影能通过降级报告门，
新增四类反例先明确复现4 failed,19 deselected in5.64s。补齐词表及投影后，报告全组
23 passed in19.96s；最终完整controller及runner联合68 passed in176.94s。
相关回归追加 `tests/test_rq2_normal_task_worker_stream_v1.py tests/test_rq2_normal_archive_capture_stream_v1.py tests/test_rq2_normal_task_process_v1.py tests/test_rq2_normal_resources_v1.py`：
134 passed in184.10s。该组不依赖本轮controller报告门改动。

真实 Windows Job 正例使用 tiny synthetic RTS loader、pair/window/package fixture，
执行完整 prepare/source/binder/kernel/journal，再在第二 Job 中禁用 solver 回放。
它不是公开来源数据观测，也不证明真实 H25 assignment 或全任务资源充分。

| 文件 | SHA256 |
|---|---|
| normal_task_controller_stream.py | 65dc01a87539b9a2f39fd77c12a3992551303b246d360997336ced27124a4be7 |
| test_rq2_normal_task_controller_stream_v1.py | 7b50fa956d87cfcaf44083b93174e61ee022e2ef35ac290afd03d88eb9c9f994 |
| test_rq2_normal_task_controller_stream_reports_v1.py | 2669bf8f9c9125056e6c05d29ac789fca3d438b6705bfde9c31fb038f34d4e37 |
| audit_rq2_normal_task_stream_v1.py | 67fce2d3a066f202e1d587e8f00e8d9551cc2fded7f1db624809ad3b0d114dce |
| test_audit_rq2_normal_task_stream_v1.py | 1e06eb35e5ca4e4b4958a3491e8ece54c5e6e0f30e0b86af2281ea3a770b64d2 |

## 真实 H25 开发声明

新 runner `audit_rq2_normal_task_stream_v1.py` 与
`configs/rq2_normal_task_stream_h25_development_v1.DRAFT.yaml` 绑定新实现和新目录，
保留旧 H25 开发预算：22275变量、28004约束、HiGHS 1.15.1、1线程、单次1秒，
execute/replay各240秒，Job/process各768 MiB，总任务600秒。
新 assembly/binding/source/binder pins 取自 SHA 已验证的完整流式 prepare 观测；
旧内容 reference 与新执行 pin 分离。声明生成不准备年度数据、不调用solver。

当前声明 SHA256：`58c700340c6ceb251d8a3405b5d466f8e493aad088888f83ed1f8ff40370c6f2`。
controller identity：`b733ae96a24d3d7c0ec73cfcda4e9381551a6d24c0934dffcb3133127fcaec80`。
独立 pre-seal 和相关回归完成后，该声明在新目录执行一次；真实运行的终态与证据见
`rq2_normal_task_stream_h25_development_v1.md`。流程完成，数值仍unresolved：1秒无解返回，
normal总耗时超过60秒门。后续不得修改本次已绑定代码/config或复用结果目录。
本规格与测试不构成 production seal、official review receipt、科学变更或正式运行权限。

独立只读R3 pre-seal最终报告门与完整双Job synthetic正例24 passed in37.29s，
runner声明门7 passed in1.98s。错误词表逐项比对及native→source→declared投影finding闭合，
最终源码/测试/config SHA及controller pin一致，无开放实质问题。
审查结论只覆盖本地未seal开发实现，不签发official receipt或正式运行权限。
