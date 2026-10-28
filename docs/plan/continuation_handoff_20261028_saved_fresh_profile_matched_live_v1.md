# F：冻结profile精确匹配，本地LIVE完整关闭

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[NFC9 OBSERVED](continuation_handoff_20261028_saved_fresh_post_return_observed_v1.md)，合同为[NFC10 profile配对scope](staged_deliverability_c_saved_fresh_post_return_admission_scope_v3.md)。本轮为progress，宽goal仍active，完整F未完成。Root唯一writer，wire_root_review只读PRE_SEAL及终态取证；没有official verdict/receipt/production seal。

## 实际端点与不可变记录

Root `results/tables/staged_rts24_saved_fresh_nfc_v10_non_authoritative`，精确 **16文件1824018B**。checkpoint SHA **8abd5d04628ee39cb93dc31f4e4eb307ecf9f49f99b80063d77d903e0a24bd65**；accepted=true、diagnostic_accepted=true，范围仅packed metadata及conditional local profile-matched LIVE诊断。size/register、唯一25-node unit、独立PRE_SEAL、startup/reference admission、唯一normal、saved全量重放及checkpoint均终态通过。所有执行source/scope/input/results bytes冻结。

Normal child的实际observed profile与原NFC9 **501203B/SHA a61fb973180f4031ebc024bb69ab162460955594c4bb53cc182d3da70559d3b6**逐字节相等。参考路径及NFC9 checkpoint pin由reference函数body-local literals固定；原profile没有复制、裁剪、清空或当前重算。profile_admission绑定当前startup/transport/registration/helpers和原NF9 descriptor，manifest raw经argv SHA连接。parent启动前后fresh context相同，且等于POST从原manifest独立派生的context；parent解码raw后再次比较原参考。字段级diff为空，未参与接受。

关闭前runtime为 **LIVE**、runtime_was_live=true；最终runtime/resource/boundary全部 **CLOSED**，live_at_report=false。Child exit0、primary=null、secondary=[]、self close_calls=[1,1]、DLL directory关闭。父端HANDLE/stdin/writer/pipes/readers全终态，无kill/timeout/truncation/reader或cleanup error。这是同一受控normal进程的conditional local LIVE，不是role、permit、producer、独立TCB或F权限。

## 原始取证、调用量与实现

Raw stdout **42365B**、stderr **16332B**，22 stages、30图对=21 namespace+9 adapter，13 census帧，parser complete、0 unclassified/stack。真实import仍在1344个guard-passed selected opens自然返回，census rejected/diagnostic_error=0；该计数不补入停止census后的source读取。

实测auth1、finder_check10、adapter_check8、profile2、Source49 bookends5，返回后active-hook idle getter3968、busy getter0。auth0.0023434000031556934s、finder_check合计0.0011349999986123294s、adapter_check合计0.021016899976530112s、profile合计0.017398500014678575s；这些bucket有嵌套，不能求和为整链分解或跨包速度结论。Namespace仍2940 nodes/376728B，adapter137 nodes/28501B；strong objects/image bytes不等于heap/retention。

Profile仍1918个sys.modules条目、cache165、paths6、finder types5；两次child profile（含finish内部返回raw）一致，且与原参考一致。loaded_python_graph_attested/registry_contents_verified/native_behavior_verified均false。原bootstrap helper完整14-name literal、两类shape、graph/freshness检查、namespace reader和memory_drain均复用已冻结bytes。core37/probe35只迁移独立manifest root，没有新增child imports或helper注册。

parent34改为受控normal单独create-only receipt，不写旧七case序列journal；其他旧parent及记录冻结。Host reference/validation/constructor/checkpoint为新版本，reference before/after/context与raw/derived/profile全部连接。Checkpoint fresh重算完整saved report，并以canonical bytes exact equality验证所有字段，包括false布尔类型，不能只核audit_validation子树。

## 费用、采样与保全

