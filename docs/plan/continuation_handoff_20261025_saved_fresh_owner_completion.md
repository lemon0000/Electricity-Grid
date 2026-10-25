# C：saved owner 相关绑定补验交接

2026-10-25，DRAFT_NONAUTHORITATIVE，起始HEAD `8528cbe1c7982c83fc7403c54c5990a148c73822`；最终发布hash以远端读回为准。接续[owner开发交接](continuation_handoff_20261025_saved_fresh_owner.md)，按[源码不变补验合同](staged_deliverability_c_saved_fresh_owner_binding_completion_contract_v1.md)完成18相关binding。

本补验18节点终态exit0，30.625s/45s；静态帽15s，整包帽60s。原owner开发包225.639s/240s、静态帽60s/整包300s保持独立，原序列化失败及两次25s超时都保留。与前143的SF49/三源snapshot逐字一致，nodeid精确互斥、合计161（56 owner/68 stage/19 guard/18 affected binding）。旧77冻结绑定仍只属于旧epoch，没有在此全量复跑。

ENTRY SHA `6f9bef022379252b29bd2a71dc5d219349569939e6cc09e44c2174aa742560bb`；tests SHA `a19d0c6434df6fd557294591aa08fc968e2bf5ef17f2bded26142f07d513f1ae`；scientific src仍为 `26b919e385f9d7042587db490dab694fc5bf1643665ab4bf94a1c9bac8087396`。saved constructor/watcher草稿使用单一attempt-state、原unit/kernel/code绑定、partial owner与原异常强持、身份无效拒绝foreign cleanup。单位stub恒real_owner=false，只使用logical context与当前PID/RAM；public issuer和saved CLI仍关闭。

保存核验：`D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_owner_binding_completion_v1_non_authoritative/checks_01/saved_checks.py`。见[报告](../../results/tables/staged_rts24_saved_fresh_owner_binding_completion_v1_non_authoritative/validation_report.md)。新checker明确区分frozen/current，future源码不自动继承161。旧导航正文逐字保持；旧verifier全文pin限制及首次失败见owner报告，当前checker用还原的旧导航字节核原pin。

下一步先固定trusted saved supervisor/permit issuer、actual role执行和最终父采用的scope/DAG、完整调用量、最大合法context与四record、发布/cleanup失败窗及总预算，再进入最小有界实现。实际saved F、B/C/E replay、solver和新模拟小时均未启动；actual OUTPUT/父目录不存在。原scope-budget、P1全683、原guard/outer、40+5+5/180s及targets/字节帽保持。actual issuer/supervise/public saved入口、昂贵失败/arming/host I/O硬中断、整链资源准入继续OPEN；fresh/parent局部verified和整包scientific/resource/formal全部false。

恢复从本页和C计划/blocker开始，刷新Git/进程并运行当前保存检查。root唯一writer，R3继续独立只读PRE_SEAL；活动目标继续，本检查点没有seal、official verdict或运行授权。
