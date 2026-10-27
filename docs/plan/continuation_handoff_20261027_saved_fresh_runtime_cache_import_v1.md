# C/F：cache候选已接入cold，完整import仍未返回

2026-10-27，DRAFT_NONAUTHORITATIVE。接续[cache方法交接](continuation_handoff_20261027_saved_fresh_cache_path_v1.md)，执行合同为[RCI范围](staged_deliverability_c_saved_fresh_runtime_cache_import_scope_v1.md)。root唯一writer、独立只读PRE_SEAL，无official verdict/receipt/seal/run authority；宽goal继续active。原所有代码、结果和失败字节冻结。

## 本轮实际进展

新core14/probe11/parent11已成组迁根至RCI，import_helper绑定冻结`bootstrap_import_cache_v1.py`；namespace timing1、Source49、4745B policy和阈值保持。登记先重核前驱cache-path全部pins、8/8、threshold met、candidate_adopted=false、helper exact SHA和总账626.5458606/count22。新命令**29560/30000 UTF16**。

5/5 unit终态通过，0 failure/error/skip，charge**1.3739181/4s**；child exit0未kill，HANDLE/pipes/readers终态，peak working set44376064B。AST仅豁免已由前驱snapshot锁定的_check_cache；codec逐字节、位置AST、CodeType及实际manifest helper path/pin均检查。真实startup discovery和profile admission通过。终态checkpoint脚本还在pre_seal_findings中预绑定exact pin，执行时与报告三方相等；没有只靠事后自pin。

唯一actual import诊断仍未在预算内返回：

- controller **7.6517996/8s**；内部parent **7.1657612/7.6430518s**。这些是不同capture边界，不是模拟小时，也不是完成时长。
- 仅有`loader_ready`与`before_adapter_import`，没有return/后续stage。child被预算kill，exit1，stdout0，无child report。
- stderr **1300B**完整保全，capture未达帽截断；2s watchdog自身的栈输出是残片，顶部为冻结importlib的`_path_stat → _path_is_mode_type → _path_isfile → find_spec → _get_spec`，末尾停在不完整的`File`行。外层import_module及依赖名没有出现在这份残片中，不能补造。
- Parent HANDLE/stdin/writer/pipes/readers均终态，无writer/reader/cleanup错误。child self-close、实际cancel及child内部资源收尾仍未知。

因此，方法级13.6%局部收益尚未转化为完整cold import完成证据。不能由采样位置变化推断cache瓶颈已解决、import更深入、普通I/O占满全时或整体提速。RTI2与RCI均被预算停止，不能拿约7.18与7.17秒作完成时长比。`import_timing accepted`仅表示这次partial取证与父端收尾符合诊断合同。

## 保存与预算

root `results/tables/staged_rts24_saved_fresh_rci_v1_non_authoritative` 为**24文件/574470B**，在24files/4MiB内，不再添加。依次读registration、unit records、pre_seal_findings/admission、discovery/profile records、probe_import_discovery.receipt的raw stderr、saved_report及checkpoint。checkpoint map精确绑定其之前23文件；`experiments/staged_rts24_saved_fresh_runtime_import_timing_checkpoint_v2.py`预绑定pin匹配，charge**0.3931935/1s**。checkpoint在saved之后，不反称原saved.exit已绑定它。

RCI含checkpoint累计static**10.83317019999231/18s**、unittest**1.3739180999982636/4s**，合计**12.207088299990573/22s**。全历史static**217.91821880000793**、pytest**366.48897970000326**、unittest**54.345750399999815**，总**638.752948900011s**，意外不接受仍**22条**。预定预算停止的partial不改记为import成功，也不删除旧失败；旧120/540/import8MiB超帽保留。编辑/审查/Git、Python初始启动及最终exit序列化不计capture，不是完整wall；无模拟小时推进。

Source49 epoch **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**及49个原字节不变。新pins仍是当前字节承接，不是独立expected truth或native认证。39项并行文稿/图件/文献dirty保留，只发布本轮范围及四导航新增段。独立只读PRE_SEAL最终复核未发现must-fix。

## 下一步与完成条件

先核Git/process和RCI checkpoint/raw/Source49/helper pins。cache1只在本诊断被测，`cache_candidate_adopted=false`保持；不原地重跑、不扩大8秒帽、不重复单个watchdog样本等成功。

下一项应先用有限的新取证设计拆分selected audit内部成本，记录真实调用数和有界分段成本。可在_audit_entry原相邻语句间计identity第一遍、cache、globals/attrs、ownership（含第二遍identity）、image+digest、machinery，另记_audit总inclusive；不能把总计与子项相加。import窗口减guard只能称outside-guard残差，仍含module/native/其他hook/调度与观测开销，不能直接标为I/O。

优先设计固定selected-open前缀与低频聚合frame，计数从真正import前启用，避免再次只测前置。达到预登记次数后才主动诊断停止，wall帽仅作兜底；完整guard检查须先完成，不能为诊断新增policy放行分支。保持primary异常顺序，保存最后完整prefix、在途计数及未闭合段。clock/encoder/write/flush根、诊断observer顺序和metadata、固定聚合器身份与数据的信任边界均须先审查；统计不参与授权或每次重做authority commit。诊断自身I/O与新增binding成本计入。当前两份单点栈不足以决定下一项整体优化；先固定问题、次数、预算/终态与独立PRE_SEAL，再执行新的有界scope。

完整import后仍有明确的下一验收链，当前未实现：core14.finish_import只在boundary CLOSED、原adapter/bindings/retention及Source49书挡通过后，profile=None才OBSERVED；固定profile原raw逐字匹配才LIVE。probe最后会cleanup，所以成功discovery最终报告应为runtime CLOSED、was_live=false。RCI driver尚无import_admission/normal；parent完整分支只验证嵌入profile，不保存import_profile.json。未来应从真正完整的child report提取canonical raw/pin，独立做profile admission、固定profile正常LIVE与完整cleanup，再处理故障窗口；不能从partial stage/stack、startup、方法unit或父端收尾合成CLOSED profile。

E/U、独立TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false。完整B_S import、M/D与NumPy政策的此runtime闭合profile、native cancel/完整收尾、实际producer和F仍OPEN。
