# F：construction、typed graph 与 lifecycle 联合检查点

2026-10-29，DRAFT_NONAUTHORITATIVE。宽 goal“持续推进”保持 active，完整 F 未完成。承接[逻辑生命周期检查点](continuation_handoff_20261029_saved_fresh_retained_producer_lifecycle_v1.md)。root 唯一 writer，retained_lifecycle_review 只读 PRE_SEAL；没有 official verdict、receipt、production seal 或新增真实运行权限。

## 当前实现和已验证内容

[bootstrap helper v2](../../experiments/staged_rts24_saved_fresh_producer_bootstrap_v2.py)把标准 SourceFileLoader 的实际 exec CodeType、原始 loader/call frame 的 globals 参数、每模块恰一次执行及返回身份连接至 construction certificate。ENTRY 继续使用 namespace 的原 raw/unit、reference/actual 两次 exec 与 same module 证明。Source49 epoch 保持 acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875；compile-only census 为37模块、500顶层函数、146类。

certificate FINAL → [typed graph v3](../../experiments/staged_rts24_saved_fresh_producer_project_graph_v3.py) capture/check → 同 raw/modules/registry 的 bundle → held lifecycle source_dispatch 已完成普通合成验证。图新增显式 Fraction、Pattern、typing/Protocol、ctypes、Enum、future feature 等编码；未知类型仍拒绝。source manifest 核 helper/graph/lifecycle 的 source-owned 定义，held CodeType/private globals 保留原执行路径。这里的 VM、stdlib loader 与 creating bootstrap 仍有 conditional TCB 边界，不是独立平台认证或抗任意 RAM ABA 证明。

[B_S v4](../../experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py)三个接点以 definition-time CodeType/defaults/spec 调用 before_import、exec、after_import。桥接函数全部运行时名字为局部参数；tuple 也由 defaults 捕获。B_S 本体仅编译和抽取三个 call 表达式验证，没有执行真实 Source49 目标模块。[lifecycle v2](../../experiments/staged_rts24_saved_fresh_retained_producer_v2.py)仅增加 bootstrap_abort，使外层证书/图失败在 producer 已开始时仍保留 exact primary、sticky UNRESOLVED 与唯一 cleanup。

[36项测试 v4](../../tests/test_staged_rts24_saved_fresh_producer_bootstrap_v4.py)唯一执行通过：18 graph、2 outer abort、16 construction/bundle；0 failure/error/skip，74 canonical 帧。runner 2.205s，外层 unit 6.269145300000673/10s；child rc0，无 capture error。HANDLE、pipes、reader threads 均终态，无 kill、截断或 reader/cleanup 错误。270次 healthy sampled 观测，parent peak 88231936B、child peak109973504B，最大峰值字段和198205440B；它不证明 continuous、descendants 或128MiB combined retention。

夹具使用 system tmp 的独立三模块源码和真实标准 loader。public lifecycle prepare 拒绝其 synthetic source；同 certificate/raw/snapshot 的 outer dispatch 连通由独立 downstream spy 证明。没有真实37-module capture、真实 P1、真实 owner producer 或模型/solver 执行。所有科学、resource、role、permit、run、formal、initial authentication 和 actual_F 字段仍 false。

## 失败与费用必须完整继承

所有已登记 source/scope/input/result 原字节冻结，修补只进入独立 successor。下列失败均保留，不重跑或覆盖：

|包|拒绝原因|包费用s|累计s|不接受条数|checkpoint SHA|
|---|---|---:|---:|---:|---|
|bootstrap v1|嵌套 TestSuite 在 admission 前调用 id，0项测试开始|8.26701830001548|1169.8695948000052|42|187f56ae2328c2508c25355bdd2c5bcda6928f959ec04499f1a3b04ff5c4fcce|
|bootstrap v2|ctypes 内部 CData 未编码，audit 夹具对非exec递归；stderr 截断，无最终 report|9.955459400021937|1179.8250542000271|43|78695a0173a0b55853647bbbf76bb6b1221f7a354e7532d8eacfe70db6fb99f1|
|bootstrap v3|36项最终 report：8 errors；builtin 私有复制字典与原字典身份不同，stderr 截断|12.167247300007148|1191.9923015000343|44|4ba6db1ee16e1e4ee068e60f258454440f74063dce46fae029b95ea4a14ac485|
|bootstrap v4|register 5.557246700016549s 超原5s帽，unit未启动|7.366585600015242|1199.3588871000495|45|1f4b84d2ace32a072b9407c021aae7503f3f211ec90b59ef55eec28b13236325|
|bootstrap v5|36项中35项通过；空builtins桥接缺 tuple，1 error|6.657212100020843|1206.0160992000704|46|27b800b508deefe082702d2791dd603c0ad03fc8852880cb5e0c042eb51bcd64|

