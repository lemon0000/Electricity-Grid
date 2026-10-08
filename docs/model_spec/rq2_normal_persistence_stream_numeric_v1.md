# Numeric normal 日志、回放、归档与固定 worker

2026-09-27，DRAFT_NONAUTHORITATIVE。连接已验证的 numeric normal 模型/kernel/source/declared 层，为完整 H25 开发任务提供独立归档与零 solver replay。旧 fast 文件、数据库和结果保持。

新增 `normal_declared_store_stream_numeric`、`normal_declared_replay_stream_numeric`、`normal_archive_capture_stream_numeric`、`normal_task_worker_stream_numeric`。只更新引用、schema 和 owned 类型；新 SQLite application ID 为 `0x4e4e5331`。旧 stream/fast archive 不作为新 schema 读取，旧三层 result tag 即使一致改写外部摘要也须拒绝。

保留 intent 先于 prepare、一次调用、意图未返回时调用数未知且不可重试、current head 独立持有、只读三层数值重放、opaque 有界 capture、固定 argv/environment/cwd/PID/FILETIME，以及 prepare 后 source 前运行态回调。replay 不调用 solver，capture 不装配年度输入，不恢复可执行 cursor。所有正式认证、恢复授权与整任务资源认证保持 false。

验证包含完整持久化/回放回归、真实进程竞争与退出窗口、capture 路径/schema/预算边界、worker prepare 后上下文漂移；新增 fast application ID、fast 三层 tag、fast replay pin、capture 双向读取隔离与旧 fast worker request type 反例。验证终态及独立审查见下文；本规格的组件测试均使用 tiny 来源。

## 本轮验证

命令前缀 `D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`。`tests/test_rq2_normal_archive_capture_stream_numeric_v1.py tests/test_rq2_normal_task_worker_stream_numeric_v1.py` 最终 71 passed in 243.34s，exit 0。独立差分审查及 zero-solver replay、tiny execute→capture→replay、隔离反例等 17 passed in 104.86s。该独立窄测完成时 store/replay 全组尚待终态，后续结果如下；本组件不作为正式 gate 证据。

store/replay 最终命令文件集为 `tests/test_rq2_normal_declared_store_stream_numeric_v1.py tests/test_rq2_normal_declared_replay_stream_numeric_v1.py`，118 passed in 754.68s，exit 0。两组完整终态均已取得，独立审查等待的回归条件已满足；无源码变更、无开放实质 finding。本次仍为开发核验，不产生 official verdict、receipt 或正式门证据。

| 文件 | SHA256 |
|---|---|
| normal_declared_store_stream_numeric.py | `17bc1430d0c1953e3ace727e0e3140d854c0cd29fb5de59e531539c74e2cad92` |
| normal_declared_replay_stream_numeric.py | `862c4431f526546a2e59055282964916a4b8c95872331a7497d44351988d7fa1` |
| normal_archive_capture_stream_numeric.py | `42323985331299409d78c7c76868b6a07fcfff22c89e9b4c5f59b4fea8b7229b` |
| normal_task_worker_stream_numeric.py | `de503cff11ea58d031cf22a1c5ab0e2b6d2bce815a506c5b028b331829f5c874` |
| test_rq2_normal_declared_store_stream_numeric_v1.py | `01752d6337999ef4051c9013a27c7b6e9fa90ae828c2a4db914a0428392edaee` |
| test_rq2_normal_declared_replay_stream_numeric_v1.py | `661502815525f76cf4a300a908a7a1465a6c61b380db3c553847d9cd56afe340` |
| test_rq2_normal_archive_capture_stream_numeric_v1.py | `83499c18d2231698c0af9008be3ee1f8bdadbffe07dd16b0fcac0613992a21e1` |
| test_rq2_normal_task_worker_stream_numeric_v1.py | `9988c28d3fed305cd9de603227d0cd6dae06cc1424e17882b16925d8782f95c3` |

源码目录为 `src/rq2_joint_deliverability_boundary_v1`，测试为 `tests`。