|阶段|charge秒|cap秒|
|---|---:|---:|
|size|1.7906207000050927|6|
|register|1.5098316999938106|4|
|唯一25-node unit|10.23548230000597|20|
|PRE_SEAL|3.2071010999934515|5|
|startup|3.804732699994929|6|
|startup/reference admission|3.0756584999908227|5|
|唯一normal/LIVE|10.197465300007025|30|
|saved replay|3.3539155000034953|5|
|checkpoint|2.4893746999878203|4|

本包static **29.428700199976447/65s**、unit **10.23548230000597/20s**，总 **39.66418249998242/85s**，余 **45.33581750001758s**留原包。Normal parent receipt **6.369980700008455/28.193498499997077s**，census窗口约3.4578s；与外层normal phase分开。累计static467.5215473999808、pytest366.48897970000326、unittest143.1424420000003，总 **977.1529690999844s**，不接受仍 **38条**。旧105文件8636628B加本包为 **121文件10460646B**，无退款/重置/跨包转用。Capture不含全部工程编辑、人工审查、Git及Python启动wall；模拟小时新增0，不是科学运行。

Parent-controller PID39588、child12980、原HANDLE624、80B结构，357 attempts/samples，kernel/direct-child/guard/drained PID及parent PID逐项一致。sampled peak WS parent55664640B、child153309184B；同次两个peak字段之和最大208973824B，private pair最大162234368B。Receipt投影精确等于last-live guard child peak，无query/handle/PID错误、over-limit、sample-limit或exit后补采。原256MiB/process、512MiB/pair只是诊断停止帽；continuous_bound_verified/combined_retention_verified/resource_admission=false，不能证明128MiB retention、连续或descendants覆盖。

Registration：352 direct inputs、17 helpers、1124 effective；SHA **da096da462e27374f28213b056da0b2f3aae548f504ef4db975f76976c5f1bac**，NF9 profile与CP为直接输入，旧constructor闭包继续fresh核验。实际registration小于758585B上界/1MiB帽；两命令独立重算：discovery29996、normal29993，最大29996/30000 UTF16。stderr上界28372/32768、saved固定body最坏4438/6144，成功root16/17文件且小于4MiB。

Unit完整52帧、25/0/0/0、runner4.094s、PID35984/exit0，原streams/pins与捕获资源全终态；SHA **f478cdfe8c0cbc29a2af996e4f1123dffe489935c1502ebaba9b0551e5b2bbfa**。新增四组核reference/admission/manifest漂移、profile四域mismatch、两次profile不同、LIVE后entry/close失败、伪LIVE、saved全字段改写及False→0类型混淆拒绝；均为logical/unit证据。真实normal匹配由本次actual另外证明。

独立只读终态复核重建1124有效闭包、零冲突/缺失/漂移，重开16 root、raw/parser、参考/manifest/context、profile、saved canonical replay与CP派生、memory/PID/费用；must_fix_open=[]。Source49 epoch仍 **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**。没有新增P1读取、实际role/OwnedChild/Job/F、模型或solver调用；全部authority/science/native/resource/formal/run/F gates仍false。

## 下一步

从[producer binding准备草稿](staged_deliverability_c_saved_fresh_producer_binding_admission_scope_v1.md)继续。当前LIVE对象仅在child中存在并已关闭；必须先定义新同进程producer/consumer桥与生命周期、完整依赖/调用量/预算及失败窗口，再接入真实消费方。不能把跨进程摘要、1918条retention观察、adapter直接14根或local LIVE当作完整生产闭包。

旧ENTRY `_expectation_adapter`仍自行import并建立10个preparation callable绑定；`capture_saved_expectation`会读P1/anchor及53个条目，不属于本轮已执行路径。下一轮先审这些实际消费者与原33根/能力DAG，不能直接调用或以现有bind tuple代替完整机制。父端采用、producer capability、角色/permit、资源和当前F完整闭包仍OPEN。

当前无活动实验进程。39项并行文稿/插图/文献改动保持；四导航仅发布新前置段+原HEAD正文。最终Git hash/remote回读见实际同步报告，不能称全局worktree clean。Scope_v3保持启动前合同字节，终态以本交接及不可变records为准。
