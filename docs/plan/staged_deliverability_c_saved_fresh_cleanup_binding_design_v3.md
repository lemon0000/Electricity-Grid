# F：cleanup binding successor v3

2026-10-30，DRAFT_NONAUTHORITATIVE。root 唯一 writer，独立只读 PRE_SEAL。接续[设计 v2](staged_deliverability_c_saved_fresh_cleanup_binding_design_v2.md)，保留全部失败和原科学合同。

validation_methods = 69; integration_methods = 11; canonical_frames = 140

v2 唯一轮69方法为63正常、1 failure、5 error。Core32与role26全过；5 error来自role `pin(raw)`返回tuple而新增CORE_CLEANUP_PIN为dict，比较恒false。后继role5仅将该常量改成 `(98453, 'ea92529f8bf2792367bc961d3464309dd2892afc53ba0ada1f9833c41f49ca20')`。Core49与Core47/48字节相同，固定anchor/journal/cleanup机制不改。

1 failure来自原SPEC call_offset2018未被opcode tracer命中。保留为locator失败，不解释为对应机制通过。新关联test采用 **expression-before / call-after**，register逐call保存source_span、actual call_offset、before_marker、after_marker及允许的line/opcode事件域。before取该Call表达式首指令，after取CALL下一非CACHE指令；静态核before<call<after。仍为同11个SPEC、11个OBJECT、1个append调用；两侧边界加append的两代，独立验证48场景，没有删除2018场景。

before位于参数求值前：mirror参数为local/constant或固定的type(boundary)；runtime_seal是固定纯读取/构tuple/hash；claim的inner FunctionType只构造函数，持久claim effect在outer CALL。测试按固定AST形状单列这些嵌套调用，不声称区间没有CALL。每场景记录并断言journal append、具体mirror身份、seal新tuple或claim计数的before/after状态。合成B_S claim新增独立claim_calls计数，证明after marker确实经过outer claim。目标Core CodeType不改，原v2定位失败仍冻结。

69方法保持Core32、role26、关联11，140 canonical frames。Core→role capsule、LIVE/RUNNING/OBJECT/IDLE readiness、entry-before-clock、失败后held packet收尾、全部异常分层与未知边界同v2。仅明确synthetic domains：kernel leaf、entry/bookend、namespace/B_S lifecycle与role效果为fixture；ordinary Capture1/DRAIN1真实sampler/HANDLE和validation child单列。项目Native/P1/Source49/solver/NFC12不执行，新增模拟0h。

实际entry/argv/channel、IMPORTING前role root/Guard2、launcher/两层quiet、完整F physical-read复用和资源准入继续OPEN；各run/science/resource/formal/actual_F gate为false。原F合同仍为19 metrics、17 targets、180秒、12500/6500读取帽、四件128KiB；12159/12053仍只是P1条件算式。
