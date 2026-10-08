# 真实 H25 流式整任务开发验证

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE，数值结果 unresolved。

本次在新目录 `results/tables/rq2_normal_task_stream_h25_attempt1_non_authoritative` 执行一次
已声明的受限开发任务，未重试。旧冻结协议和结果保持原字节。
入口、预算及 pre-seal 验证见 `rq2_normal_task_controller_stream_v1.md`。

## 已观测事实

caller exit=0，controller API 返回 `completed_development_replay_diagnostic`，总耗时274.39秒。
caller exit来自调用端观测并在事后索引记录，没有独立caller process observation工件，
其证据强度低于两份持久化Job observation；API completed返回另见caller日志。
该状态表示开发流程完成，不代表取得可接受数值解。最终文件中
`validated_before_final_observation_write` 仍只是写入前快照；本次 API 返回另由caller日志保留。

| 观测 | execute Job | replay Job |
|---|---:|---:|
| PID | 7352 | 2940 |
| creation FILETIME | 134344510322658414 | 134344511848068234 |
| 耗时（秒） | 151.094 | 119.812 |
| 退出码 | 0 | 0 |
| 整Job静默 | true | true |
| process commit峰值（bytes） | 622563328 | 623521792 |
| Job总commit峰值（bytes） | 623742976 | 624693248 |
| 运行期采样次数 | 653 | 519 |

两阶段均未报告host reserve/API观测错误，Job峰值低于原805306368 bytes上限。
父进程lifetime peak working set为144953344 bytes。以上是本次开发路径的资源观测，
不是全策略/全场景资源保证；whole_task_resources_verified、硬盘配额和native execution
authentication字段仍false。

第一次与第二次捕获的全部pins相同。record为3819335 bytes，SHA256：
`ebe4ba6c5f715ce5ee5713813d9bbf780807ddf1ca7ded7356db3d7af79cec6a`。
result identity：`c3e71a067488ea349dd3bd6ae2998d503f213326d90414cecba7baf95cdbc68c`。
replay报告SHA256：`85aa72ed17b9ae617d0367c813bac09b926b2c21daf35e8b3908d653d4662a1a`。
本次只读提取另核payload摘要和encoded result identity，未重跑数值计算。

独立replay为 `replayed_unresolved_declared_normal_record`，archive_consistent=true、errors为空，
solver_calls_by_replay=0；accepted_record_reproduced、assignment_recomputed、
normal_witness_reproduced均false。`complete_native_record`仅指返回记录完整，不能当作完整可行解。

## 两个仍开放的数值缺口

原生求解实际调用一次，solution_count=0，状态为aborted/maxTimeLimit；
objective和upper为null，lower=0.0。optimal、assignment_valid、native_infeasible均false。
没有可交给current/episode的有效normal assignment或terminal witness；这不是数学不可行证据。

normal结果还记录 `observed_wall_time_exceeds_budget`：总耗时67.5576574秒超过既定60秒门。
preflight为33.6408526秒，solve/load/canonical pipeline为27.3536661秒，
normal witness audit为0秒；两次nested builder为6.75423和6.8464579秒。
preparation另耗31.3762977秒，source wrapper另记录113.8775376秒。
这些计时层级有嵌套关系，不能直接全部相加。
normal lifetime peak由585658368增至640892928 bytes，core payload为4074529 bytes，
本次未记录这些门超限。

下一必要工作是定位normal preflight/pipeline及末端检查的实际开销，保持内容、模型、
数值和身份复核不变量；随后解决受限求解下有效assignment获取。不能靠删除复核或提高
接受阈值把本次记录变成accepted。已有执行的代码、声明和结果已建立绑定，后续实现或
预算变化须用明确后继和新目录，不改写本次工件。

## 来源与推断边界

本次使用完整8784小时公开RTS-GMLC来源重建H25输入，不再替换loader为synthetic fixture。
全关机/零发电初态及业务功率映射继续属于显式机制参数；observed_power_mapping=false。
本次没有产生业务可交付容量、四臂优劣、工程安全、恢复尾部履约或经验风险结论。
右删失、风险分母、科学注册和正式启动门继续开放。

证据索引：`results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_task_attempt1_evidence.json`，
绑定54项文件的bytes/SHA，索引SHA256：
`4f5c61bc8f4ebfa615448cfbbb29c45ae25409e8d290c8583847ae9aff001f1c`。
日志：`results/logs/rq2_normal_task_stream_h25_attempt1_non_authoritative.log`。
本记录不是production seal、official review receipt或正式实验结果。

独立只读核验：54项bytes/SHA全部一致，总4248161 bytes；21项request/intent/supervision/
launch/claim/completion/报告/归档交叉检查通过。SQLite只读核对原始三层状态、native终止、
calls/solution_count、payload摘要及result identity与上述记录一致。未重跑prepare、solver
或数值replay；无实质矛盾。计时粒度不足以确定具体性能机制的限制保留。
