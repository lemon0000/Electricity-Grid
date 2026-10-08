# H1 持久调用记录与逐阶段采集器

状态：DRAFT_NONAUTHORITATIVE，R3 PRE_SEAL_AUDIT 有待闭合的 parent anchor 问题。公开 `run()` 暂时拒绝执行；私有测试入口仅用于 mock adapter 的零 solver 控制流验证。

`normal_h1_stage_collector.py` 将已验证的增量 stage archive 接到内部 `capture.solve_once`。独立 collector declaration 绑定当前 packet、前驱、相对小时、source/parent 引用、完整 objective slots、旧短求解预算、solver specification、replay limits 与实现身份。实际后续 stage identity 由前一份 durable receipt 的 canonical locks 推导。

outer registry 复用 chunk journal，容纳 intent、每阶段与 terminal 写前 checkpoint、outcome，完整链最多 n+3 个 metadata-only 事件。child 使用独立 collector binding，并保留每阶段一份 raw 加 terminal 的格式。intent 登记 child identity、genesis、绝对目录及内容预算。checkpoint 在 child 写入前持久登记 previous/expected child heads 和 raw/metadata hashes；expected head 由已审 raw 与元数据机械计算。每份 raw 必须经过增量 archive 的审计、提交、fresh readback 和二次语义审计，且实际 head 与 checkpoint 相同，下一阶段才能取得其 locks。

控制流仅允许新建 owner 尝试一次。同一 registry root 的重复创建由 create-new 和 NTFS lease 拒绝；重开的 owner 仅能审计，不能续跑或补写 outcome。给定独立 registry anchor 后，重开可只按末 checkpoint 登记的 expected/previous 两个 child heads 完整核验，不读取未登记的 tail 作为可信 head。无 outcome 时一律 pending_unknown，solver_calls 为 null，不能交付 projection；即使 child 已有完整 terminal，也不能推断调用记录已成功完成。已持久 rejected raw 可记录 rejected outcome，并停止调用。异常或提交歧义锁止 collector，保留现有字节，不自动重试。

待闭合根锚点：每次 registry 更新后，parent 必须原子持久并 fresh 验证最新 registry head，之后才能首次调用、写 child 或交付 outcome。现有测试显式保存独立 registry head 以验证 child 的两状态恢复；这不是 parent 集成证据。公开 execution 门保持关闭，直到接入具有独立身份和持久 receipt 的根锚点。

这里的去重范围是一个 registry root；跨 root 的同一请求去重与统一总预算必须由后续 source-normal parent registry 实施。parent/source 引用尚未独立认证，不声明真实调用历史认证。完整 child terminal 重放通过后才允许 outcome；outcome fresh 验证后才能返回 accepted。

本版严格沿用旧 H=1、最多 20 calls、最多 60 solver seconds 的开发门。真实 RTS 232-stage 链仍在创建目录之前被预算门拒绝。逻辑内容预算不代表物理磁盘 reserve 或进程资源准入。正式实验、source-normal 父集成和共同前缀发布均未完成，所有相关 formal/published/authenticated 标志保持 false。

开发测试使用固定哈希的既有三阶段报告，mock 内部 adapter；没有新增 native 求解。这验证持久化与调用顺序的控制逻辑，不替代实际 native 集成和进程故障实验。
