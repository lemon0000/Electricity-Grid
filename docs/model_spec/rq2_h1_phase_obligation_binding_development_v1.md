# H1 finite episode phase obligation binding

2026-10-09，DRAFT_NONAUTHORITATIVE。根代理唯一 writer；本单元仅审计已存在的 pending N request。
完成状态以 development_checks 和最新 plan/blocker 记录为准。

后继 parent 必须从 genesis 声明 hours=192；旧168小时 declaration 的 identity 不允许原地扩张。
relative_hour 0..167 为 enrollment，168..191 为 followup；拒绝 bool、非整数和超界小时。
两阶段使用同一 unresolved training_ub family、ordinal、完整 source catalog coordinate 与 obligation node。
不把 followup 改名为 holdout 或 training_b6_actual；其他义务家族仍各自保留，尚待后续接线。

整段 E=168 预检仍调用已经闭合的 enrollment validator，固定起点和168行，保持 CFE domain、workload
投影、chain、split 与 source catalog 检查；进入 followup 不扩张预检为192行，也不截断或删去来源义务。
当前行只按原起点加 relative_hour 加载，并核对 pending receipt 的来源 lineage、request key、预算和时钟。
同一 parent/spec/limits/budget 原样进入记录；phase 属于审计标识，不加入 N 科学 request key。
前后复读 pending request 与 pinned dependencies，确认字节和文件观察保持一致。

本 API 的顺序前提是“当前 pending request 已经存在”。它不能证明该 request 创建前检查过 live need。
followup_need_authenticated、paired_owner_guard_authenticated、episode_terminal_verified 始终 false；
返回 JSON、resolver node 或 phase 标识均不是启动 N/source、Job、Rref/A 或发布 paired outcome 的凭据。
完整资源准入、正式运行、策略证明和可执行任务目录仍为 false。

测试保留真实 pinned RTS/marginal input 上的 hour0 pending join，使用192h parent，但不运行 solver/Job。
167/168/191 的 tail join 测试明确替换 pending N snapshot seam，同时读取真实当前源行；它证明 phase、
来源坐标、固定 E 预检与记录绑定，不证明存在 accepted 192h N prefix、真实 native 或完整执行。

后续集成顺序：owner 在一把 live guard 下重放 paired state，先判 need；若仍需当前小时，先留存
pre-N attempt intent，再调用 phase controller，绑定 owner heads/intent/need 与 controller predecessor。
N 产生 terminal 后才读取该小时 fresh source join，再进行 Rref/business/A 与 paired commit。
若无需下一小时，则发布独立 episode terminal，不读取下一来源、不伪造底层 parent complete。
completed/halted lane 的 carry 必须冻结；失败和模糊提交保持 pending/unresolved，不自动重试。
这些 live owner/controller、失败窗口和 source right-censor 接线尚未由本单元实现或验证。
