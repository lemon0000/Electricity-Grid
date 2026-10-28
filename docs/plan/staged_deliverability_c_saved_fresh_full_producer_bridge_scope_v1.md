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

## 控制器修复与验证矩阵

本scope仍未登记时补齐第5组控制器修复。唯一unit包含原4项构造器测试与12项控制器测试，共16项、34帧；控制器故障注入仅使用system tmp内synthetic roots和mock，不调用P1、Source49目标模块或真实capture child。helper/tests自身正常执行。原第1—4组现有修补与本组需一起接受独立只读PRE_SEAL，测试终态仍以本root原流为准。

精确关系为：NFC12继承1157项的canonical map pin必须等于其登记的inherited_effective_pins_pin，直接input_pins必须360项、登记字段effective_input_count必须1167、重建并集也必须1167项；加入其16个root文件（其中3项已在继承集合）为1180项；再合并7项own inputs，其中sampled capture和memory drain两项重叠，最终1185项。登记与check均重建此集合及完整archive，拒绝动态删减；archive要求路径/解析后路径唯一，转dict后仍为155项14350165B，与冻结map精确相等。测试覆盖重复/别名、同尺寸换项、内容漂移、输入/own/archive删项、计数伪装、前驱pin/计数字段漂移，以及删掉已继承的直接pin后并集仍1167的反例。

正常阶段严格为register → unittest → pre_seal → saved → checkpoint；每阶段先核完整accepted前缀，任何拒绝停止后续payload。checkpoint可关闭以失败record终止的连续前缀，按record数续计历史39，不解释为package数。终态create-only，重复/终态后调用不执行payload。每次保存预留1MiB checkpoint空间；失败封存仍受原10文件/4MiB及每record1MiB限制。

checkpoint的previous、replay或canonical校验异常不得跳过保存；独立fallback重读可验证record的真实charge、原流/已知pins与错误，并只用固定NFC12 checkpoint验证历史累计。可解析且字段有效的非canonical record保留已知charge及已知不接受record名；仍明确accounting incomplete，不宣称完整累计。不可解析、duplicate key或字段无法安全验证时费用未知，仅保留raw pin；记录或历史账无法认证时累计总数/总秒数为null。测试覆盖三类主异常、缺失前驱、非canonical成功/失败、不可解析/重复键record、不完整成功前缀、失败元数据关闭及checkpoint自身超帽。

完整有界正常DAG为：register（previous 1次、own syntax、builder.current 1次、16-node清单）→唯一unit（parent capture前/后各check 1次，child前/后各check 1次；原4项测试共current/derive 4次，另12项tmp故障测试；合计previous 4次、builder 8次）→PRE_SEAL（前/后各check 1次，共previous 2次、builder 2次及固定finding数据）→saved（前/后各check 1次，共previous 2次、builder 2次，原流34帧/exit/memory guard重开）→checkpoint（check 1次，内含previous 1次、builder 1次，另saved canonical比较、独立费用fallback及pins）。全包正常共previous 10次、builder.current/derive 14次；后者各读49-source共686次，ENTRY函数源码和AST测试直接读另计。checkpoint正常复用check内的同次previous，删除原先紧邻的多余遍历；失败分支仍独立previous后保存费用与pins。

各previous完整遍历冻结driver链并验证约56MB的1180项前驱/root集合及155项archive；各check另读49-source contract。阶段间与parent/child前后freshness读覆盖不同漂移窗口，保留而不缓存跳过。686次为builder显式source读，不包含previous旧链中的重读；旧链仅有限元数据验证，不执行旧NFC12或48项unit。固定阶段cap仍register5/unit10/PRE_SEAL5/saved5/checkpoint5，正常规划上限static20+unit10=30s，余static5/unit5仅失败保存。普通unit由8s child sampled capture约束；parent两次完整check计入同一unit10s charge，实际能否在帽内通过须由唯一unit终态测量，不承诺未测wall/RAM。受控预算仍static25/unit15/总40s，未扩大或挪用旧余量；后续producer的736/1419/2102次P1内容读不属于本DAG。
