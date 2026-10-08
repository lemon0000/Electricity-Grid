# H1 normal 短 episode 开发日志

状态：DRAFT_NONAUTHORITATIVE，2026-09-30。实现为 `normal_h1_episode.py`。
本组件验证已批准 v2 合同中 normal 链的调用生命周期；输入是调用方声明的当前观测。
不认证数据来源、历史 native 执行、共同发布、完整服务或最低容量。

## 状态与调用顺序

`DevelopmentH1NormalEpisode` 使用独立类型、SQLite application ID、数据库、schema 和 head 域。
不接受调用方传入的 before-state，不接受任意 archive 追加，也不继承共同 projection store。
复用本地 NTFS lease 与底层连接检查；目录必须以 `_non_authoritative` 结尾。

创建前核对完整计划：最多 24 小时、20 次 solver 调用、累计声明 solver 时间 60 秒。
每小时阶段数是 `1 + all_generators + committable_generators`，全部阶段预算一次预留。
这是声明的内容/调用预算，不是磁盘预分配或进程硬时限认证。

每一步按下列顺序执行：

1. 按独立保留的 exact head 回放所有历史；第一小时用声明初态，后续用前一 accepted 投影。
2. 只接收当前行与 raw workload；实际 source timestamp 必须连续一小时，time basis 保持一致。
3. 落盘 intent，绑定当前请求、source audit、前驱、chain identity 与预算；fresh connection 逐字读回。
4. 调用既有 owned H1 normal 链，保持原数值门；调用后不自动重试。
5. accepted 结果经完整 archive 回放，outcome 提交并 fresh readback，全部历史重放及最终实现检查成功后，才返回 accepted current result 并推进 normal 小时。

rejected/exception 返回 `None`，日志为 halted，normal 状态不推进。
进程中断留下裸 intent 时为 unresolved_intent；本 owner 的写入或读回异常使 owner 停止。
重新打开需要独立保留或显式只读恢复取得的 head；pending/halted 均不允许再次调用。
日志 head 的增加不等于 normal 状态推进。`complete` 仅指短 normal 计划完成。

## 证据与字节容量

每个事件是一份二进制 frame：固定魔数、8 字节元数据长度、canonical JSON 元数据、依序连接的原始 BLOB。
元数据中每份 BLOB 都绑定连续索引、长度与 SHA256；event head 绑定整个 frame。
多余、缺失、换序、改字节及非 canonical frame 均拒绝。事件作为一个 SQLite BLOB 原子提交。

accepted 保存既有 `archive_current` 原始字节（最多 32 MiB），重开时完整执行 `replay_archive`。
失败结果严格检查 exact result 类型、request/chain、stage 顺序、调用预算及负权限字段，
保存所有已返回且被旧 collector 接受的 native payload 原字节（每阶段最多 16 MiB）。
失败的 assignment audit 和 numeric predicate 仅保存派生摘要的长度与 SHA256，**不声称已回放或完整保存这些派生对象**。
错误序列及异常文本保存长度、SHA256、最多 1024 字节的 prefix 和 `complete` 标志；
异常 `str()` 失败时标记 `rendered=false`。UTF-8 surrogatepass 编码保留异常字符串的代码单元。
collector 内尚未返回的报告不可由本层恢复，调用数可能 unknown。

令 `H` 为计划小时数，`S` 为每小时阶段数，`C` 为总调用预算，
`M = 256 KiB + 14 bytes`（元数据及 framing）。内容容量在 native 前确定并绑定 header：

- 单事件容量 `M + max(32 MiB, S × 16 MiB)`。
- 全日志容量 `2H × M + H × 32 MiB + C × 16 MiB`。
- intent 的元数据在调用前通过 256 KiB 检查；失败 outcome 的固定字段与至多 20 组有界摘要落在该上限内。

这一容量覆盖受控 returned evidence，包括 accepted archive 因旧 32 MiB 门拒绝后保留的全部 raw reports。
它不保证物理 I/O 成功或无限异常全文保存；I/O 失败保持 unresolved，不转换成数值不可行。
失败诊断只接受严格结构和绑定检查，不重算失败报告的数值，也不认证其历史执行。

## 后续集成边界

此开发组件只拥有 normal 链。共同 key 的跨 episode 冲突、认证 source lineage、Rref/A 独立链、
三链持久发布、按需后续数据及完整支持 LB/UB 仍需后续集成。
该日志不能作为已发布的共同 N cursor 或正式运行授权。
