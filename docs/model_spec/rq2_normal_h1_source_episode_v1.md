# 来源绑定的 H1 normal 短 episode

2026-09-30，DRAFT_NONAUTHORITATIVE。实现 `normal_h1_source_episode.py`，保留旧 normal episode 与来源适配模块的字节。

`DevelopmentH1SourceEpisode` 使用独立类型、SQLite 文件、application ID、schema 与 head 域。
沿用已有 normal 数值链、archive replay、binary codec、失败摘要和本地 NTFS lease；
来源凭据与 normal intent 放在同一 BLOB、同一 SQLite 事务中。

header 固定静态网络、DC bus、solver/小时/总预算、来源 origin declaration、绝对 upstream/config 路径、
source-binding 及所有相关实现身份。每次连接、提交前后和回放末尾重新计算 header 并核对。
origin 包含 split、两侧起始 raw index、power outage seed 和 config SHA256，属于开发声明，不是登记选择证据。

## 当前来源与前驱

`step` 只接收独立保留的 `expected_source_identity` 和 `expected_head`，不接受 row、workload 或 declaration override。
owner 用 `origin.power_raw_hour + completed_hours` 与 `origin.workload_raw_hour + completed_hours` 重载当前来源。
重载调用已有 pinned loader，复核当前 receipt identity、静态网络与字节上限。
两侧必须持续处于各自同一条已验证 source chain；power timestamp 每次前进一小时且 time basis 一致。
workload 仍使用独立边际坐标，不推断共同观测时钟或联合概率。

intent 同时记录 source binding identity、原始 audit bytes、canonical observation、normal before/audit/chain/request identity 和调用预算。
只有 intent 提交并 fresh readback、重新加载来源和前驱回放成功后，才调用 native。
恢复时每个 intent 都重新从外部 pinned 文件加载当前 receipt，与持久 pin、audit 和 observation 精确核对；
只使用重建后的 observation 组装 H1。来源标签和 audit 不进入 normal 计算键。

accepted outcome 需通过原 archive 完整数值回放、提交/fresh readback 和最终来源及历史复核，才返回 decision 并推进 normal。
rejected/exception 返回 `None` 且 halt；pending 不重试。
intent 之后的来源或实现漂移会拒绝继续执行或返回 decision；提交/读回/历史复核异常锁止当前 owner。
solver 返回后才发现来源变化时，已写入的 outcome/native 证据保留，接口仍失败；
重新打开需独立核对的 head 和可重建的原始来源。

## 容量与范围

沿用最多 24 小时、20 次调用、累计声明 solver 时间 60 秒的短开发预算。
每个 source audit 最多 256 KiB，原字节保存，超限在 intent/native 前拒绝。
令 `M=256 KiB+14 bytes` 为 binary framing 和元数据上限，`H` 为计划小时，`S` 为每小时阶段数，`C` 为总调用预算：

- 单事件内容上限：`M + max(32 MiB, S×16 MiB, 256 KiB)`。
- 全日志内容上限：`2H×M + H×32 MiB + C×16 MiB + H×256 KiB`。

这些是内容容量及 solver 声明预算，不是物理磁盘、来源扫描或进程硬资源保证。
来源/mapper 在 intent 前拒绝时，不写 intent、不预留该小时调用；既有历史损坏或漂移则锁止 owner。

inspection 的 `source_bound_hours` 包含已验证的 pending/rejected intent，只表示已绑定来源的尝试数。
`complete` 只表示短 normal 计划完成。source_authenticated、selection_registered、native_execution_authenticated、
formal_result、published、complete_service_certificate 均保持 false。
日志依赖外部 pinned 来源，不是自包含来源认证，也没有源文件 writer lock 或 hostile ABA 保证。
共同 key 冲突发布、Rref/A 三链、正式 E/F 登记与按需后续、完整支持 LB/UB 及运行资源门仍待集成。

## 固定真实网络的资源边界

零 solver 来源盘点：固定 RTS 网络有 158 台 generator，其中 73 台 committable，
按已批准 H1 阶段次序每小时为 `1+158+73=232` 个 native stages。
当前短开发入口的 20 次调用门会在构造 owner 时拒绝该网络；通过 native 执行验证的是小型合成 source-bound episode。
固定真实来源目前只有零 solver 读取及资源结构检查，尚无本组件的真实 episode/native 运行。
完整 192 小时的朴素阶段数为 44,544，这不是实测时间、算力可行性或运行授权。
真实执行需后继资源合同和验收门；保持本组件短门，不将当前测试解释为真实 192 小时可运行证明。
