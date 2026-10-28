# F：retained producer逻辑生命周期检查点

2026-10-29，DRAFT_NONAUTHORITATIVE。宽goal“持续推进”保持active，完整F未完成。承接[project graph检查点](continuation_handoff_20261028_saved_fresh_producer_project_graph_v1.md)。root唯一writer，retained_lifecycle_review独立只读PRE_SEAL；没有official verdict、receipt、production seal或新增真实运行权限。

## 本轮改动与证据范围

[生命周期实现](../../experiments/staged_rts24_saved_fresh_retained_producer_v1.py)连接原consumer plan/binding、prebound capture、context/check、外部expected image、完整HeldInput raw map及G0→G2→G3→close。排他复用原owner._consume_state与runtime_seal语义，拒绝第二claim；foreign thread不改状态或清理，同线程重入保留exact pending error，吞错也不能提交成功阶段。

可信入口为creating bootstrap预持的(CodeType, isolated globals, state)。source_dispatch按source编译核全部source-owned函数/类方法、常量、direct imports和builtin targets；helper/graph顶层函数提前复制至private globals，原始metadata漂移后仍以held code收尾。公开producer方法明确要求该入口。此机制有bootstrap私有state、已认证project依赖及解释器信任边界，不防御任意两个Python bytecode间对整个进程的敌对改写，不签发真正P1 token。

失败保留primary与各label secondary原对象，cleanup exactly once，原Core close(primary)+空secondary的carrier单独保留。terminal reset/seal/publish fault有不可重试registry，后续重抛同一sealed wrapper。cleanup前后比较完整retained数据与caller-image投影，close reset在释放live refs/CLOSED前完成；不确定时UNRESOLVED并保留原引用。成功报告返回独立数据副本，全部科研、资源、运行及F字段false。

[31项合成测试](../../tests/test_staged_rts24_saved_fresh_retained_producer_v1.py)已唯一执行并通过：31/31，64 canonical帧，0 failure/error/skip；runner1.612s，外层unit7.778219999978319/10s，child rc0，capture_error=null。HANDLE、pipes和reader threads终态，无kill/truncation/cleanup/reader错误。原Source49目标模块、真实P1、真实owner producer执行均0。

夹具以独立synthetic named函数及逻辑runtime执行实际生命周期程序；683项/2950863B为合成内容。原49 source只作读取/hash/compile-only核对，未执行其目标模块。public prepare拒绝synthetic原函数，测试的私有逻辑plan不是bootstrap issuer或许可。

305次healthy sampled观测，parent峰值48529408B、child91099136B，峰值字段和最大139628544B；未触发256MiB/process和512MiB/pair停止帽。它不证明连续/descendant/128MiB retention或真实37-module路径资源准入。

## 冻结输入、预算与保存

[合同](staged_deliverability_c_saved_fresh_retained_producer_lifecycle_scope_v1.md)与[controller](../../results/tables/staged_rts24_saved_fresh_retained_producer_v1_non_authoritative/driver.py)在首次register冻结；合同中的“未登记/自身0费用”为登记前快照。前驱graph账源SHA为7fd488b14a7c1e4a8171bebb37b81944a9c95f026116f16e2a79c5fee344a6b2，累计1144.4288945000255s、不接受41条。历史Source49、NFC12、bridge v1–v3及graph原字节保持，不重跑NFC12。

继承1214、自有8、重叠4，精确1218 inputs/58189448B；archive174文件/16327041B。独立重开逐文件核input/archive/own/known/charged pins，无mismatch；Source49 49/49与NFC12 16文件原字节不变。

Root为results/tables/staged_rts24_saved_fresh_retained_producer_v1_non_authoritative，6文件665020B；checkpoint9547B，SHA **61baf0d187724f066f9c9f629dc4f0c3ecf594b970de59e6e7d6c350885c806f**。accepted、diagnostic_accepted、accounting_complete均true，acceptance_scope为logical_retained_producer_lifecycle_only；accounting_errors=[]、pin_errors=[]、本包不接受记录[]。所有gate仍false。

|阶段|charge秒|cap秒|
|---|---:|---:|
|register|1.5199018999992404|5|
|唯一31-node unit|7.778219999978319|10|
|PRE_SEAL|3.3671868999954313|5|
|saved|2.9818978999974206|5|
|checkpoint|1.5264752999937627|5|

本包static9.395461999985855/25s、unit7.778219999978319/15s、总17.173681999964174/40s。累计static567.7200877000098s、pytest366.48897970000326s、unittest227.39350909997665s，总 **1161.6025764999897s**；不接受仍 **41条record**。不重置、退款或转用历史/本包余量，所有旧失败保留。费用只计受控capture阶段，不含编辑、只读审查、额外机械核对及Git全部wall；新增模拟跨度0h。

## 下一步与现场

本包PRE_SEAL/saved/checkpoint已保存。下一包必须继承本checkpoint SHA 61baf0d187724f066f9c9f629dc4f0c3ecf594b970de59e6e7d6c350885c806f及上述累计/41条，不能继续以graph旧账源记新费用。优先推进真实bootstrap issuer与Source49初始module/class/default/source闭包oracle，再固定37-module图调用量与旧40图帽的后继接线、父端quiet后reopen replay、全workflow wall/RAM/storage准入。该逻辑检查点不授予P1/actual role/native校准/模型/solver/长实验权限。

39项并行论文、插图和文献改动保持原字节；共享导航只用index发布本轮前置段加原HEAD正文，工作区仍保留并行内容。Git远端hash和最终worktree状态以发布后的实测读回为准；宽goal不因本组件完成而结束。
