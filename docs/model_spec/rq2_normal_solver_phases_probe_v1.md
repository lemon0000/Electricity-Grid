# H25 单次 native 求解阶段诊断

状态：DRAFT_NONAUTHORITATIVE。延续 numeric H25 开发记录，定位正常状态求解调用的时间分布；不改变模型、求解选项或 normal 验收。

## 实现与边界

`experiments/rq2_normal_solver_profile.py` 使用现有 numeric 模型和完整输入身份，固定本机 Pyomo 6.10.1、HiGHS 1.15.1 及相关接口源码。仅执行一次 fresh `solve(load_solutions=False)`，保持 HiGHS 1 秒、1 thread、tee=false。调用前后核对模型结构、未加载变量快照、完整输入及实现身份。

调用返回后读取既有 `_last_results_object`，记录 legacy/internal 状态、solution 数量、`set_instance`、`optimize`、`load solution` 及其嵌套计时、native 计数器和日志字节数/SHA256。日志正文不导出。`load solution` 是内部结果构造阶段名称，不代表本诊断给 Pyomo 模型加载赋值。HiGHS 总时间须落在 optimize 计时内；嵌套计时不得超过父计时，顶层总和不得超过内部 wall，内部 wall 不得超过接口耗时。

日志指纹只能标识当次内部日志，不能代替可复核的 presolve/搜索细分证据。现有计时若不能细分两者，保持未知；不得通过时间相减臆造 presolve 时间。

`experiments/diagnose_rq2_normal_solver_phases_v1.py` 沿用既有来源声明的完整 streaming prepare、独占诊断目录、固定 argv/environment/cwd/PID/creation FILETIME、Windows Job 和父进程核验。诊断进程上限120秒（含原静默尾部），Job commit 上限768 MiB。该预算是独立诊断预算，不替代 normal 的60秒验收。单个诊断 JSON 保持16384 bytes 上限。

`native.intent.json` 通过既有 exclusive-write/flush/fsync 在 native 调用之前持久记录。已有目录或预留不可重用。异常、进程中止、缺少或不匹配的预留、缺少完成记录均保持调用次数未知；只有正常静默退出、全部来源/身份/内容核验成功，才报告一次已完成的诊断调用。父进程不重算年度输入，不求解、不重试。

all-off 初态、U250 及业务映射沿用既有机制参数，不是真实运行观测。结果不生成 assignment/witness、正常状态接受结论或最优/不可行/安全证书；所有正式、认证和完整任务资源权限保持 false。

## 验收与测试

补齐 runner 显式依赖 pin 之前，helper 与 runner 阶段性针对测试共121 passed（31.85秒），包括 tiny 原生对照、调用前预留、预留失败零调用、native/返回后异常不重试、未知调用次数、来源与绑定篡改、fixed launch、父进程异常、计时包含关系和禁止日志正文导出。该次命令：compute Python `-B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_solver_profile_v1.py tests/test_diagnose_rq2_normal_solver_phases_v1.py`。

helper 独立 pre-seal 已闭合，两项 finding（日志正文输出、native 时间包含关系）已修复；独立复测36 passed（2.56秒），其后 helper 字节未变。补齐执行器、进程层和持久写入层的显式源码绑定后，最终 runner 的85项测试与旧 prepare/numeric probe 相关回归合计215 passed（79.42秒），这是当前 runner 字节的测试终态。runner 独立 pre-seal 已闭合，无开放实质 finding。以上开发测试不构成 official review 或正式实验门证据。

## 2026-09-27 单次 H25 开发观测

使用原 H25 development 声明 SHA256 `9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6`，runner implementation pin `8bf88df7d0edf733238d5b4b1813911f811015c2d44e8315737a9229066fe084`。命令为 compute Python `-B experiments/diagnose_rq2_normal_solver_phases_v1.py --declaration configs/rq2_normal_task_h25_development_v1.DRAFT.yaml --expected-sha256 <上述声明摘要> --expected-implementation <上述实现摘要> --diagnostic-root results/tables/rq2_normal_solver_phases_probe1_non_authoritative --execute-development`。单次执行，未重试。

父侧汇总 `normal_solver_phases_observed`，errors=[]，solver_calls=1、call_count_complete=true。进程 exit0、whole_job_quiescent=true，Job elapsed60.969秒，commit峰526721024 bytes；子进程观测58.5945922秒，其中完整 prepare35.798187秒。这些是独立诊断的进程和子阶段计时，不是 normal 验收计时。

| 当次阶段或状态 | 观测 |
|---|---|
| set_instance | 1.7605765 秒 |
| optimize | 1.0094633 秒 |
| 内部 load solution 标签 | 0.0004879 秒；模型值未加载 |
| HiGHS reported / internal wall / legacy interface | 1.0091042 / 2.7721603 / 2.7725891 秒 |
| legacy / internal | aborted / maxTimeLimit；noSolution |
| solution_count / mip_node_count / simplex_iteration_count | 0 / 0 / 4844 |
| ipm / pdlp / qp iteration count | 各为 native 原值 -1，不能当作零次计数 |
| 日志 | 2022 bytes，仅保留 SHA256 |

模型结构身份 `e18f8f95846b33f4c358fe8d2a47082660ea19f161e317ca672ccd657e3f40f0` 与既有 numeric H25 相同。本次证明模型传入及 native optimize 均实际完成返回；调用到达1秒限额仍没有 solution。0个 MIP node 和4844次 simplex iteration 不证明不可行，也不提供完整 presolve/搜索阶段分解。此次2.77秒接口耗时与旧完整 normal 的24.24秒 pipeline包含不同工作，不能直接作性能差值或把旧 pipeline 全归因为 solver。

结果根为上述 diagnostic-root，外层日志 `results/logs/rq2_normal_solver_phases_probe1_non_authoritative.log`。本次没有 assignment、witness 或任一种认证，normal_accepted=false。新38项索引 `results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/normal_solver_phases_probe1_evidence.json`，SHA256 `5ed4385cf074e0dc5e260a7ba11ab3c3d7ea1c6f0fd70449b303e46939f6ad89`；包含本次源码、测试、进程产物、声明、来源记录及本机私有接口源码，另绑定12个历史索引、433条旧证据。旧433条已在执行前后复算保持一致。

独立只读结果审计已闭合：38/38新项、12个历史索引与433/433旧项均复算一致；intent、launch、Job observation、phases、summary、实现/来源/process pins及binding链一致。计时包含关系成立，日志仅保留字节数与摘要。文档中未落盘的外层会话计时已移除，无开放实质 finding。该审计为 non-authoritative，不产生 official verdict、receipt 或正式权限。

下一必要工作是给“有效 normal 仍缺可行解”建立可复核的有界开发验证方案：把原1秒探针的观测与后继可行性验证的预算、成功标准和失败语义分开，在运行前固定，保持原模型、安全阈值和旧产物。不得把本次到时无解改写为模型不可行，也不得以增加时间后出现 incumbent 代替现有最优性和 witness 验收。真实 current/episode、完整 UID/四臂资源以及正式实验仍依赖有效 normal。
