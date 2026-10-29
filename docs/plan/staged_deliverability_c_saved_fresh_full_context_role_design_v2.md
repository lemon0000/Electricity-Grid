# F：full-context role 八组机制修补 successor

2026-10-29，DRAFT_NONAUTHORITATIVE。沿用[八组机制设计 v1](staged_deliverability_c_saved_fresh_full_context_role_design_v1.md)的验收矩阵和边界，遵循[scope v2](staged_deliverability_c_saved_fresh_full_context_role_scope_v2.md)。root唯一writer、独立只读PRE_SEAL，无official verdict/receipt/seal。

v1登记后发现test01遗漏keyword-only `outer_deadline`；唯一26方法测试得到25正常、1 error，原流和11.672237799997674秒费用全部冻结。原v1 runtime/test/design/scope/driver/registration/unit/checkpoint和原WIP快照保持。v1 checkpoint只接受失败元数据，diagnostic_accepted=false；不把25项局部通过当八组完成。

新runtime v2与登记v1源码逐字节相同，保留六处内部与public无条件拒绝；仅test v2修正该调用参数并指向v2源码。私有AST副本/固定无import、空builtins target fixture、code/namespace/owner/clock/cleanup白名单及clone provenance保持。26方法、方法内有限反例及八组范围保持；每fixture一个内存child对象，0 child进程，只有一个普通unittest runner。

八组包括authority、role/context/deadline、partial launch、cleanup metadata/carrier/终态拆分、swallowed reentry、物理返回与G3提交失败保留、sticky/registry/emergency及fixed-window替换反例。真实entry/argv/channel认证、外部full context、Native清理class/helper图、audit hook、source-specific launcher/quiet等仍需后继实际来源实现。完整F、双侧真实B/C/E、P1/source成本和资源准入均未完成；NFC12复用现有证据，所有run/science/resource/formal/actual_F/adopted gates保持false。
