# H1 完整阶段资源声明与 full anchor

状态：DRAFT_NONAUTHORITATIVE，R3 PRE_SEAL findings 已闭合；无执行、封存或正式结果授权。独立审查者只读复核实现、测试证据与产物，未运行测试、runner 或 solver。

现有 `execution_workload.NormalWork` 每个 normal 任务计一次求解，不能用于本 H1 normal。新 `normal_h1_full_resource_contract.py` 使用独立 `H1NormalWork`，完整登记固定顺序的成本、committable UID commitment 和全部 UID generation 阶段，并保留精确 solver specification。158 台机组、73 台 committable 对应每小时 232 次，192 小时 44,544 次。没有共享命中率、提前停止、重试或 scratch 回收抵扣。

新合同复用 `TaskEnvelope` 与 `SerialResourceBudget` 的声明字段，但不调用旧 single-normal workload 核算。per-stage TimeLimit 以其输入数值的精确有理数累计；单任务 wall 取 solver 总秒数加 non-solver allowance 的向上取整。non-solver allowance 必须包含来源加载、构模、原生接口超时余量、审计、存档、重放、关闭与静默。该数值由调用者声明，尚未测量充分性。全串行 wall 累加，Job commit 取最大值并另加 supervisor 与 reserve；全部 archive/scratch 累加保留。

`bind_current_hour` 对实际 current packet、任务小时范围和完整 stage order 进行绑定，实际构造首模型及带 n-1 个有限零占位锁的末模型，核验变量不变、行数恰增加 n-1，且实际两端规模满足声明与 replay limits。占位锁只用于 shape，可能不可行；输出明确 shape_only_placeholder_locks=true、complete_chain_shape_verified=false、numerical_certificate=false。它不产生 assignment、不假造未来 carry，也不免除后续实际 stage 的 runtime size 和数值审计。

## 完整内容上界

设阶段数 n、小时数 H。原始报告上限 R=16MiB、元数据 M=256KiB、chunk=1MiB 保持原值；新 anchor 单记录 A=64KiB。

| 存档对象 | 最坏内容字节 |
|---|---:|
| 每小时 child：n 份 raw、n+1 事件 | nR+(n+1)M |
| 每小时 registry：intent、n+1 checkpoints、outcome | (n+3)M |
| 每小时 anchor：genesis、n+3 事件及 header | (n+5)A |
| 父 journal：每小时 intent/outcome，每事件最多 2M | 4HM |
| 父 anchor：genesis、2H 事件及 header | (2H+2)A |

总内容上界为 H 倍前三项加后两项。另要求显式正数 `archive_overhead_bytes`，用于 SQLite schema/header、pages、索引、rollback journal、目录分配、execution locks、controller/request/result 文件等；这仍是 allowance，不是已证明的物理空间上界。TaskEnvelope.archive_bytes 必须至少覆盖内容上界加该 allowance。scratch 独立计入，禁止依赖清理仓库或旧结果兑现预算。

声明检查始终保持 model_shape_verified（整计划）、physical_space_reserved、whole_task_resources_verified、execution_authorized、formal_ready 为 false。模型绑定只对提供的当期模型单独报告 shape 检查结果。主机/卷准入、OS commit 限制和全生命周期资源执行仍须接入已存在的 `declared_task_process` 与 `normal_resources`；磁盘不是硬 quota。

## 版本化持久锚点

`normal_h1_full_attempt_anchor.py` 保留 immutable 文件、xb/fsync/fresh-read、独立根目录 lease、previous head/hash 链、未知提交 poison 与重开仅审计语义。独立 schema、`FullAnchorReceipt` 类型和实现身份将其与旧 anchor 隔离，旧 24 条 cap 不变。

新声明最多 385 条：单小时 232 阶段需要 236 条；192 小时父日志需要 385 条。header 不计入 records 数，但计入内容字节。每份读取最多 64KiB+1，以超限拒绝；单条写前检查 64KiB。完整扫描保留，因此增加支持容量不等于证明长期 I/O 成本可接受。本地受信根不是抵抗恶意全目录回滚的服务。

anchor implementation identity 绑定其自身及直接 registry/pin、codec、lease、controller/file helper 模块字节。依赖改变时 live owner 与旧 root 重开均拒绝；不能跨依赖实现误认持久记录。

## 后续连接

完整 collector 必须使用此独立 workload/资源声明，不能把它伪装为旧 GridDevelopmentBudget；保持完整 lex stages、normal 原数值门、逐 raw 分块与 checkpoint/anchor 持久顺序。full controller 复用既有 envelope-bound Windows Job 类，无需重写底层进程监督。现旧短 collector 与 source parent 尚未接入此合同，不能执行真实 232-stage native 链。实际 per-stage 时间、non-solver、commit、archive overhead、host/volume、地点与任务清单仍须形成具体且可审阅的运行包。

## 开发证据

初始 targeted 33 项通过（395.88s），包含逐条写入全部 385 records、单小时第 236 条边界确认、容量耗尽拒绝及重开只审计；当时 anchor SHA 为 `d73d61529646d94d247bfdd86a0c236dacd401dd374c092e6c7c4189b0e2aa68`。随后只增加 anchor 的直接依赖身份绑定，并修复资源绑定/两端 shape 验证。最终受影响定向与旧 anchor/resource/declared-process 回归 67 passed、1 deselected（3.91s）；deselected 是已完成的完整 385 条循环。没有将该早期运行时间当作最终实现或真实工作负载的资源测量。

`experiments/audit_rq2_normal_h1_full_inventory_v1.py` 验证旧 shape 的 11 个绑定文件及固定 1+73+158 阶段结构，在禁止 solver 的作用域内导出库存。单小时完整内容上界 4,031,840,256 bytes，192 小时 774,088,294,400 bytes；这是全部预留槽位取内容 cap 的上界，非实际写入量、最低磁盘需求或已保留空间。per-stage TimeLimit、non-solver、archive overhead、commit、host/volume 均保持 null。详细记录位于 `results/tables/rq2_normal_h1_full_resources_v1_non_authoritative/`。
