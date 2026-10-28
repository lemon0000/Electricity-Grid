# F：XZ启动进入payload，manifest helper配对拒绝已保全

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[消费接口开发交接](continuation_handoff_20261028_saved_fresh_consumer_binding_unit_v1.md)，本包冻结合同为[真实连接scope v2](staged_deliverability_c_saved_fresh_producer_binding_admission_scope_v2.md)。本轮是progress，宽goal仍active；完整F未完成。root唯一writer，既有wire_root_review只读PRE_SEAL，无official verdict/receipt/seal。

## 本轮端点

NFC11 root `results/tables/staged_rts24_saved_fresh_nfc_v11_non_authoritative`，**11文件1124554B**。checkpoint SHA **ffe8b099b75d997e6ce9c304db911071e559bb17179ddc1e0a6fb03e8e9e00f8**，accepted=true仅接受失败元数据，**diagnostic_accepted=false**。原128文件11375838B保留，连本包为 **139文件12500392B**。原Source49 epoch仍acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875。

唯一size/register及48/48 unit、98帧、独立PRE_SEAL通过。XZ参数固定FORMAT_XZ/CRC64/preset6，64MiB decoder/max_length131073，raw固定len/SHA、eof/unused/CRC及完整源码/位置AST/CodeType检查；全出口清理5个临时别名，DLL cookie双失败保原primary和cleanup cause。最终discovery/normal命令 **29956/29953 UTF16**，transport29632B/SHA **f337dc9c93dbee9eb449ac51c7d126948bd08dc96be233ed86f31c1cba193ff6**。最初30153/30150工程超帽候选及helper/transport原字节保存在transport_preparation.json，1.3473566s工程wall单列，不混入capture账。

**唯一startup discovery失败于MANIFEST。** 真实XZ child已解码并进入原payload，返回结构化failure report，但尚未生成startup_profile、SELF、namespace、adapter import或LIVE。primary为 `ValueError('fixed namespace helper reference')`。根因明确：冻结core38第130行仍要求 `staged_rts24_saved_fresh_entry_namespace_post_return_v1.py`，parent35第135行却选择 `staged_rts24_saved_fresh_entry_namespace_consumer_v2.py`。本轮48项单测覆盖logical consumer、codec及parser，没有将真实parent manifest交给core check_plan配对；不能再用单方schema检查代替这个连接。

Child PID23844/exit1，parent6632、原HANDLE548、80B结构、7个healthy native样本一致。stdout1633B/SHA **40afef05f9620bea40bdd0cb1088735e782dd5b582daa2aa7ce886e2e369fdad**，stderr0B。DLL cookie成功关闭；父端HANDLE/stdin/writer/pipes/readers全终态，无kill/timeout/truncation/reader或cleanup错误。Child没有self lease/runtime，self_handles_closed、runtime/resource phase均null，不能称其runtime CLOSED或LIVE。Receipt0.40838789999543224/3.4981729999999516s；phase2.912020699994173/6s，拒绝原因是配对，不是超时。

48-node unit runner15.821s，外层24.637472999995225/25s；PID40912、parent40876、HANDLE580、1213 native样本，原流/全部98帧和资源终态通过。外层成本明显含parent/child各两次全量check与collection；下一包复用未变更的48项证据，优先补少量真实配对测试，不重跑本包或自动扩帽。

## 预算与失败

|阶段|charge秒|cap秒|终态|
|---|---:|---:|---|
|size|2.7049627999949735|8|accepted|
|register|2.1671693000098458|5|accepted|
|唯一48-node unit|24.637472999995225|25|accepted|
|PRE_SEAL|4.687823100000969|5|accepted|
|唯一discovery|2.912020699994173|6|rejected|
|checkpoint|2.3395836999989115|5|失败元数据accepted|

本包static **14.811559599998873/80s**、unit **24.637472999995225/30s**，总 **39.4490325999941/110s**，余70.5509674000059s留原包，不转用。累计static488.3207191999784、pytest366.48897970000326、unittest182.8750850999968，总 **1037.6847839999784s**；受控不接受 **39条**，另保留工程命令超帽候选。所有旧预算/剩余/失败保持。未执行profile admission、normal、saved；其缺失是流程停止后的真实状态。新增模拟跨度0h；完整producer/P1/父端采用/能力/资源/科学/正式/run/F均未完成或false。

## 已准备的下一步（没有执行）

从[scope v3准备草稿](staged_deliverability_c_saved_fresh_producer_binding_admission_scope_v3.md)继续。core39、probe37、parent36已由 `experiments/staged_rts24_saved_fresh_consumer_manifest_transform_v2.py`机械生成：core修正唯一helper literal并迁移NFC12 root，probe/parent迁移对应root/文件；helper v2、codec、bootstrap、consumer验证、Source49和原NF9 profile不变。**尚无NFC12 driver、policy、预算登记、单测或child。** 这些代码仅prepare，不能称已解决真实连接。

新对话先核Git/进程和本交接，保留全部冻结字节。先写NFC12完整DAG/预算及合法证据复用规则，然后补真正parent/core manifest配对：discovery正例、旧helper路径反例、normal startup/reference/policy关系。对exact successor重新算完整命令、prefix/raw/code identity及停止/收尾成本。只有这些新准入通过，才进行唯一startup、原NF9逐字profile匹配和真正same-LIVE-owner consumer。原预测38图=25NS+13adapter、7次Source49 bookend、finder14/adapter12/auth1/profile2仍待真实normal验证，不能由本轮unit替代。

NFC11所有执行source/scope/inputs/results冻结，不修改、不重跑；Source49与39项并行文稿/插图/文献dirty保持。四共享导航仅发布新前置段+原HEAD正文；同步commit/remote以实际回读为准，不能称全局worktree clean。
