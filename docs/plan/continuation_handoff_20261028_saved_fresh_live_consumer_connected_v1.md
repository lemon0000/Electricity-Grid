# F：真实同一LIVE owner完成binding消费并关闭

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[NFC11 manifest拒绝交接](continuation_handoff_20261028_saved_fresh_consumer_manifest_rejection_v1.md)，冻结合同为[scope v3](staged_deliverability_c_saved_fresh_producer_binding_admission_scope_v3.md)。本轮progress，宽goal仍active，完整F未完成。root唯一writer，wire_root_review只读PRE_SEAL及终态重开；无official verdict/receipt/seal。

## 已实际接通的边

唯一NFC12 normal重新bootstrap真实child，同一native self owner完成namespace transfer、B_S import及原NF9 profile精确匹配，进入LIVE；此前IMPORTING/boundary CLOSED阶段建立的consumer plan用于实际调用原ENTRY `_expectation_binding_entry`。六adapter成员连接原14-root tuple、四leaf从prepare起强持，返回对象确为原adapter；消费前后plan/runtime/Source49检查后，状态CONSUMED，再完整关闭runtime/resource/boundary。只有成功close后返回bounded canonical data；父端逐原流与上下文核验。

这次是真实same-LIVE-owner binding consumer连接，不是logical fixture。**consumer_result.same_live_owner=true、consumer_return_is_adapter=true、binding_members=10、consumer_state=CONSUMED**，runtime_phase_before_close=LIVE，最终runtime/resource/boundary=CLOSED，primary=null、secondary=[]，self close_calls=[1,1]，live_at_report=false。所有producer_capability_verified、full_P1、角色/permit/OwnedChild/Job、完整runtime/独立TCB/native行为、资源/科学/正式/run/F权限仍false；尚未调用P1 capture或完成父端科学采用。

Actual共38图对=25 namespace+13 adapter，76 graph帧、22 stages；7次Source49 bookend；auth1、finder_check14、adapter_check12、profile2，idle getter4013、busy0。阶段分布与scope预测一致，prepare位于after_boundary_close、consume及内部close位于after_finish_import，最后probe close幂等无新图。原NF9 profile **501203B/SHA a61fb973180f4031ebc024bb69ab162460955594c4bb53cc182d3da70559d3b6**逐字相等、diff=[]，参考未重算；parent reference-before=after=derived context，完整saved canonical replay与checkpoint闭合。

## 不可变端点与保全

Root `results/tables/staged_rts24_saved_fresh_nfc_v12_non_authoritative`，**16文件1849773B**。checkpoint SHA **bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de**，accepted=true、diagnostic_accepted=true，范围 `packed_metadata_and_connected_binding_consumer_diagnostic_only`。1167 effective inputs、20 helper pins；前驱139文件12500392B保持，连本包为 **155文件14350165B**。Source49 epoch仍 **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**。全部执行source/scope/inputs/results bytes冻结。

Core39将固定helper精确更新为consumer v2，并把真实固定startup path提前加入check_plan，路径与early audit/verify_startup_profile一致。parent36每次返回实际manifest前调用该Core check_plan、helper/policy read_file、normal startup/reference pin关系检查；错误不进入Popen。constructor逐字重建Core/Probe/Parent；全部LocalRuntimeInputs方法在同虚拟filename下CodeType相等，未改变已验证消费/关闭行为。XZ codec、namespace/bootstrap helper、consumer validator、memory actor和原reference保持前驱字节。

本轮只新跑 **3/3补充测试、8帧、0failure/error/skip**，runner0.904s，外层9.755853599999682s。测试涵盖实际discovery/normal parent→Core配对、旧helper/错pin/错policy/bootstrap拒绝和真实固定startup path；normal仅用真实路径的metadata读取overlay，不向实际root发布fixture。旧 **48-node证据仅复用**：原完整98帧、原exit pin、未变helper/方法代码及依赖closure重新核验；不是本轮重跑48项。

## 实测资源与费用

Normal parent36548、child35984、原HANDLE564、80B结构，465个healthy native样本。Raw stdout43199B/SHA **5eb8ae3c590d37da315f9d52c70316ece3d61b14b17e1284e05c4f1447c4a66d**；stderr17178B/SHA **6ee04ce2cfc867e3c3aa7d1de18989b1dc268eeab663e37f4a2b8fc044c58f33**。Receipt8.20975449999969/27.38172279999708s；child exit0，DLL cookie和父端HANDLE/stdin/writer/pipes/readers全部终态，无kill/timeout/truncation或cleanup/reader错误。

采样peak WS parent98635776B、child184311808B，同次两个peak字段之和最大282947584B；仅为本包256MiB/process、512MiB/pair采样停止帽内观测，非连续、descendants或128MiB retention证明。Startup child19120/parent40308、HANDLE564，14 healthy样本、receipt0.5723689000005834s；模块名到lzma/_compression/_lzma/hashlib/_hashlib origin、pyd及liblzma/libcrypto native边界/pins通过，仍属conditional TCB。补充unit child28596/parent10216、HANDLE564、319样本及完整收尾通过。

|阶段|charge秒|cap秒|
|---|---:|---:|
|size|2.5829377000045497|10|
|register|2.261878000004799|6|
|唯一3-node unit|9.755853599999682|12|
|PRE_SEAL|4.672916900002747|7|
|唯一discovery|5.468718900010572|8|
|profile/reference admission|4.565730299989809|8|
|唯一normal|13.545977999994648|30|
|saved|4.8741563000075985|8|
|checkpoint|3.5797400000010384|6|

本包static **41.55205610001576/100s**、unit **9.755853599999682/15s**，总 **51.30790970001544/115s**，余63.69209029998456s留原包。累计static529.8727752999941、pytest366.48897970000326、unittest192.63093869999648，总 **1088.9926936999939s**；受控不接受仍 **39条**。NFC11 manifest失败及工程超帽候选、所有旧预算/剩余完整保存，不退款、不重置、不转用。受控费用不含工程编辑/人工复核/Git/Python启动wall，新增模拟跨度0h。

## 继续推进的位置

先核本交接、Git/进程、当前计划/阻塞和agent.md第7–9节。当前连接已关闭，不能恢复旧PID、由JSON摘要发行能力或复用已消费owner。任何后续真实消费必须在新的合法bootstrap内重新建立LIVE owner，复用本包已证明等价且仍fresh的代码/证据。

下一实质目标是完整producer与父端采用。先审现有ENTRY `capture_saved_expectation`和实际父端接收/采用入口：旧capture仍自行调用 `_expectation_adapter`、读取anchor/P1及53条数据，不能直接把本轮10-member binding-summary当成完整producer/issuer闭包。应明确如何在同一LIVE owner下建立真实数据、固定依赖和源/状态、提交/失败收尾及父端reopen replay边，再登记全路径调用量、I/O/内存/存储/时长与许可边界。若需改变Source49、P1读取、actual role/native校准/模型/solver/长实验，遵循原冻结合同和现有明确授权；先做可审实现和准入，不能从本包诊断自动推出权限。

33个legacy root catalog的replacement/能力状态仍原样，不因当前真实binding消费就全部闭合。资源和128MiB retention、完整P1/permit/科学采用/正式F仍OPEN或false。保留所有失败与旧source，不重跑NFC11或NFC12；后继复用这次真实连接与失败记录，避免重新付费验证已闭合且未变的步骤。

Git仅同步本轮已审范围；四导航用新前置段+原HEAD正文暂存，39项并行文稿/插图/文献dirty保持。最终commit/remote hash见实际同步回读，不称全局worktree clean。
