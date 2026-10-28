# F：完整返回后通路OBSERVED并关闭

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[NFC8认证及根集合失败](continuation_handoff_20261028_saved_fresh_post_return_roots_v1.md)，实际合同为[NFC9完整14根scope](staged_deliverability_c_saved_fresh_post_return_admission_scope_v2.md)。本轮是progress，宽goal仍active，完整F未完成。Root唯一writer，wire_root_review只读PRE_SEAL及终态取证复核；无official verdict/receipt/production seal。

## 已实际闭合的端点

Root `results/tables/staged_rts24_saved_fresh_nfc_v9_non_authoritative`，**17文件/2285992B**。checkpoint SHA **5fb9c83a6ec9e7933e684a7f4ca2491fa52d9d7e1a6a8b7cc3740d9eb30428da**；accepted=true、diagnostic_accepted=true，范围仅packed metadata及post-return诊断。size/register、唯一21-node unit、独立PRE_SEAL、startup/profile、唯一actual、saved重放和checkpoint全部终态通过。已执行source/scope/input和结果bytes冻结，不能在原路径续写或重跑。

真实import在1344个guard-passed open后自然返回；其后实际完成finder observed2→authenticated2、pending=false、原Source函数14根逐一compiled metadata、2类shape、adapter graph、Source49 post/final bookend、retained sys.modules entries、boundary.close、两次profile一致及finish_import。**关闭前runtime=OBSERVED，最终runtime/resource/boundary全部CLOSED，runtime_was_live=false**。child exit0、primary=null、secondary=[]、self close_calls=[1,1]、DLL directory关闭；父端HANDLE/pipes/readers/writer/stdin全关闭，无kill/timeout/truncation/reader/writer/cleanup error。

新helper仅把旧“13个函数”错误块替换为函数体内固定有序14-name literal与14个唯一compiled roots；其余逐函数code/defaults/kwdefaults/closure/globals、2类shape及完整图检查原样保持。名称为digest、sources、stamp、caller_image、capture、hold、bookend、project_metrics、validate_metrics、replay、_replay、validate_payload、bind_payload、compare_payloads。旧NFC8失败保全；本轮没有改Source49、模型或科学阈值。

## 原始证据与实际调用量

Raw stdout **42375B**、stderr **16303B**；22 stages、30完整图对=21 namespace+9 adapter、13 census帧，canonical/pins/parser与派生记录精确对应。图interval与合同一致，0 unclassified，无stack。计数实测为authenticate1、finder_check10、adapter_check8、profile2、source_bookends5；返回后active-hook idle getter3968、busy getter0。该getter数量不等于全部finder行为。

namespace每图2940 nodes/objects、376728B canonical image；adapter每图137 nodes/objects、28501B。adapter首次freeze所在stage约0.008136s；后续8次check合计0.02237889998650644s、max0.0035613000072771683s。authenticate0.002384200008236803s，finder_check10次合计0.001088400007574819s，两个profile调用合计0.017699100004392676s。这些是嵌套观测bucket，不能求和充当整链分解或跨包加速结论；graph image bytes/strong objects也不是完整heap或retention大小。

`import_profile.json` **501203B**，与raw child profile pin、saved report pin及实际文件逐字节连接。core36.finish_import实际返回其内部使用的immutable observed raw，probe34要求它与先前CLOSED-boundary profile raw精确相等；成功exit0证明本路径比较通过。profile记录1918个sys.modules条目、cache165、paths6、finder types5；loaded_python_graph_attested、registry_contents_verified、native_behavior_verified均false。1918是条目/持有观察数量，不是完整Python图或独立TCB证明。

Source49 epoch仍 **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**。原bookend/graph计数误差的更正见NFC8交接；本次实测吻合30图与5次bookend。

## 采样、费用与保全

Actual parent-controller PID5088、child10148、原HANDLE620、80B结构，354 attempts/samples。native sampler/PID在kernel identity/direct child/guard/drained四处连接，parent PID三方一致。sampled peak WS parent56496128B、child153677824B；同次两个peak字段之和最大210173952B，private pair最大165154816B。receipt的memory_observation精确投影last_live child sampled peak。无query/handle/PID错误、over-limit或sample-limit，无exit后补采。

原每进程256MiB/pair512MiB只是本诊断sampled stop帽；continuous_bound_verified、combined_retention_verified、resource_admission=false。不能据此解释128MiB retained-root、连续/descendants覆盖或资源准入。

|阶段|charge秒|cap秒|
|---|---:|---:|
|size|1.8864330999931553|6|
|register|1.76088190000155|4|
|唯一21-node unit|9.785983099995065|16|
|PRE_SEAL|3.329841099999612|5|
|startup|3.9389981999993324|6|
|profile admission|3.0778957000002265|5|
|唯一post-return actual|9.761602399987169|30|
|saved replay|3.1979817999963416|5|
|checkpoint|2.0389736000070116|4|

本包static **28.9926077999844/65s**、unit **9.785983099995065/16s**，合计 **38.77859089997946/81s**，余 **42.22140910002054s**留原包。实际parent receipt **6.209745200001635/28.15886650000175s**，import census窗口约3.3709s；与外层actual phase分开报告。累计static438.09284720000437、pytest366.48897970000326、unittest132.90695969999433，总 **937.488786600002s**，不接受仍 **38条**。capture不含全部工程编辑/人工review/Git/Python启动wall；模拟小时新增0，不是科学实验运行时长。

旧88文件6350636B加本包为 **105文件8636628B**；原失败、余量和历史记录完整保留，无退款、重置或跨包转用。registration 349 direct/16 helpers/1110 effective，SHA63cc2c701444f3a63fb1f80d6636c74454c39c23a74c6a7dc4747ad83e5672e5；744249B小于745275B登记上界及786432B帽。command由本包size/register各自重算，恰30000/30000 UTF16；stderr理论28372/32768、saved固定body3084/4096。不能复用本次准入到任意新字节。

Unit完整44帧、21/0/0/0、runner3.548s、PID5768/exit0、所有捕获资源终态；SHA740f5605b99415c1c40d65f5836531e3757e46c8be1cba125d0379812722eaca。新增完整synthetic loader证明14 bindings与漏/改compare_payloads、default/kw/source-order拒绝；不执行科学函数body。真实adapter图/关闭则由本次actual单独证明。独立只读复核重建1110有效闭包，零冲突/漂移，重开17 root/map、raw/parser、profile与saved、采样/PID/投影和预算；must_fix_open=[]，但不生成official权限。

## 剩余关卡与恢复入口

本次是本地OBSERVED→CLOSED诊断闭合，**不是LIVE或F完成**。checkpoint的cold_import_acceptance_complete、independent TCB、all-unselected/任意RAM ABA/native effects及全部production/science/resource/formal/run/F字段仍false；也未调用P1/实际role/OwnedChild/Job、模型或solver。

下一步见[profile配对与LIVE准备草稿](staged_deliverability_c_saved_fresh_post_return_admission_scope_v3.md)：先审新case/参考profile provenance、DAG/调用量/资源和完整失败矩阵，再建独立后继。随后仍需producer binding、父端采用与资源/当前F完整闭包。不能从OBSERVED、auth2或saved metadata推导这些门槛已满足，不恢复已关闭PID10148。

当前无活动实验进程。39项并行文稿/插图/文献dirty保持，四导航仅发布新前置段+原HEAD正文；本轮最终Git hash与remote回读以实际同步报告为准，不能称全局worktree clean。scope_v2保留启动前合同标题/语境，实际终态以本交接与不可变exit/checkpoint为准，不回写冻结scope。
