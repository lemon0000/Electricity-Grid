# F：构造终态、失败保全与静态重开检查点

2026-10-29，DRAFT_NONAUTHORITATIVE。宽goal“持续推进”保持active，完整F未完成。本轮沿[bootstrap wiring交接](continuation_handoff_20261029_saved_fresh_bootstrap_wiring_v1.md)推进；root唯一writer，retained_lifecycle_review独立只读PRE_SEAL，未签发official verdict、receipt或seal。

## 当前实际完成

[精确变换](../../experiments/staged_rts24_saved_fresh_construction_terminal_transform_v1.py)生成Core41、Probe39、Parent38、Namespace3、LC3、Helper4和Loader2独立后继，冻结旧source和结果不变。Core40的LocalRuntimeInputs所有方法在同一虚拟filename下逐个CodeType相等。Helper4只改LC3 pin，仍只接受None admission；本地token不能成为真实issuer。

LC3修正真实清理协议中的确定性错误：namespace完成移交后保持CONSUMED，runtime/resource成功关闭应CLOSED。新只读终态采样核对原namespace、inputs、successor、resource、owner、原sys.modules容器、actual/reference两种别名全部清空与pending handles为空。primary失败保留时，允许runtime UNRESOLVED并持有原failure，不再制造“namespace不是CLOSED”的伪secondary。Probe39同时携带该终态数据。

[Parent终态oracle](../../experiments/staged_rts24_saved_fresh_construction_validation_v1.py)对独立discovery/import_discovery case核对closed schema、canonical JSON/duplicate keys/NaN、原compressed profile完整性、同kernel pid/time/image/command、manifest/helper context前后、22阶段与43图、census、POST计数、guard顺序、原句柄和parent quiet/memory。transport/manifest准备失败也进入统一receipt和费用记录。只有完整父端重开通过才create-only写profile；最终超帽或发布失败时，核验本次新建文件dev/ino后移存为.rejected.json，保留字节、primary与cleanup账，不占用正式profile路径或覆盖foreign文件。

[静态图账](../../experiments/staged_rts24_saved_fresh_construction_graph_budget_v1.py)将构造路线紧定为43次：33 namespace、10 adapter。旧40次在report后尚缺最终关闭3次，不能完成该路线。INTERVALS进入manifest v2并由Core41/Parent38绑定；实际完整producer代码静态下界107，若保留等价report则109，尚缺issuer、P1 guard及fault预算。成功POST计数为authenticate1/finder16/adapter9/profile2，source bookend7；getter次数和耗时仍只能有界观察。这些是代码账，不是实际37模块成功或whole-workflow资源证据。

## 唯一普通测试与失败记录

[29项测试](../../tests/test_staged_rts24_saved_fresh_construction_terminal_v1.py)唯一执行，29/29，0failure/error/skip，60个canonical帧。覆盖完整合成terminal/raw replay、图/阶段/JSON异常、profile展开/流尾/hash、namespace别名/对象链、primary保留、preflight失败记账、发布后超帽与读回失败、foreign/archive保留、kernel/memory/context篡改。

Runner1.670s，外层unit4.271836800005985/10s，rc0/capture_error=null。handle、pipes、reader threads均终态，无kill/截断/reader/cleanup error。原采样195次，parent peak36380672B、child peak53374976B，sampled峰值字段和89755648B；未超过原256MiB/process、512MiB/pair停止帽，不证明连续/后代/128MiB retention或资源准入。普通fixture只执行helper、独立合成函数和metadata；新增Source49 target/P1/native owner/角色/模型/solver执行0，新增模拟跨度0h。NFC12未重跑。

v1在保存独立PRE_SEAL结论时，外部PowerShell文本管道给canonical JSON追加CRLF，被严格原流校验拒绝。机械复现确认追加的字节为CRLF；该阶段费用0.6252245000214316s与拒绝记录永久保留，未在v1重试或改写源。v1 checkpoint accepted=true、accounting_complete=true仅表示账务保全，diagnostic_accepted=false，不能称原包验收通过。

