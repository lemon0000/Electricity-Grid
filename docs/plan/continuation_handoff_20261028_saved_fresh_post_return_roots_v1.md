# F：finder认证完成，adapter根集合不符已保全

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[真实自然返回](continuation_handoff_20261028_saved_fresh_import_return_v1.md)与[NFC8合同](staged_deliverability_c_saved_fresh_post_return_admission_scope_v1.md)。宽goal持续active；本轮为progress，完整F未完成。Root唯一writer，wire_root_review仅只读PRE_SEAL，无official verdict、receipt或production seal。

## 当前端点与冻结记录

Root：`results/tables/staged_rts24_saved_fresh_nfc_v8_non_authoritative`，精确 **15文件/1191896B**。`checkpoint.json` SHA **39a8b3ac3e5ff68a5810b2d2809d3c16ca292b0ef0f76951a10d957206cd686e**；accepted=true仅接受失败元数据，**diagnostic_accepted=false**。size/register、20项unit、PRE_SEAL、startup/profile通过；唯一actual失败后停止，没有saved重放或重试。所有已执行source/scope/input及结果bytes冻结。

真实import仍在1344个guard-passed open后自然返回。新loader随后实际完成finder认证：observed=authenticated=2、pending=false；authenticate一次 **0.0023243999894475564s**，该失败路径finder_check共5次、6077个返回后active-hook idle getter事件、busy getter0，无reentrant fault/violation。此数量覆盖观测窗口中的getter，不能代替全部finder行为或registry内容证明。

接下来已读取adapter原始source并完成source_bytes bookend，随后primary为 **ValueError("fixed thirteen adapter function roots required")**。冻结adapter的实际AST是 **14个唯一顶层函数、2类**；旧helper写死13，与实际输入不符。14函数为：digest、sources、stamp、caller_image、capture、hold、bookend、project_metrics、validate_metrics、replay、_replay、validate_payload、bind_payload、compare_payloads。本轮没有修改adapter/Source49或放宽科学阈值。

未到before_adapter_roots，因此adapter graph、retention、boundary成功close、profile和OBSERVED均未执行。终态child exit1、runtime UNRESOLVED、boundary FAULTED、resource CLOSED；self close_calls=[1,1]、DLL directory closed，完整primary与LocalRuntimeUnresolved/BootstrapImportUnresolved secondary/cause保留。父端pipes/readers/writer/stdin/HANDLE全部关闭，无kill/timeout/truncation/reader或cleanup error。raw stdout4634B、stderr14491B；10个stage与18图对均可重开。18次均为namespace，2940 nodes/objects、376728B canonical image；这是图表示规模，不是retained heap或资源准入。

计数更正：NFC7原始17次图中，loader_ready之前15次，stop后cleanup2次；source_bookends=2是pre-import1+cleanup1。NFC8终态18图=15pre+source_bytes1+cleanup2；source_bookends=3=pre1+source_bytes1+cleanup1。旧交接关于“2个均为pre-import”的描述不准确，旧记录保持原字节。完整后继成功的名义目标仍为30图=21 namespace+9 adapter、source_bookends=5。

## 采样、预算与边界

本包startup已有独立native healthy采样；actual parent PID13468、child37728、原HANDLE572、80B结构，340 attempts/samples，无query/PID/handle错误或停止阈值触发。sampled peak WS：parent55091200B、child148250624B、同次pair203341824B；max private pair155705344B。receipt的memory_observation精确投影last_live_memory_guard child sampled peak。没有exit后补采；continuous_bound_verified、combined_retention_verified及resource_admission均false，不能推导128MiB retention、连续或descendants覆盖。

|阶段|charge秒|cap秒|
|---|---:|---:|
|size|1.8011126999917906|6|
|register|1.516805999999633|4|
|唯一20-node unit|9.368381000007503|16|
|PRE_SEAL|3.166471599994111|5|
|startup|3.8662386999931186|6|
|profile admission|3.049351800000295|5|
|唯一actual（失败）|7.795859499994549|30|
|saved|未执行|5|
|checkpoint|1.6780792999925325|4|

包static **22.87391959996603/65s**、unit **9.368381000007503/16s**，总 **32.24230059997353/81s**；余 **48.75769940002647s**留原包。累计static409.10023940002、pytest366.48897970000326、unittest123.12097659999927，总 **898.7101957000225s**，不接受 **38条**（新增唯一actual失败）。capture charge不含全部工程编辑、人工审查、Git或Python启动wall；模拟小时新增0。旧73文件5158740B加本包为88文件6350636B，均保全；不退款、重置或转用旧余量。

新registration：349 direct inputs、16 helpers、1099 effective union；SHA3ff3b3a13bad9c0e339340663a2d8dca06add8c7eb56c288d729c197d602b183，原始bytes少于756640B独立上界。唯一unit完整42帧、20/0/0/0、runner3.220s、PID39300/exit0、资源收尾完整；SHA b7a470adece75e25d48d638c8f07559a8074bcd70e28df7ff0e1cb9034dc7922。独立PRE_SEAL逐层重建1099有效闭包及Source49，零冲突/漂移，包含完整raw chronology正例/重排拒绝及external-read/close/finish故障反例。它不产生official状态。

command恰30000/30000 UTF16，size与register分别重算相等；stderr最坏上界28372/32768B、saved固定body3084/4096B。当前成功合同没有被实际满足，不能把20项unit或认证stage2当作整条成功。

## 下一步

先按[完整14函数集合后继草稿](staged_deliverability_c_saved_fresh_post_return_admission_scope_v2.md)建立独立NFC9：预期根集合用函数体内固定14-name literal，逐一源码compiled code/defaults/kw/closure/globals校验与2类/完整图保持；补完整loader的14根正例及漏/改compare_payloads反例。旧NFC8 helper、scope、失败和关闭的PID37728不恢复或改写。后继必须独立登记预算、输入闭包、constructor/oracle、unit与PRE_SEAL，再进行一次有界续接。

Source49 epoch仍 **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**。没有P1/实际role/OwnedChild/Job/F、模型或solver调用；全部native行为认证/科学/资源/正式/run权限仍false。当前无活动实验进程。39项并行文稿/插图/文献dirty保持；四导航只发布新前置段与原HEAD正文。最终Git同步状态以实际remote回读与本轮报告为准，不能称全局clean。
