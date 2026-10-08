# H1 分块内容 journal 开发规格

状态 DRAFT_NONAUTHORITATIVE；为后继完整 H1 链提供独立物理存储原语，不是 normal episode、数值重放器或正式资源合同。旧模型、solver、20 calls 短门和单 BLOB store 均保持原版本。

## 身份与内容

独立 DevelopmentH1ChunkJournal / SCHEMA / APPLICATION_ID / h1_chunk_journal.sqlite3，复用本地 NTFS lease、文件身份和 DELETE/FULL 连接。三张 STRICT 表精确核验；header 绑定绝对根目录、外部 binding identity、实现哈希、预算、SQLite 版本和表结构。根目录必须 _non_authoritative。重开必须提供独立留存 head，不能自行从 DB 接受末 head。

元数据为不超过 256 KiB 的 canonical JSON object。每个非空 immutable bytes chunk 最多 1 MiB；append 接受单次 iterable，另需调用方独立声明总 payload 字节数与 SHA256。每块存储自身 SHA256 和递增 chunk chain；event 保存小 descriptor（长度、块数、whole-payload SHA256、final chunk root），head 再绑定元数据 hash、序号和前驱。不列全部 chunk hashes，不拼接完整事件。

append 在 BEGIN IMMEDIATE 内验证旧前缀并流式写入 chunks，event 行最后写入，同一事务 COMMIT。关闭写连接后，新连接逐块重算整个 prefix，成功才返回新 head。read 使用一个 SQLite read snapshot，先验证全前缀再逐块 yield；event_metadata 只返回已验证的有界元数据。中途终止 reader 保守锁止 owner。

## 预算与失败

ChunkContentBudget 明确 max_events（最多384）、max_event_bytes、max_total_bytes，exact int 拒 bool，正值且小于 2^63；事件和累计预算包含元数据+payload。写前检查声明预算，消费过程中再次计数；SQL先查 count/sum/max(length)，再读取有界 blob。

这些是逻辑内容门，不包括 SQLite page/index/rollback journal/temp/fsync 复制、物理磁盘 reserve 或硬 quota，也不代表可以在本机存下 192h 的最坏内容。没有 native 调用、资源预留或执行授权。

stream异常、预算耗尽、数据库写入/commit/no-op/fresh readback 歧义与篡改均锁止当前 owner，禁止自动重试。若 commit 已成功而响应失败，调用方状态仍未知；没有独立新 head 就不能猜测后继续。此原语尚无 durable caller intent/ambiguous-commit 协调协议。head 仅用于完整性与独立旧快照检测，不证明来源真实性或抵御 hostile ABA。

## 验证边界

测试使用真实 SQLite SQLITE_LIMIT_LENGTH 降至约 1 MiB，验证总计 3 MiB 的事件可以分块原子写入、重开和流式读取；未实际写入 3.89 GB 或 754 GB。独立 hash oracle、chunk/descriptor 篡改、预算边界、单次消费、commit 前后故障与 fresh readback 拒绝分别覆盖。

ChunkInspection 的 content_verified 仅证明字节完整性，numerical_chain_verified / native_execution_authenticated / formal_result / formal_execution_ready 均 false，physical_space_reserved=false。不解释报告内部字段，不恢复 normal decision。

## 后续集成门

仍需逐阶段 raw report 的版本化流式 archive/replay、独立 intent/outcome 状态机与持久预约、source/normal 前驱绑定、按小时源重验，以及物理空间/commit/wall 资源合同。旧 replay_reports 的20-stage/32MiB域不适配本类型，不能直接放宽或冒充完成真实232-stage链。上一轮 one-BLOB blocker 对旧实现仍成立；本组件只验证分块替代方案的内容存储能力。


领域复核补充：后继接口应在每个 native stage 返回 raw report 后、下一阶段之前持久化完整 receipt，并绑定已提交 intent head、stage index/identity 和 request；sink 失败立即停止，后续 locks 不推进。尚未返回的报告必须保留 missing/unknown，不能补造。accepted 与 rejected 都保留实际返回的原始前缀。

现 replay_reports 同时限制20 stages和32MiB，request/chain身份也绑定短budget；即使真实232阶段恰巧小于32MiB，仍不能直接复用旧archive入口。后继必须有独立版本的stage-reference及replay类型，通过旧合成例等价性与新顺序/故障验证；复用数值predicate/assignment audit不等于放宽旧门。完整物理预算不得按内容去重扣减，也不能仅由此次小样例下调上界。

API 使用非重入 guard；迭代 reader 未耗尽/关闭时，其他操作立即拒绝，不等待同一调用栈释放锁。reader 全部耗尽后可继续读写；中断 reader 会锁止 owner，再 close 释放 lease。


后继具体集成边界：本384-event原语用于 hour-local archive（单小时 intent、最多232个 stage receipts 和 terminal），不承担192h逐stage日志。parent control journal分别保存每小时intent/terminal pointer与normal前驱；chunk head是存储证据进度，不是 completed_hours。新 full-hour archive header 需绑定 parent identity、intent head/hour、source/request/chain、完整stage order、network/spec及独立资源身份。

下一层应逐stage读取最多16MiB raw，按原数值predicate和严格assignment audit重放，locks只从前一已接受stage导出；最后才形成新projection。accepted terminal manifest+有序stage events构成新logical archive，不重新聚合成旧schema冒用。parent需fresh-open指定child head、零solver重放、再核source/前驱后才提交outcome pointer。若raw已经返回而sink落盘失败，必须明确raw incomplete与unresolved，不能宣称全部raw已保留。pending不重试，所有已提交前缀保留。
