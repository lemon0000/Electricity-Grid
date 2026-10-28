# F：expectation与full hold的同owner producer桥

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[真实binding消费交接](continuation_handoff_20261028_saved_fresh_live_consumer_connected_v1.md)。root唯一writer，wire_root_review只读PRE_SEAL。NFC12及全部旧source/scope/results冻结，Source49不原位改变，39条受控不接受与全部预算保留。

## 完整目标与本轮可验证边

完整producer必须是同一真实LIVE owner内的 expectation53 → context/bookend → adapter.hold(source,expectation.image) → 精确HeldInput/caller-image join，并强持到controller G2/G3；parent/fresh各自重新full hold，跨进程只传有界数据。`adapter.capture`自己生成image，不能代替外部expected truth；本轮也不能将53-read expectation独立称为完整producer。

当前ENTRY.capture_saved_expectation在首段调用_expectation_adapter，重新import/构造preparation binding；直接从NFC12调用会绕开已经强持的同对象binding。此轮先实现并验证一个source-derived prebound capture code：只在函数签名加入binding参数、移除唯一 `_expectation_adapter(source)` 赋值并使用显式derived函数名；其余原AST、53-read/metadata/anchor/caller-image/失败bookend和结果类型完全保留。运行时未来由受控namespace以原ENTRY globals实例化，传入同一LIVE owner预先强持的binding，不能临时修改ENTRY globals或提供任意callback。被移除preparation中的Source49 freshness、EXE/P1/SCOPE及原函数/default/module检查须由完整runtime plan和bookend替代，当前构造器不证明这些替代已完成。代码生成不exec/import Source49目标模块、不读P1、不创建runtime/capability；开发helper和tests自身按合同正常执行。

验收必须证明：原Source49及NFC12 checkpoint绑定；唯一原函数/唯一定义、无decorator/default/closure；删除节点精确匹配，新增参数不会遮蔽原自由变量，转换可逆且其余AST位置保留；compiled code不再引用_expectation_adapter；原函数字节与其他Source49不变；签名/源码/pin/目标名称或额外语句漂移均拒绝。此构造器只解决producer的一个必需连接边，完整runtime closure和retained producer owner仍OPEN，不能因AST转换成功授予P1或能力权限。

## 后续实际producer必须闭合

1. closure必须覆盖ENTRY capture/context/metadata/read及expectation类、adapter HeldInput类与dataclass方法、stamp，以及codec parse/canonical/directory_identity/ordinary、core.digest/load_fixture、mechanical.inventory/pin/checked_pin、固定constants和实际global/module/class边。旧catalog仅候选，不把1092/980个静态节点或当前10-binding当完整runtime图。NFC12中adapter自身图已覆盖的部分可复用；跨模块内容和defaults/classes必须另核。
2. 原生命周期要强持真实runtime、expectation、context、adapter、完整HeldInput至G2/G3；不能用已关闭的consume_once结果或JSON重建capability。任何partial stage/consumer/context/full-hold/bookend/close失败均sticky reject，原primary和各secondary保存，不重试、不降级使用53-read结果。
3. expectation53内容读53次、metadata两遍、anchor两次；一次full hold读683内容、anchor两次；每次默认full bookend再读683和anchor一次。因此expectation+G0为736次P1内容读取，+一次full bookend为1419，原controller G0/G2/G3为2102；source/fixture/外部case和runtime bookend读取另计。后续replay自带额外bookend，须按真实DAG再计，不能隐入本预算。
4. parent只采用canonical evidence并独立核Source49、anchor、完整683map、expectation raw/image/pin、producer PID/creator/runtime-owner关系和quiet后重开；科学adoption、角色issuer/permit/OwnedChild/Job、完整资源和F权限依然独立。形成具体可审实现及完整预算后再处理实际P1读取许可，不从本轮代码生成推导运行授权。

## 当前开发预算与保全

本轮仅标准库源读取/AST compile及独立synthetic构造器测试；无P1/actual owner/native校准/模型/solver/child诊断。开发root `results/tables/staged_rts24_saved_fresh_full_producer_bridge_v1_non_authoritative`，static25s、unit15s、总40s；register5、唯一unit10、PRE_SEAL5、saved5、checkpoint5，static余5/unit余5仅同包失败保存。unit subprocess复用原sampled capture，256MiB/process、512MiB/pair、stdout128KiB/stderr32KiB、10ms/4096 sampled停止帽；测试不执行科学payload。最多10文件/4MiB，每record≤1MiB，所有原流/exit/input pins及失败create-only保留。旧155文件14350165B、累计1088.9926936999939s和受控不接受39条不重置、不退款或转用。仅本轮新增受控费用累加；模拟跨度新增0h，所有producer/role/科学/资源/正式/run/F flags false。
