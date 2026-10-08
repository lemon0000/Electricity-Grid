# H1 完整锁链回放与共同投影开发日志

2026-09-30，DRAFT_NONAUTHORITATIVE；依据已批准 v2/H1 规则实现，尚未 production seal。

`normal_h1_replay.py` 对完整 H1 native report tuple 逐阶段重建模型。
阶段次序由当前输入决定，下一阶段的等式 RHS 只来自此前 assignment 的独立 canonical 重算；
每阶段重新执行原 normal 数值 predicate、objective provenance 回算和 H1 严格 assignment 审计。
原始上下界、assignment、报告字节不修正。最后 assignment 还需通过精确 carry 域门。

`archive_current` 只接受完整 owned current result，同时对照重算得到的 stage identity、assignment audit、
numeric predicate bytes、锁链与最终公开 projection。输入中的权限异常被拒绝，不通过改写 false 消除异常。
存档逐字保存全部 native report；`replay_archive` 要求外部保留的 SHA256，并重新计算所有派生字段。
单 report 最多 16 MiB、最多 20 阶段，报告原始字节合计和最终 canonical archive 均不超过 32 MiB。
原始报告预算先于模型重建检查。

回放输出为不可变诊断投影，包含完整 all-UID 状态值、relative completed hours、canonical 锁链及其身份。
它不是 `H1NormalBoundary`，不能直接供下一小时 source adapter 使用。
`solver_calls_by_replay=0`；报告中的 native 字段只按证据数据重算，不证明历史 native 执行真实性。
`native_execution_authenticated`、`published`、`formal_result` 始终 false。
reserve 等辅助 witness 可以不同；若全部审计通过且公开投影相同，不判决策冲突。

`normal_h1_projection_store.py` 提供独立的 `DevelopmentH1ProjectionStore`：

- 复用已存在的本地 Windows NTFS 单 owner lease，目录必须以 `_non_authoritative` 结尾。
- SQLite 使用 DELETE journal 与 synchronous FULL；记录只追加，不覆盖已有 witness。
- 每条记录绑定 sequence、前 head、request key、原始 archive SHA256，并生成新 head。
- 打开已有日志必须提供独立保留的 exact head；schema、header、文件身份、连续历史与每份 archive 字节 hash 均复核。
- 最多 64 条记录（可声明更低上限），全库 archive 字节合计最多 64 MiB；读取 blobs 前通过 SQL 计数和长度检查预算。
- 每次读取某个 key，重新验证该 key 的所有 archive。没有记录返回 `absent`；全部投影一致返回 `available`；出现不同投影返回 `unresolved_conflict`，且不返回可供消费的投影。
- 后来再次提交原投影不能消除冲突。同一个 key/archive SHA 的重复追加是幂等操作，不增加记录。
- 追加前验证完整 witness；commit 后关闭写连接，以新连接逐字读回预验历史与 head，再返回成功。
- commit 或读回异常后 owner 停止写入和重试；恢复需独立保留的 exact head。失败调用期间内存 head 可能只是预期值，不能仅凭该值声明提交成功。

这些操作持久保存的是已完成的开发证据，不登记或发起 native invocation；没有 production lease 或执行权限。
日志输出没有 executable boundary，也不推进 episode 的 N/Rref/A head。
后续 controller 仍须完成来源认证、源审计 lineage、episode 精确 predecessor 回放、三链状态发布及按需后续。
哈希与零 solver 重算不能替代这些证据，也不构成完整履约或最低容量认证。

测试区分两个范围：完整数值回放拒绝 stage/assignment/bounds/派生字段篡改，并验证合法 auxiliary witness 变化不改变 projection；
日志的一致性测试通过 validator-output 故障注入制造不同投影，验证 sticky conflict 规则，不将该注入称作第二份真实 native 证书。
原子性测试分别覆盖 commit 前、commit 后返回前、未实际 commit 以及 commit 后读回失败。
