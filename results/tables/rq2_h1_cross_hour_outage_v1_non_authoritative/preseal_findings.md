# 三小时合成链的只读 PRE_SEAL findings

2026-10-20，DRAFT_NONAUTHORITATIVE。root 为唯一 writer；现有独立只读 `sol_reviewer`（`/root/source_factory_preseal_audit`）进行开发范围复核。没有 production seal、official verdict、receipt 或 gate 变更。

冻结用例范围：3h、两台 normal 机组、3 lanes；事故在左边界已 active/onset unknown，h1 延续，h2 观测修复且 cap24MW；CFE h1 timeout 后两 carry 均保持，其余 lane 继续；缺 h3 拒绝后关闭、从 live preclose 独立关键 heads 留存进行同进程只读重开。完整168+24、真实RTS/native及正式实验不在已完成范围。

| Finding / 要求 | 修正与证据 | 当前状态 |
|---|---|---|
| 两机 inventory 的 producer aggregate budget | 原 connected01 失败保留；toy 每小时13次/13s，unit06 直接调用原 producer 验12次或12s在0capture前拒绝、13/13完成完整13stage | 当前 toy 用例闭合 |
| q/r 测试误加调用上限 | 原 unit03 失败保留；按冻结合同分别验q<=f*w、q+r<=D及恢复上限，原模型/config/阈值不改；Fraction oracle 与保存7paired全等 | 当前科学一致性闭合 |
| 只读尾部 file-only 无活动停止 | connected02 原终态保留；detached03 先取得0Job保存重放与CPU观测证据；新 attempt 以实际owned-tree CPU或文件活动监视，1500s wall不变 | 当前监视诊断闭合；CPU不代表算法进展 |
| 原外部 expected heads 仅在 RAM，停止后不可重建认证 | 不从旧 journal/最后ticket adopt；原 connected02 authenticated reopen仍未验证。connected03在close前独立exclusive/fsync/readback保存关键heads/科学对照，删除原RAM对照后从文件读取 | 新3h clean-close同进程范围闭合 |
| Windows held execution.lock 无法第二句柄读 | 原 owning stream 读实际字节并恢复游标；0Job实际嵌套函数AST probe覆盖8held→closed→fresh2；完整444文件前后SHA一致 | 当前文件采集范围闭合 |
| postcheck 精确计数与资源合同缺少固定断言 | 固定444 owned、1299 actual request pins、1279 inherited、1500s/120s/1GiB/128MiB及activity policy；1299来自实际request，不采用早期估数1300 | 闭合 |
| postcheck parent身份误用owner换行编码 | 首次script/终态保留；按原无尾换行compact JSON合同独立计算，新增三个Job request声明与identity全等；独立补验exit0 | 闭合；没有修改科学数据 |
| 性能文案把单个Reader observation叫作完整batch | 定向文档复核指出33.283s仅为单Reader观测；按真实owner stage原始timing补完整batch_source最大65.255s，并说明每batch两个独立Reader；改前报告保留 | 当前性能统计口径闭合 |

独立 reviewer 终态交叉核：444文件inventory=checkpoint=result；9events顺序和两owner heads/holder head一致；34captures为13/11/10，唯一index17 timeout有有效incumbent、optimal=false/native_infeasible=false；全部assignment balance/residual检查通过，h2 G1均24MW。CFE状态为paired→actual_unresolved→skipped_halted，business/actual后续均未推进。3个fake Job PID唯一、exit0/quiescent，各numerical_evidence_verified/formal flags仍false；不存在hour003的Job/clock/obligation/parent项。

32个batch observation token互异，API/prefix32/64、parent64/128；13个trace完整，checkpoint至最终reopen约175.6s。旧connected01的164文件与connected02的462文件由reviewer逐项重新计算SHA，均未变化。request1299与继承1279计数一致。reviewer确认parent修正与原`normal_h1_projection_store._bytes → rq2_objective_provenance_run_v1.encode`合同一致，并加强了三个Job的独立关系校验。

当前3h synthetic范围未见剩余具体阻断finding。fake Jobs的`numerical_evidence_verified=false`；完整未观察process-tree absence、crash durability、writer rehydration、持久atomic-live、production budget、full192、真实native、正式follow-up右删失、formal/resource均未证，产物维持false或OPEN。只读开发复核不替代将来exact sealed outer的fresh official review。
