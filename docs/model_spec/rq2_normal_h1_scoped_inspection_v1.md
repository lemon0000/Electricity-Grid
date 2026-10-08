# H1 有界审计作用域与来源父控制器 successor

状态：DRAFT_NONAUTHORITATIVE；R3 PRE_SEAL_AUDIT 实质 findings 已闭合，无 production seal 或 official verdict。独立审查者只读复核实现、测试与产物，未重复运行测试或求解器。

`normal_h1_scoped_child_inspection.py` 为已有 anchored collector 提供独立类型的审计入口。构造与首次 `inspect` 共同组成一个作用域：保留 persistent SQLite writer 和排他 lease，构造期在 `BEGIN IMMEDIATE` 下完整重放全部已有 raw；首次 `inspect` 消费私有、归属特定 archive 的一次性 token，并重新验证实现、请求、来源 audit、cache 摘要、文件身份、连接身份、data_version、total_changes、schema/header、head/count/tail。token 带消费标记，重新挂回旧 token 仍拒绝。任何失败 poison owner，不能交付 projection 或重试。

基类早期构造使用私有 sentinel 暂存，紧接着必须完成锁保护的完整 replay，并验证 exact incremental inspection 类型，才可结束子构造。构造异常释放连接与 lease。后续 `inspect` 始终重新完整重放；没有进程全局 identity cache、跨作用域结果缓存或旧 stage 审计删减。

这里 inspection-only 指 API 不提供 create、append 或 native run。底层沿用可写 SQLite 连接和 `BEGIN IMMEDIATE` 写锁，**并非操作系统级只读**。持久化格式、旧实现字节、root 信任边界不变。仍须完整验证 anchor、registry、全部 checkpoints 和 child terminal；pending 的 previous/expected 两种 child head 分支均沿用旧解释。新 `H1ScopedChildAudit` 绑定 auditor identity，内部 inspection 的真实性、正式结果和发布权限均未提升。

`normal_h1_scoped_source_episode.py` 是独立声明身份的父控制器 successor。新执行 child 仍走旧 anchored collector；fresh reopen 走新审计器，adapter 精确核对外层 receipt 类型、auditor identity、内层 collector inspection 类型及全部权限标志严格为 False，再交回旧父逻辑。父 outcome 前的 fresh reopen、来源重载、逐字段一致性、before 私有重建、pending 不推进不退预算规则均保留。旧父不能误认新父 namespace，反向亦然。

性能诊断使用保存的合成 raw，禁止 solver 调用。两小时旧父 profile 在构造、inspect、close 中对 6 份 raw 调用了 48 次 `_audit_stage`，观测到 7170 次 dependency version 查询。instrumented wall 27.42s 是本机单次测量。新旧 child 对比使用同一保存小时，核对逐字段结果、审计次数和旧产物哈希；结果见开发记录。重复重放减少不等于真实多日硬资源准入。

同一三阶段小时的新旧对照中，完整阶段审计次数由 12 次降至 3 次，结果逐字段相等；instrumented wall 分别 6.52s 与 2.57s。旧 collector 20 个绑定文件零漂移，新增 solver 调用为零。单次、固定顺序、本机 profile 存在测量及缓存效应，不能作为通用加速比或多日资源上界。

最终 child 定向 11 项通过，覆盖 accepted/rejected、checkpoint previous/expected/terminal pending 等价、构造异常资源释放、一次性凭据重用、漂移拒绝及第二次完整 replay。该轮联合测试为 14 passed/1 failed，失败是父隔离测试未创建临时目录；修正后父 6 项与 incremental/hour/chunk 相关 103 项合并运行，109 passed（204.60s）。父测试覆盖显式内外类型/身份/权限 gate、新旧声明隔离、pending 预算保留及每次恢复的完整 child replay。所有测试使用保存 raw 或拒绝求解入口，无新增 native solve。

该修改仅消除单次新建 child 审计作用域内的重复数值重放。父级 prefix 仍逐小时完整恢复，依赖身份仍重复计算。真实 RTS 232-stage 执行、跨 namespace 请求去重、Rref/A 共同发布、全支持 LB/UB 与正式实验仍待完成；旧短求解预算保持原值。