v1 root为results/tables/staged_rts24_saved_fresh_construction_terminal_v1_non_authoritative，5文件732049B；CP11594B，SHA33714000c4827e628cf6b8129131da247a3835250207fc2bd23330a62a2dac7c。register1.8312494999845512s、unit4.271836800005985s、PRE_SEAL拒绝0.6252245000214316s、checkpoint0.5432065999775659s，总7.271517399989534/40s。该失败后完整账1239.7939447000201s、不接受47条。

## 唯一静态收尾后继与账源

[v2合同](staged_deliverability_c_saved_fresh_construction_terminal_scope_v2.md)及[controller](../../results/tables/staged_rts24_saved_fresh_construction_terminal_v2_non_authoritative/driver.py)只重开原29项原始流和已冻结15项source/test/合同输入。没有unit阶段，unit_reexecuted=false；保存PRE_SEAL通过Python subprocess.run(input=canonical bytes)直接传递。

v2 root为results/tables/staged_rts24_saved_fresh_construction_terminal_v2_non_authoritative，5文件696058B；CP6150B，SHA **0bc1887e3de8a9dbb49c180a97bd5ff7077fee01149f49789f92a68f7caa3240**。accepted、diagnostic_accepted、accounting_complete均true；acceptance_scope=reused_construction_terminal_units_and_static_reopen_only，accounting_errors=[]、pin_errors=[]、本包拒绝[]。原v1拒绝状态与记录继续保留。

|阶段|charge秒|cap秒|
|---|---:|---:|
|register|1.5260945000045467|5|
|PRE_SEAL保存|2.2206471000099555|5|
|saved原流重开|2.80289520000224|5|
|checkpoint|1.9469290999986697|5|

v2 static **8.496565900015412/20s**、unit0；旧40秒包剩余不转用，旧费用和失败不退款或重置。本轮两包累计新增15.768083300004946s；当前累计static **611.9632506000155**、pytest **366.48897970000326**、unittest **269.8382803000168**，总 **1248.2905106000355s**，不接受 **47条**。下一受控包必须继承本CP与完整账，不从旧1088/1232费用或39/46拒绝数重新开始。编辑、只读审查、机械准备和Git墙钟不冒充受控阶段费。

v1完整1301加root5、扣driver重叠1后继承1305；v2自身2、overlap0，精确union **1307 inputs/65964377B**。archive **216文件22428588B**。原unit exit23522B，SHAba989d71ed26219ffa10b34ce3e3da0983d7cec1e5ba4a69e3eb0000e4a88a9c。原v1 source scope与15项own bytes冻结，v2 own2同样已登记冻结。

最终机械重开inputs/archive/own/known/charged/Source49/NFC12共 **1599次pin比较**、1398个独立文件，mismatch=[]。Source49全部49文件及epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875保持；NFC12全部16文件和CP bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de保持；原39项并行论文/图/文献dirty逐SHA相同。

## 完整F的下一步

完整目标保持真实、外部授权、creating-thread-held issuer → 同LIVE owner完整producer prepare/run/G2/G3/close → parent quiet后的独立重开采用 → whole-workflow wall/RAM/storage准入。当前None-admission construction不能替代这个目标；真实issuer、只读P1 guard和实际37-module兼容性仍OPEN，Source49原关闭的issuer/capability cut未开放，所有role/permit/science/resource/formal/run/F门false。

下一步先形成实际startup/import discovery与后续完整producer的独立范围、DAG、完整调用量/故障路径和预算合同，给出真实held issuer/P1 guard的来源与绑定，再按agent.md第9节准备具体真实校准包及专项授权。43次构造图账不能代替107+未知部分的完整路线预算；旧NF9 profile只作metadata参考。当前没有新真实启动、producer、Native/P1或长实验授权。已登记v1/v2及原source输入保持冻结，后续修补另建独立successor。

共享四导航只在index发布新前置段加上一版HEAD正文，worktree原并行字节不改；最终Git remote hash和index/39项保留状态以发布后现场读回为准。宽goal保持active。
