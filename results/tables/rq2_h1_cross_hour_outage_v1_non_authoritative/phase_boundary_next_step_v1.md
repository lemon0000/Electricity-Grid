# 下一步：真实时域边界的连接验证

2026-10-20，DRAFT_NONAUTHORITATIVE 工作清单。入口证据为三小时事故/修复/分支停止完整链及其独立 postcheck；旧 hour0、两小时 batch 与相关 guard 按 SHA 复用。这里没有启动新实验或打开正式门禁。

当前已覆盖：N0/N1/N2 → 共同 Rref/各 active Actual → paired/carry/debt → 一个 lane timeout 后其余 lane 继续 → 缺下一小时输入拒绝 → 外部关键 heads 留存 → clean-close 同进程只读重开。完整168h enrollment和至多24h follow-up尚未连接验证。

后续按以下依赖推进：

1. 从冻结规格、原 phase/business FSM 与配置列出 hour167→168、follow-up 上限及 episode terminal 的准确输入与状态条件。分开正常零债务结束、携债进入 follow-up、恢复后结束、到上限仍携债及缺源；右删失只在合同规定的条件下报告。不得缩短 E/F 来冒充真实边界。
2. 审查原 source/normal/owner 的前缀、freshness、holder/heads 关系与 readonly replay 成本。列出完整调用 DAG、正常及失败/收尾次数，并沿用本次32/64的明确统计层级；不可把 API 层计数当全部 I/O。
3. 优先复用现有确定性 oracle、未变 guard、旧保存重放和已闭合 source coverage；若新路径需要真实168h前缀，必须逐项证明来源与合法复用关系。不能从待认证 journal/ticket 推断外部 expected heads，也不能跳接当前/未来或跨 split 行。normal writer 冷重建未实现，不能私下 adopt 旧 root 继续写。
4. 为尚未覆盖的昂贵动态重放先设计有界诊断，固定问题、次数、whole wall/RSS/storage、活动与超限停止规则。若需增量/跨调用复用，先证明 dependency closure、输入 freshness、失效/异常/并发窗口与逐小时科学等价，采用独立 DRAFT successor 和只读 PRE_SEAL 复核。
5. 预算和必需科学不变量有证据后，运行能连接真实 phase 边界与终结的合成路径，核 N/Rref/A carry、paired 状态、恢复债务、失败停止、诚实右删失、外部关键 heads 及关闭后完整只读重放。报告模拟覆盖和墙钟、保存字节、失败原件与各未闭合项。
6. 完整跨小时证据闭合后，落实具体科研任务/reuse DAG、同合同 LB/UB 与完整资源预算，再按既定 seal、fresh official review 和具体正式运行授权推进正式科研实验。

当前不变的 OPEN 项：完整168+至多24小时、episode结束与正式follow-up右删失、真实RTS/native、生产整体预算、writer可写重建、持久atomic-live认证、seal与fresh official review。旧Common/source-factory findings保留，主线只处理直接影响上述连接路径的阻断。
