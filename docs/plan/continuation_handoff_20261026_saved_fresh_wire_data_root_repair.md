# C：wire 两项数据根风险修复检查点

2026-10-26，DRAFT_NONAUTHORITATIVE。接续[原WIP](continuation_handoff_20261026_saved_fresh_wire_data_wip.md)，沿用[原540s预算](staged_deliverability_c_saved_fresh_wire_data_scope_budget_v1.md)，具体语义见[修复说明](staged_deliverability_c_saved_fresh_wire_data_root_repair_v1.md)。root唯一writer；独立只读PRE_SEAL无两项风险的剩余必修finding，无official verdict、receipt或production seal。

## 已闭合的开发范围

1. contract factory和entry各自函数代码内包含五组长度/SHA literals；全pin globals、合同raw及自报commit同步替换仍拒绝。此结论不包含函数代码/require/sha256替换或任意RAM沙箱。
2. packet projection SHA继续核canonical raw；G0/hold/store/issuer依赖连接独立source_image_sha声明。bootstrap原schema没有source_image_sha，由三个固定startup join接收独立opaque声明并在本地immutable facts强持，下一角色核同一原join对象与声明；不补字段或反推物理真实性。
3. 三角色startup join核parent-private capture与child self proof、独立owner/thread、原25/19/19-token argv及list2cmdline、header/descriptor/时间序。独立stdlib物理slot夹具连通context→mailbox/ACK→controller→parent→fresh；原旧authority域与CLI保持关闭。

最终Source epoch：`e94eb34025ff99d52089ad0af304b17951603b749a0a36f60fa110eefdf61922`。同一Source版本531目标节点终态通过：51新＋480原回归；不是新模拟小时或真实F。新四组为r3_new_smoke/1/2/3（10/14/14/13）；原十组中expectation-a有效记录为r4_old_expectation_a_12，其余为r3_old_*。原定义/CLI AST、其他47个Source和4333历史路径保持。

## 账与失败记录

所有记录在`results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative/checks_01`；最终保存状态先读同root的`checkpoint.json`，再读`final_package_01`的freeze、saved/terminal报告及原exit。freeze是开发checkpoint索引，production_seal=false。

冻结前static累计38.4783401/120s、pytest累计288.2881149/420s，总326.766455/540s。freeze/saved/terminal继续从原账扣费，最终准确数值以checkpoint的全exit累计为准；不重置预算。费用是capture准备/执行/前后pins＋0.5s tail reserve，不包括全部编辑、review、Python启动和Git wall time，也不证明实际F资源准入或硬停止。

保留三次不接受终态及其完整原stdout/stderr和源码snapshot：原wip_static_02语法失败（2.9809804s）；r1_new_smoke夹具value(name)冲突（6.6945581s）；r3_old_expectation_a_12测试exit0但postcheck拒绝（25.3390577s；现场诊断为helper漂移，原exit未序列化after-helper map）。独立fixture修复后r2 smoke是旧test epoch，当前覆盖只计r3/r4终态。后者在不改Source下按原32s帽单组重核通过；原失败未改写。

## 下一步与保持的边界

继续前先核Git、实际source/helpers与进程。仍缺8个公开接口：validate_saved_stage_transcript_data、validate_saved_stage_failure_data、validate_saved_wire_failure_data、compose_saved_failure_event_data、validate_saved_controller_binding_data、validate_saved_controller_return_data、validate_saved_broker_return_data、validate_saved_constructor_diagnostic_data。逐边DAG反例、16帧stage/early failure、五类failure及JSONL预留、return/diagnostic矩阵也未完成。后续不能把此531节点当完整45域协议或actual F已完成。

后续沿剩余预算续账，先登记受影响Source与目标组；不要重放已完成的全部回归来代替新增行为证据。新Source不继承本epoch“当前通过”，历史snapshot继续保留。真实producer/retained owner/Job/bootstrap能力连接、33根runtime闭包/NumPy政策、source6500/180s、整链wall/RAM/storage和硬停止、actual fresh与最终父端采用均未建立。相关auth/读取/run/F/science/resource/formal状态保持false；本轮无新native、冷进程probe或模拟小时。

现场论文/文献/插图改动由并行工作保留。四导航只发布本轮前置段；共享README/20261022其余dirty正文不纳入本轮commit。最终Git哈希以实时读回为准，不能报告全局clean。

归档另见checks_01/retry_archive_reconciliation.json：原admission_retry.json实际被r4使用，但继承了r2/r1的旧provenance字段，原字节保持；reconciliation单独绑定真实r3计划、拒绝记录、r4 exit/harness和实际helper pins，不把旧字段当作正确证明。
