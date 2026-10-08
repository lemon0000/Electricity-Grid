# H1 受控增量阶段存档（开发）

状态：DRAFT_NONAUTHORITATIVE。只读独立 PRE_SEAL_AUDIT 未发现阻断项，无 production seal 或 official verdict。

`normal_h1_incremental_archive.py` 复用已封存开发版 chunk journal 的物理表结构，采用独立高层 schema、实现哈希与 binding identity。旧 hour archive 无法按旧身份打开新存档。输入、数值谓词和 assignment 审计沿用既有 hour replay；不改变科学验收门槛。

活跃 owner 持有 NTFS 排他 lease 和一个持续 SQLite writer connection。初始化从完整持久 prefix 重建缓存。每次写入检查该连接的 `data_version`、`total_changes`、精确 schema/header、累计计数和末事件；同连接自己的提交不改变 `data_version`，其他连接的提交改变它。创建空库时实测这一语义，重开不执行探针写入。该协议检测普通 SQLite 并发提交，不提供 hostile raw-file/ABA 保证。

每阶段顺序为：审计当前 raw → 原子提交 chunk/event → 重新取得写锁 → fresh connection 复核新事件、全部新块及累计计数 → 重新审计读回的当前 raw → 推进 canonical lock。释放保护写锁后再次检查 epoch。每个阶段只进行两次当前阶段数值审计；不重新读取旧 raw prefix。SQL 累计计数仍访问表，因此不能把这个性质解释为所有操作均为常数成本或完整资源准入。

任何 commit/readback/语义复核异常同时锁止高层和底层 owner，不返回可继续执行的新 head。报告数值拒绝保留其 raw 并终止阶段推进；模型、资源和实现异常不改写成数学不可行。终端将持久 raw 完整重放结果与缓存逐字段比较，并完整重算 projection；当前终端路径保留三次完整重放。重开与 inspect 均执行完整验证。

该类接收已有 raw bytes，尚不证明 native 调用时序。采集器逐阶段持久化集成、父 intent/source-normal 验证、物理磁盘和进程资源准入仍待完成。`source_authenticated`、`native_execution_authenticated`、`parent_intent_verified`、`published`、`formal_result` 和 `formal_execution_ready` 均为 false。真实 RTS 232-stage 数值链未运行；旧短求解门保持原值。

验证使用固定 SHA 的既有三阶段原始报告，零新增 solver。定向 15 项通过（30.92s），incremental/hour/chunk 相关 103 项通过（83.98s）。独立审查复核代码与规格，未重复运行上述测试；结论与文件哈希记录于机器可读 development checks。
