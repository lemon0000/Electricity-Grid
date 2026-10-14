# H1 finite enrollment 的按需 follow-up 判定

2026-10-09，DRAFT_NONAUTHORITATIVE。完成状态以本单元 development_checks 与最新 plan/blocker 为准。
根代理唯一 writer；开发函数读取已批准 finite-v2 机制文档，不提供新的科学或运行授权。

完整业务 carry 先通过 exact_business._validate 的确定性历史重放，并核对 expected carry identity。
只接受共享 actual business ledger，使用相对业务时钟 0..192；不读取任何 source row。
协议固定 E=168、F≤24、due=birth+24，due 小时末先恢复再保留 deadline snapshot。
primary 集合按 cohort.created_hour≤168 定义，后续新 cohort 与所有 debt 原样保留在描述集合。

每个 primary cohort：

- missed_at_deadline>0 是已知 deadline failure，即使后来 remaining=0 也不改变。
- missed_at_deadline=0 是已知 success，不能按真假值把零误认成缺失。
- due 前 remaining=0 是已知提前恢复。
- 其余尚未到 due 的正债务为 pending。

None/wrong due offset、到 due 却缺 snapshot、时钟或历史不一致均明确拒绝，不用继续到192掩盖合同错误。
h<168 时，即使没有 debt 仍需后续 enrollment 请求；h≥168 时，只要有任一 pending primary cohort
就需下一小时。h=192 后不能再生产来源或执行；合法完整历史的所有 primary due 均应已观察。
某 cohort 已失败不允许忽略另一个仍 pending 的 cohort；所有登记 cohort 的结局都要可判定。
all_component_observations_known 要求完整 enrollment、无 pending primary 且适用分项均非 U；
失败优先折叠得到的 recovery F 本身不能证明其他 cohort 已观察齐全。
primary 已全部判定时立即停止，即使 followup cohorts 的 remaining/debt 尚未归零。

输出分别保留 grid_request_status、cfe_request_status、primary_recovery_status。
请求观察只取前168条已提交 business records；不适用维度保留 None，完整E之前为U候选；
共享债务没有 grid/CFE provenance，deadline miss 只属于 recovery 分项，不向请求维度发明归因。
complete_contract_status 始终为 None；本单元不注册 ternary aggregate truth table、不生成正式联合评分。
未来若必要来源缺失，完整E中已经判定的请求观察不应被改写；pending recovery 保持U。
实际 source 缺失分类/右删失发布由后继 live owner 负责，本函数不证明 source availability。

Roster 开发接口只计算已重放业务事实的组合：active lane 必须与共同 outer clock 同步；
completed lane 不得还需要 primary 后续；halted_unresolved lane 不消费更多小时。
global need 是各 active lane need 的 OR。已停止 lane 可以比共同链更早结束，carry 不变。
调用方提供的 disposition、对象类型或返回 Assessment 都不是持久 owner 凭据；
owner_replay_authenticated、actual_paired_commit_verified、producer_admitted、formal_result 始终 false。
真正使用前，后继 owner 必须从持久配对 outcome 重放 disposition/actual carry，并在同一 live guard 下重算。

来源覆盖限制：冻结目录保留全部 enrollment windows，但 training 604 pairs、holdout 593 pairs 至少
一源缺完整24h尾部。缺尾不能提前判unknown；只有判定仍需要当前小时且该行缺失/映射未决才右删失。
后继 N 链从 genesis 声明最多192小时，enrollment/followup 沿同一 family/ordinal/obligation，
不重置 N、Rref、业务或 A 状态。旧168小时 parent 的已固定 identity 不能原地扩张。

本单元是完整192h producer 接线的前置行为修复；尚未接入 persistent owner、phase N controller，
不证明真实 source/root 集成、资源准入、raw ingress、完整 task manifest、LB/UB 或正式结果。
