# F：完整继承关系的单次live pin核验

2026-10-29，DRAFT_NONAUTHORITATIVE，未登记。完整目标、36-node矩阵、Source49/权限/TCB与输出/资源停止条件沿用[整体合同](staged_deliverability_c_saved_fresh_producer_bootstrap_scope_v1.md)和[builtin后继](staged_deliverability_c_saved_fresh_producer_bootstrap_scope_v4.md)。root唯一writer，retained_lifecycle_review只读PRE_SEAL。

v4登记计算完成后以5.557246700016549s超过原5s帽拒绝；没有unit启动。原helper v2、graph v3、LC2、B_Sv3、tests v3以及scope/driver/result字节均冻结。拒绝root3文件354753B、checkpoint1f4b84d2ace32a072b9407c021aae7503f3f211ec90b59ef55eec28b13236325、包7.366585600015242s完整保留，不提高原帽或退款。

本后继仅优化controller前驱重建。以固定SHA checkpoint为根，读取其pin绑定的完整registration payload（expanded1249，非NFC12的直接360 map），再用固定SHA的v3 checkpoint及其绑定完整registration（1242）显式重建v3 expanded+root4→1245，加入v4 own12→1249及archive188+4→192；要求与v4完整maps逐项完全相等。加入v4 root3形成本包继承1251及archive195。所有selected输入/归档live文件依旧逐一hash验证，重复路径pins冲突、路径alias、缺项/多项、count/bytes或固定anchor差异全部拒绝。减少的是递归执行历代controller所造成的重复读取，不减少当前完整集合及live freshness要求；保留完整旧链字节和失败。

登记前须以旧递归v4.previous()加其own/root独立重建同一完整map，与新previous逐项比较，并做map副本删除/添加/改pin的拒绝检查。哈希固定的旧complete expanded registration承担其历史集合证据，不称该复用为新的actual运行或独立TCB认证。

新账源固定上述v4 checkpoint，累计static586.8018303000529、pytest366.48897970000326、unittest246.0680770999934，总1199.3588871000495s，不接受45条。新包自身0，未登记；所有旧费用/失败不退款、重置、转用。

继承1251、自有12、重叠10，精确1253 inputs；archive195文件/19496035B。实现/测试全部复用v4冻结字节，本后继仅新controller/scope。DAG仍register→唯一36-node unit→独立PRE_SEAL保存→saved→checkpoint→Git；失败即停止并保全。

预算static25/unit15/40s与5/10/5/5/5s不变，其余5static/5unit只作同包失败保存。child≤8s、-B/-s/-S、stdout128KiB/stderr32KiB、256MiB/process/512MiB/pair sampled；root≤10文件/4MiB、record≤1MiB并预留checkpoint1MiB，所有false gates/未知域拒绝保持。费用只计受控capture，额外机械对照、编辑、审查/Git不冒充受控阶段费用。

真实37模块/Source49目标模块/P1/issuer/角色/native校准/模型/solver不执行。Core/probe/parent/manifest/profile/旧40图帽后继、父端reopen replay、128MiB retention及whole workflow/F继续OPEN；完整目标不因本包逻辑验证而完成。
