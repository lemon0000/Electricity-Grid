# Normal 与双向容量 episode 的版本化绑定

2026-09-29，DRAFT_NONAUTHORITATIVE。本组件属于已授权双向容量接入的 R3 开发，
不依赖待批准的 CFE 映射 A，也不注册有限登记的参数与按需停止合同。

四模块 `normal_bidirectional_episode_{binding,transport,worker,controller}` 显式使用
`scale_episode_bidirectional` 家族。相对旧 normal bridge，仅版本化 import、schema 与 owner 类型；
旧 normal 数值验收仍由已封存 `normal_numerical_execution_v2` 提供，门槛不传播到 planner 或 selector。
旧桥接、旧业务策略及旧结果保持。输入必须通过新 EpisodeInputs 与 BidirectionalPolicyCursor 的
精确类型门，独立 schema、内容 hash 和传递 implementation identity 防止旧新混接。

绑定侧独立重放 normal 归档，要求已接受的完整计划；逐小时重建信息、source pair、来源审计、
reference/actual 初态及 selector identity。完整资源计划必须相同。单独 normal diagnostic
不能授予 episode 依赖；unknown normal 拒绝。审计禁止 solver 与 episode 执行。

持久输入同时携带 normal 与 episode bytes 及外部 pins。execute、audit 和 parent 独立复核
来源、实现和绑定报告，复用既有 Job、one-shot、lease 与完整资源预留。输出与来源隔离，
子进程 release 前及最后发布前检查来源漂移。合成测试注入来源，不声称真实正式实验已运行。

## 验收矩阵

| 行为 | 新测试文件（统一前缀 test_rq2_normal_bidirectional_episode） |
|---|---|
| 完整 normal、source pair、小时、初态、selector 与资源计划绑定；允许覆盖子窗 | binding_v1.py |
| 未决 normal、无依赖 diagnostic、执行 guard、声明漂移拒绝 | binding_guards_v1.py |
| 新 wire/typed packet roundtrip，错 pin、旧 schema/type 及 source snapshot | transport_v1.py |
| 直接和间接来源必须全部列入 pins，路径与输出隔离 | source_inventory_v1.py |
| 真实短合成 execute→独立 audit→parent，回放零 solver，one-shot | pipeline_v1.py |
| durable launch 后漂移不 release；伪造绑定回执拒绝 | pipeline_failures_v1.py |
| 旧新 BoundEpisodeInputs/type/schema 互拒，依赖身份向 binding/transport/worker 传播 | isolation_v1.py |

通过状态由开发结果及只读 pre-seal findings 记录，不由此矩阵推定。
本次只验证显式固定窗口；episode 需被完整 normal horizon 覆盖，整段 source pair 仍与 normal 对应。
E 内策略与缺尾时按需 follow-up 的 normal 信息安排仍是科学合同阻塞。
完整培训支持的因果容量、holdout 绑定及正式运行均不由该桥接的小例证明。

## 开发验证记录

六文件批次23项通过812.71秒，追加隔离与身份依赖5项通过2.42秒；均使用指定compute Python、
`-B -m pytest -q -p no:cacheprovider`。规格与实际文件hash、完整命令及只读预审结果
记录在 `results/tables/rq2_normal_bidirectional_episode_v1_non_authoritative/`。
当前仍为未封存DRAFT，正常路径和故障注入验证不构成正式科学合同或运行许可。
