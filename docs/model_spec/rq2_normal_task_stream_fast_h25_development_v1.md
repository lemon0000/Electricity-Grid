# Fast streaming H25 单次开发验证

2026-09-27，DRAFT_NONAUTHORITATIVE。执行、双归档和独立回放完整结束，但 normal 数值门仍为 unresolved。此次结果不解除正式实验阻塞。

## 输入、执行与核验

使用 `configs/rq2_normal_task_stream_fast_h25_development_v1.DRAFT.yaml`，SHA256 `807fcffd90ec05f2fdc6893b1b8be079aa53be8d4e80ebce7e94a46cbad6bb95`；runner `experiments/audit_rq2_normal_task_stream_fast_v1.py`，SHA256 `96d872bf0b6460a42fce17de3c5d51a8d222ab36d27207f8898f3655b192b182`。命令使用 compute 环境 Python `-B`，传入上述 `--declaration`、`--expected-sha256`、`--expected-script-sha256` 及 `--execute-development`。仅一次开发调用，无自动重试。

H25、22275 variables、28004 constraints；HiGHS 1.15.1、1 thread、1 second，normal 60 seconds、Job 768 MiB 等原预算保持。RTS-GMLC 来源与既有配对保持；all-off 初态、U250 和业务功率映射属于机制参数，不能当作真实观测。

controller/报告/runner 最终相关回归为 92 passed in 223.37s；独立 pre-seal 定向分别 9 passed 和 34 passed，过程及修复见 `rq2_normal_task_controller_stream_fast_v1.md`。

## 实际结果

| 项目 | 观测 |
|---|---|
| controller API 终态 | completed_development_replay_diagnostic；303.141 s |
| 落盘 observation 状态 | validated_before_final_observation_write |
| execute / replay Job | 165.781 / 133.453 s；均 exit 0、whole_job_quiescent=true |
| execute / replay Job commit 峰值 | 734072832 / 631373824 bytes |
| normal elapsed | 63.5284186 s；observed_wall_time_exceeds_budget |
| preflight / solve-load-canonical pipeline | 30.0346942 / 27.6280582 s |
| 嵌套 builder 时间 | 5.7378942 / 5.9379112 s；不可与外层 pipeline 重复相加 |
| native solve | 1 call；aborted / maxTimeLimit；solution_count=0 |
| assignment / witness | 未取得；objective、upper、residual 为 null |
| independent replay | replayed_unresolved_declared_normal_record；errors=[]；solver_calls_by_replay=0 |

API 返回与落盘 observation 的状态处于不同写入时点，保留各自原值。归档一致和来源绑定核验成立，但 accepted_record_reproduced=false；无最优性或不可行证书。whole_task_resources_verified、hard_disk_quota_enforced、native_execution_authenticated 和 formal_result 均为 false。进程观测未越原 Job 限额不等于整任务资源认证。

旧 stream normal 为 67.5576574 s，本次为 63.5284186 s；不同运行时点和负载不能支持受控性能提升结论。此前编码级对照也不能替代完整 normal 的 60 秒验收。

## 留存证据

结果根：`results/tables/rq2_normal_task_stream_fast_h25_attempt1_non_authoritative`；日志：`results/logs/rq2_normal_task_stream_fast_h25_attempt1_non_authoritative.log`。

新增索引 `results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_fast_task_attempt1_evidence.json` 绑定 76 项，SHA256 `91dda12ffceb2463b3fa1fda666ede79d23d0b888953a223e3e3eb1d1ca94a69`。旧八批 188 项 bytes/SHA 重核一致。新索引独占创建；未覆盖旧文件。

独立只读结果审计复算新 76/76 与旧 188/188 项一致，并核对 phase 交叉链、SQLite schema/record 和状态解释；未运行 solver 或数值 replay。唯一轻量 finding 是历史总数未自包含绑定八个旧索引，已新增独立清单 `results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_fast_task_attempt1_index_inventory.json`，SHA256 `8cf0ec3ecdc9f702412db7883b880b5098a27afef9265168f6fe288cb27fd96a`。清单逐项列出八个旧索引及本次索引的路径、bytes、SHA 和条目数；生成时再次复核所有 264 条，原结果索引未改。该审计不是 official verdict 或 gate receipt。

controller identity 重算一致；retained_pins 与 final_pins 字节相同；SQLite 在进程静默后以 mode=ro&immutable=1 读取。record SHA256 `197bf5662d72c66a211e2d4b25d6d131c09dee389c45c6d57ef90299a703d11b`，3819367 bytes；replay report SHA256 `92efefbadf4e97b35aa277c9f26544a1a849a4583600ad1a9888725d5b1ec2a9`，均与外部记录一致。

## 下一必要工作

先进一步定位完整身份复核和 normal 构建/加载耗时，在独立后继中保持全部复核点及 60 秒门；另行诊断 1 秒求解无解记录的形成过程。两项均未解决，不能仅靠编码加速推断取得有效 normal。已有本次结果绑定的代码、配置和结果保留，不在原 attempt 重跑。

只读代码核查进一步限定诊断范围：`run_normal_only` 的 admission builder 与 solve builder 均保留构建前后身份复核，builder 内部还重新核验模型输入。现有 `preflight_seconds`、`builder_seconds_nested` 和 pipeline 时间包含重叠区间，无法直接分离验证、编码、构建、接口传输与 native solve 的耗时。`continuous_grid_candidate._solve` 在 `load_solutions=False` 返回后直接记录 `len(native.solution)`；本次 count=0，后续显式加载和 assignment witness 没有执行。因此现有证据不能把无解归因为加载失败，也不能判断求解时间消耗于 presolve、搜索还是接口开销。

下一诊断应先补不改变数学模型和调用次数的分段计时设计及 tiny oracle，分别覆盖 identity validation/encoding、builder、solver create/solve、返回证据提取；完整输入复核、模型矩阵与旧编码字节必须保持。新增计时只能是开发诊断，不作为扩大 solver 限额或削减复核点的理由。

有效 normal 后才可推进依赖它的真实 current/episode、完整 UID 与四臂资源验证。恢复末端右删失、风险分母、holdout overload、未识别机制参数、科学注册与正式启动门继续开放；连续多日、恢复债务、拒绝动作及四臂诊断既有实现无需重复开发。