v5/v6 控制器避免递归执行历史 controller 的重复 hash，以固定 checkpoint 绑定的完整 expanded registration 显式重建直接前驱关系，再对每个唯一 live 文件 hash。独立旧递归 oracle 对 inputs/archive 逐项相等；没有使用 NFC12 直接360 map替代完整继承，没有减少输入集合或提高帽。

## 接受根、资源和账源

[scope v6](staged_deliverability_c_saved_fresh_producer_bootstrap_scope_v6.md)及[controller v6](../../results/tables/staged_rts24_saved_fresh_producer_bootstrap_v6_non_authoritative/driver.py)在 register 冻结；其中“未登记/自身0”是登记前快照。实际1260 inputs =1256 inherited+12 own−8 overlap；archive199文件20212912B。额外机械重开核 input/archive/own/known/charged 与 Source49 共1541次 pin 比较，mismatch=[]。NFC12仍16文件、checkpoint bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de，未重跑。

Root 为 results/tables/staged_rts24_saved_fresh_producer_bootstrap_v6_non_authoritative，6文件724075B。checkpoint 11201B，SHA **bad043eeae43dcfba7c7dd0c65d33e81271a29f6099e79e23f7a2700879891c8**。accepted、diagnostic_accepted、accounting_complete 均 true；acceptance_scope=synthetic_construction_graph_lifecycle_bundle_only，accounting_errors=[]、pin_errors=[]、本包不接受记录[]。

|阶段|charge秒|cap秒|
|---|---:|---:|
|register|0.9753505999979097|5|
|唯一36-node unit|6.269145300000673|10|
|PRE_SEAL|1.8054500999860466|5|
|saved|1.8172594999778084|5|
|checkpoint|1.1410405000206083|5|

本包 static5.739100699982373/25、unit6.269145300000673/15、总12.008245999983046/40s。累计 static594.0510823000325、pytest366.48897970000326、unittest257.48428320001767，总 **1218.0243452000534s**；不接受仍 **46条 record**。下一包必须继承本 checkpoint SHA 和该累计账，所有旧预算/失败保留，不退款、重置或转用余量。费用只计受控阶段；编辑、只读审查、额外机械核对和 Git 的 wall 不冒充受控费用。新增模拟跨度0h。

## 下一步与现场

优先补 creating bootstrap 对本桥的真实加载和 issuer：从[Core39](../../experiments/staged_rts24_saved_fresh_pre_entry_lease_v39.py)、[Probe37](../../tests/staged_rts24_saved_fresh_runtime_handoff_probe_v37.py)、[Parent36](../../experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v36.py)的真实顺序出发，在 ADOPTED 后、B_S definition-time capture 前创建 held import bridge；validator 必须核新增 defaults/spec/命名空间，不能直接把 B_S4 塞进 NFC12。Core/probe/parent/manifest/profile 和旧40图帽都需要独立后继及调用量/成本合同。

其后才是实际37模块兼容性与初始构造取证、同LIVE owner producer、父端 quiet 后 reopen replay，以及 whole workflow wall/RAM/storage 准入。真实 Source49目标模块/P1/角色/native校准/模型/solver/长实验仍没有本包新权限；所有实际执行要先核适用合同与授权。完整 F 和128MiB retention 保持 OPEN，不能以合成通过代替。

39项并行论文、插图与文献改动保持原字节。共享四导航仅用 index 发布新前置段加原 HEAD 正文；worktree 保留并行内容。Git hash 与终态以发布后远端实测读回为准。宽 goal 不因本组件完成而结束。
