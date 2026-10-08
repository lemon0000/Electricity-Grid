# Numeric streaming H25 单次开发结果

2026-09-27，DRAFT_NONAUTHORITATIVE。完整 execute→capture→replay→recapture 已结束。normal 实测 53.8714377 秒，本次未触发原 60 秒超时；仍未取得可行解或 witness，数值状态保持 unresolved，正式实验阻塞未解除。

## 实现与调用边界

实现、完整测试及独立 pre-seal 审查见 `rq2_normal_execution_stream_numeric_v1.md`、`rq2_normal_persistence_stream_numeric_v1.md` 和 `rq2_normal_task_controller_stream_numeric_v1.md`。各组 root 终态为 179、121、118、71、61、33 passed；它们是分别运行的文件集，不是单次整组结果。独立审查的实现及文档 finding 已闭合，无 official verdict/receipt。

声明 `configs/rq2_normal_task_stream_numeric_h25_development_v1.DRAFT.yaml`，SHA256 `6cc200dad82041d33ac83277d9067c32e63bc9d0d56428b949081a46b5243b0c`；runner `experiments/audit_rq2_normal_task_stream_numeric_v1.py`，SHA256 `50cd24d39b3c532f0efc0f53ad2645d33eace067e11f2a1bbaea797ade281e35`。

调用命令为 compute Python `-B` 加上述 runner，传入 `--declaration <上述声明> --expected-sha256 <声明摘要> --expected-script-sha256 <runner摘要> --execute-development`。一次开发调用，日志以独占创建方式保存，未重试。controller pin 启动和终态均为 `eb17872a206cf009d317ab8cf05971fcdda3663552f3cd10b0e8d851c9d6929c`。

H25/22275 variables/28004 constraints、HiGHS 1.15.1、1 thread、1 秒求解、60 秒 normal、768 MiB Job 和 600 秒 controller 预算保持。来源与旧 fast 声明相同。all-off 初态、U250 和业务功率映射属于机制参数，不是真实机组或数据中心运行观测。

## 观测结果

| 项目 | 本次观测 |
|---|---|
| API 终态 | completed_development_replay_diagnostic；272.5 秒 |
| 落盘 observation 状态 | validated_before_final_observation_write |
| execute / replay | 147.25 / 121.656 秒；均 exit 0、whole_job_quiescent=true |
| execute / replay Job commit 峰 | 733990912 / 629653504 bytes |
| normal total | 53.8714377 秒；errors=() |
| preflight / solve-load-canonical pipeline | 25.2331097 / 24.2355538 秒 |
| 嵌套 builder | 4.7877502 / 4.8441187 秒；不与外层重复相加 |
| solver | 1 call；aborted / maxTimeLimit；solution_count=0 |
| assignment / witness | 无；objective、upper、residual 为 null |
| 独立 replay | replayed_unresolved_declared_normal_record；errors=[]；solver_calls_by_replay=0 |

archive_consistent 与来源绑定成立，但 accepted_record_reproduced=false。normal 没有时间/内存错误并不等于 normal_accepted；后者仍要求最优性、完整 assignment 和 witness。本次没有 infeasibility/optimality/security certificate，whole_task_resources_verified、hard_disk_quota_enforced、native_execution_authenticated、formal_result 均为 false。

旧 fast normal 63.5284186 秒、新 numeric 53.8714377 秒来自不同执行时点，不能用该差值宣称受控性能提升或跨运行资源保证。它只证明本次完整 normal 没有触发原 60 秒门。

## 证据留存

结果根 `results/tables/rq2_normal_task_stream_numeric_h25_attempt1_non_authoritative`，日志 `results/logs/rq2_normal_task_stream_numeric_h25_attempt1_non_authoritative.log`。API 返回与落盘 observation 的状态处于不同写入时点，保留各自原值。

99 项索引 `results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_numeric_task_attempt1_evidence.json`，SHA256 `d5679002d9c4a388a4c955eb4a95096321169196eb26bf3c1a266d46180ad983`。索引同时列出 11 个历史索引的路径、bytes、SHA 与条目数；旧 334 条逐项复核一致。

retained_pins 与 final_pins 字节相同。进程静默后以 SQLite `mode=ro&immutable=1` 读取：record 3819353 bytes，SHA256 `47fbd733141708967c231dfc9bf3590cd38794ad6bdd2df52671d8048fa520f2`；replay report SHA256 `d2986971056852e06d571e152ab3503e12c4c2966b3734e409165b5a9fb0c569`，均与外部记录一致。本次绑定源码、声明、结果均保留，后续使用明确后继。

独立只读结果审计已完成：新 99/99 项、11 个历史索引及其 334/334 项、三项外部输入声明均复算一致；双 capture、SQLite 三表/application ID、进程身份链、零 solver replay 与 API/落盘状态时序闭合。结果解释及四处进度同步无开放 finding，不构成 official verdict、receipt 或正式门证据。

## 下一必要工作

重点转向 native 求解阶段：现有记录只能确认 1 秒返回无 solution，不能区分 model transfer、presolve、搜索的成本，也不能解释为数学不可行或归因为加载失败。下一项补独立且有界的求解阶段诊断设计和 tiny 验证，保留当前限额、模型及验收标准，记录实际阶段信息后再确定必要修复。

本地已安装 Pyomo 接口只读核查发现：`pyomo.contrib.solver.solvers.highs.Highs.solve` 在转换为 legacy 结果之前将内部 `Results` 保存在 solver 的 `_last_results_object`，其中包含 `solver_log`、`timing_info.highs_time`、wall_time 和 `HierarchicalTimer`；`LegacySolverWrapper._map_results` 只将状态/界映射至本项目目前保存的 `SolverResults`。因此下一诊断可以在一次同模型、同限额、`load_solutions=False` 调用返回后读取现有内部记录，无需额外求解或更改 solver 选项。该私有接口须固定版本及源码身份、限制输出并以 tiny 对照验证；计时器的 `load solution` 标签不代表 legacy 模型发生了显式加载，presolve/搜索细分仅在日志实际提供时报告，否则保持未知。

有效 normal 仍是后续真实 current/episode 和完整 UID/四臂资源验证的前置条件。恢复右删失、风险分母、holdout overload、未识别机制参数、科学注册及正式运行门仍开放。已有连续多日、债务、拒绝动作、四臂及诊断产物继续复用。
