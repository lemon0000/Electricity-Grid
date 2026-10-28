# F：执行来源、returned graph与lifecycle连接合同

2026-10-29，DRAFT_NONAUTHORITATIVE，未登记草稿。root唯一writer，retained_lifecycle_review只读PRE_SEAL。承接[逻辑生命周期检查点](continuation_handoff_20261029_saved_fresh_retained_producer_lifecycle_v1.md)，完整F保持未完成。本合同只固定普通合成验证，不启动真实bootstrap/Source49目标模块、P1、角色、native校准、模型、solver或长实验。

## 真实缺口与本包目标

现有Core39持有固定raw49并bookend；namespace consumer v2对ENTRY进行原raw的reference/actual两次初始化并比较。B_S post_return v2对adapter返回后核14个函数根，对其余模块只有registry retention及finder metadata，缺少逐模块实际exec来源。旧project graph v1只观察continuity，不能补造过去的construction事件。

compile-only census固定37模块、500顶层函数、146 class。源码确定包含Fraction ZERO、re.Pattern、typing.Literal、ProtocolMeta和ctypes.Structure；graph v1的有限类型域不能编码它们。新graph v2显式处理这些值及相关Enum、future feature、ABC缓存、类型alias和runtime结构值，保留未知值拒绝；不能据此推断实际37模块已经capture成功。支持规则是封闭编码与conditional stdlib/VM/native边界，不把repr、pickle、未知getter或任意外部class当作oracle。

本包实际代码路径为：标准SourceFileLoader exec → same-bootstrap construction FINAL → graph v2 capture/check → 同modules/raw/registry bundle → held lifecycle source_dispatch。

任一步不完整或未知节点均不能返回bundle、创建producer或占用owner._consume_state。构造证书是同一bootstrap中顶层import已returned、lifecycle尚未开始时的代码来源/metadata/identity证据，不宣称完整中间态、文件reader拿到同一个raw byte object或抗RAM ABA。SourceFileLoader执行CodeType须等于对held raw按原路径dont_inherit=True/optimize=0的编译结果；源码仍冻结Source49 epoch。

## 接线与信任边界

[bootstrap helper](../../experiments/staged_rts24_saved_fresh_producer_bootstrap_v1.py)从Core持有的raw49选定36个src模块加ENTRY。ENTRY吸收namespace已有_raw/_unit/2次exec/actual_initialized及same module证明；其余36项在import前cold absent，每项exec恰一次。审计事件只有code，故另核原CPython _call_with_frames_removed及SourceFileLoader.exec_module实际frame/code/globals，要求其真实exec参数为该code和登记module.__dict__，拒绝仅sys.audit伪造事件或错globals。

collector只在选定exec时做有界身份核对，不逐事件调用昂贵的owner.entry/namespace graph。begin、finalize和bundle边界仍做owner bookend。这里的CPython、stdlib loader初始来源属于creating-bootstrap现有conditional TCB假设；本包不能把捕获函数identity升级为独立源码/平台认证。

[B_S successor v3](../../experiments/staged_rts24_saved_fresh_bootstrap_post_return_v3.py)是独立未执行字节，仅在begin_import后调用固定before_import桥，import返回下一行调用after_import桥，在原audit busy事务前转发exec。桥为原CodeType/isolated globals/state，source_program先以冻结lifecycle的source verifier核自身定义，私有globals执行。它不使用sys.setprofile/settrace、不更换loader，不改NFC12/Source49/旧scope/results。真实Core/parent/probe manifest、独立profile、旧40图帽后继及实际调用量仍须后续接线与准入；不得把此B_S草稿直接用于旧包。

bundle在construction FINAL且graph成功后才向lifecycle独立successor v2提供同owner、同snapshot及原capture CodeType；外层held dispatcher逐操作先验证construction和graph/lifecycle的source manifest，再调用held lifecycle dispatcher。v2仅新增bootstrap_abort入口：producer已持有时若外层certificate/graph验证失败，仍在原operation lock内保留exact primary、final checks与exactly-once cleanup，形成sticky UNRESOLVED；foreign thread仅拒绝，成功CLOSED后重复close只读取数据报告。v1原字节不改。admission来自creating bootstrap外部明确授权的scope，helper不发行真实P1 token。当前普通夹具的object token和fake owner没有实际权限，lifecycle public prepare必须拒绝其synthetic source。

所有导入/构造异常保留原primary并sticky失败，交由原probe/boundary/runtime的finally执行唯一清理；collector不在audit回调中另行close或重试。unknown graph、缺项、重放、额外alias、wrong frame、registry漂移及helper metadata漂移必须阻断bundle。所有科研/资源/角色/正式/run/F gate false。

## 验证与资源预算

普通unit仅使用system tmp、独立synthetic源码及真实标准SourceFileLoader；不执行Source49目标模块、不读真实P1。unit child用-B/-s/-S维持无site的标准builtin域；样本与真实-C cold bootstrap的覆盖范围分开。源码census和原B_S AST差异为compile-only，不能称actual construction。

唯一36-node suite包含冻结graph原12项行为回归（在新graph上执行），6项typed graph反例、2项外层abort/清理与16项constructor/bundle测试。覆盖标准loader的真实call-frame参数连接、执行代码漂移、伪造exec、缺项、额外alias/reload、ENTRY raw/registry漂移、同raw snapshot绑定、unknown graph不进入lifecycle、synthetic owner拒绝、graph函数metadata篡改、foreign thread poison和B_S三个固定接点。已执行旧测试证据仍保留；本包会如实记录实际新执行的36项。

完整受控DAG：register → 唯一unit → 独立PRE_SEAL保存 → saved canonical replay → checkpoint → Git。每阶段一次；失败终止正常后续并保存checkpoint，原字节及失败费用保留，后继不得退款或转用本包余量。

预算static25/unit15/总40s；register5、unit10、PRE_SEAL5、saved5、checkpoint5，其余static5/unit5仅同包失败保全。参考前包register1.5199、unit7.7782（runner1.612）、PRE_SEAL3.3672、saved2.9819、checkpoint1.5265，另含本包source compile/census、标准loader/frame与typed graph开销，不用runner替代controller wall。child≤8s、stdout128KiB/stderr32KiB，256MiB/process、512MiB/pair sampled停止帽；不证明continuous/descendants/128MiB retention。root≤10文件/4MiB，record≤1MiB且预留checkpoint1MiB。

前驱账源checkpoint SHA **61baf0d187724f066f9c9f629dc4f0c3ecf594b970de59e6e7d6c350885c806f**：累计static567.7200877000098、pytest366.48897970000326、unittest227.39350909997665，总1161.6025764999897s，不接受41条。本包自身0，未登记。前驱expanded inputs1218与自身root6合并为继承1223项；archive174+6=180文件/16992061B。自有12项与继承重叠5项，精确union1230 inputs；每次register/check重建完整关系，不以直接map替代完整继承。

本轮结束后仍须真正37-module兼容性/初始化观测、新bootstrap issuer与manifest/profile/图调用量预算、父端quiet后reopen replay、实际P1许可及whole workflow wall/RAM/storage准入。完整目标不因合成bundle通过而完成。
