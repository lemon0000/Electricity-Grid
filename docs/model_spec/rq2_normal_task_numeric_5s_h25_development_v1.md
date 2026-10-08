# H25 固定五秒 normal 开发验证

状态：DRAFT_NONAUTHORITATIVE。目标是推进有效 normal 的缺口，复用既有 numeric 完整执行、赋值/witness 审计、持久化、capture 和独立回放链。原1秒观测无可行解，不能判不可行。本任务只允许一次预先固定的5秒调用，不按目标值选择参数，不自动重试或延长。

## 预先固定的范围

来源、H25完整矩阵、all-off机制初态、U250业务映射、1 thread、seed0、HiGHS1.15.1、gap1e-8、三项容差1e-9均继承原声明。仅将 `specification.time_limit_seconds` 和 `execution_budget.max_seconds_per_solve` 从1改为5；新目录和四项派生身份/controller身份相应更新。5秒处于既有通用单次开发上限30秒内，是一次短验证，不是正式实验参数选择。

完整normal仍需满足原60秒、768 MiB、完整最优性/赋值/witness验收。execute和replay各240秒、controller600秒及全部存储预算保持。增加4秒求解预算不保证有解，也不保证拿到赋值后的完整验证能在60秒内结束；任何失败均如实保留。timeout、无incumbent、资源超限或回放失败均不得改写为不可行、有效normal或正式结论。

`experiments/audit_rq2_normal_task_numeric_5s_v1.py` 读取并校验旧1秒声明SHA，强制除上述变化之外的输入、环境和预算相同。其余模型及执行链源码完全复用。声明 `configs/rq2_normal_task_numeric_5s_h25_development_v1.DRAFT.yaml`，SHA256 `3095c79e6bdea5ab1d26edabbd4c03feffaa5feccf8a697e36d7cfd4dc5383b2`。目标目录 `results/tables/rq2_normal_task_numeric_5s_h25_attempt1_non_authoritative`，已有目录不得重用。

## 运行前验收

核对新旧声明差异、所有派生pin和来源pin，拒绝重新计算声明摘要后的模型/容差/线程/资源漂移；沿用独占执行与进程监督，旧记录不修改。完成针对性检查与独立pre-seal后，只执行一次完整任务。成功标准是原normal acceptance以及独立archive/replay一致性，不以solver返回incumbent或进程exit0替代。业务及机组初态仍是机制假设。

独立pre-seal指出派生身份仅靠旧controller检查不足以在启动前排除自洽伪造的source链。新runner已从SHA固定的PairDeclaration独立重算normal→source→declared→replay，再验证controller身份；当前声明四项值原本均正确，无需修改。加入source/declared连带重hash反例后，新20项与旧runner8项合计28 passed（5.29秒），独立新20项通过（4.62秒）。pre-seal已闭合，无开放实质finding。本文件不授予formal run或改变科研注册/认证门。

## 2026-09-27 单次开发终态

runner SHA256 `067db81a8b40443761b18025159c97b0985bd15a8a21342e1f92aa36ccae6625`。通过 compute Python `-B` 调用上述 runner，传入 `--declaration <上述声明> --expected-sha256 <声明摘要> --expected-script-sha256 <runner摘要> --execute-development`，单次执行，无重试。外层日志 `results/logs/rq2_normal_task_numeric_5s_h25_attempt1_non_authoritative.log`。

API controller终态为 `completed_development_replay_diagnostic`，落盘controller.observation为 `validated_before_final_observation_write`，对应不同写入时点，均保留原值。controller238.281秒；execute/replay分别131.438/103.297秒，均exit0且Job静默，Job commit峰734322688/630001664 bytes。normal总计51.3511618秒、errors=()；preflight21.7703767秒、pipeline25.46389秒、嵌套builder4.3694796/4.4709501秒，不重复累加。

native为1 call、aborted/maxTimeLimit、solution_count=0、assignment_valid=false、optimal=false、native_infeasible=false。没有objective、upper、residual或witness，normal_accepted=false。回放 archive_consistent/source_input_binding_verified成立，errors=[]、solver_calls_by_replay=0，accepted_record_reproduced=false。所有正式/安全/完整任务资源权限保持false。5秒仍没有可行解，这是预算内未解状态，不证明数学不可行。

双capture字节一致。record3819394 bytes，SHA256 `615c0674a0ef35e90376366c11719b0af2c4062fb6d133438e33942c3d97bb77`；result identity `b86edec493d2cb86dafbeeec008c810f45c572273d438826809ee7f0900daf91`；replay report SHA256 `eec5e63a50ce44360f557083121c8db188ece88dea60436326fe2f9cd3597a70`。没有放宽原60秒或数值验收，完整normal在本次未报资源错误。

下一项先核对既有合格引擎与正常状态模型求解路径。仓库已有Gurobi和HiGHS的接口/规模记录及跨引擎pilot，adapter原生支持两者；当前安装gurobipy13.0.2。旧pilot对应其他模型与预算，不能直接认证当前H25 normal，需先做当前接口tiny验证，再预先固定同预算交叉验证；不能直接把开发对照解释为正式引擎选择或性能结论。

新98项索引 `results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/numeric_5s_task_attempt1_evidence.json`，SHA256 `4dc646b77c9e5aa71114b577117fc6a6493976c6e0a0fc6f7d9bcdb2cca55af6`。另绑定13个历史索引、471条历史证据；root均已复核。独立结果审计已闭合，核验98/98新项与471/471历史项、SQLite与capture/回放链及进度文档一致，无开放实质finding。原始lower仍保留，但不是可行、最优或不可行证书；本审计不授予正式权限。
