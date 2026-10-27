# None identity 接入：封装超时与重复输入读取交接

2026-10-28，DRAFT_NONAUTHORITATIVE，起点522321cf673159f0bfc02a2f629092206ab5359c。承接[方法候选交接](continuation_handoff_20261028_saved_fresh_image_none_v1.md)，原用户指定的[wire WIP](continuation_handoff_20261026_saved_fresh_wire_data_wip.md)继续作为历史入口；不得回到旧draft重做或重置预算。root唯一writer，既有wire_root_review只读PRE_SEAL，无official verdict、production seal或运行权限。宽goal active，完整F未完成。

## 当前可证状态

新增audit接入在置busy之前核exact class、class image binding、held code/default/kw/closure和native id；metadata getter产生的native object.__getattr__仍走原busy=false早返，不扩_internal或放宽reentrant。`_audit → _audit_entry → _observe_machinery → _image`三条调用边均default-held，audit直接四个commit和machinery两个commit均用held image。Probe精确核各default，原fresh image、cache、ownership、source bookend与optional计数保持。

六项native-audit逻辑guard用例在v2成功完成；v3也全部完成。覆盖实际proof/native getter时序、两种busy状态的setter trap、defaults同步换绑并重算commit、同code/default clone绑定、三条调用边中的class替换、exact type及sticky cleanup。它们使用真实native audit dispatch和exact helper class，owner/runtime仍是逻辑fixture，不能证明实际kernel owner。非audit旧admit/authenticate/close、未知hook、无事件ABA和任意RAM仍不获认证。重复None事件刻意减少，完整observable/fault trace不等价，all_unselected_events_verified=false。

命令尺寸由v1的30014/30000降到v2/v3的29705/30000 UTF16。Prefix逐行缩进4→1，核原token与压缩token确有差异、忽略INDENT文本后token结构一致、AST/行号/co_lines及递归运行CodeType字段一致；仅列位置/linetable可变。payload的允许comment-space变换、原位置AST、精确CodeType、dictionary与marker均核；不声称prefix精确CodeType或完整traceback等价。

## 三次attempt均未达到cold

| attempt | 实际终态 | unit / cold |
|---|---|---|
| NFC v1 | size30014超帽；拒绝checkpoint保存 | 0 / 0 |
| NFC v2 | size/register通过；14调用13成功/1 error，case07旧AOC5 receipt缺drain_reason等父端字段；拒绝checkpoint保存 | 1 child、14调用 / 0 |
| NFC v3 | 修完整receipt fixture；size/register通过；14本体打印OK，但capture timeout/killed，缺最终report；拒绝checkpoint保存 | 1 child、14调用 / 0 |

v3采用15文件packed成功布局，保留旧15失败文件。Registration内嵌新helper原bytes、transport和command，继承旧输入/snapshot且逐次回读；parent的profile admission改从exit内嵌记录读取，原全部绑定检查保留。每phase区分path pins与内嵌canonical/raw bytes，下一phase/checkpoint重开。Unit有序输出admission、逐项start/end和最终report，父端严格核每行canonical及换行；失败也交叉核raw/streams/process/drain。Saved packed上界57352≤65536，有派生报告拒绝后的重构校验；当前未执行saved或cold，不能把静态布局当动态通过证据。

**v3 stdout恰29帧**：admission + 14组start/end，没有report。stderr末尾是Ran14 in2.004s、OK；这只证明runner内测试调用完成，不支持unit phase/package通过。Capture为returncode1、error timeout、killed=true；HANDLE、pipes、reader threads终态关闭，无截断、cleanup或reader error。固定代码顺序将停止窗口界定为runner返回后、最终report emit前的check(reg)区间；没有stack，不得再归因到某个具体read或函数。独立reviewer已重开227个当前input pins、11个helper pins和全部raw；effective inputs933。Checkpoint的accepted只接受拒绝元数据，diagnostic_accepted=false。

## 冻结证据与费用

恢复先读以下端点，再核它们绑定的root和source。执行过的所有源码、scope与结果均冻结；不修v1/v2/v3原路径。

| root（均在results/tables） | 文件 / bytes | 端点SHA256 |
|---|---:|---|
| staged_rts24_saved_fresh_nfc_v1_non_authoritative | 4 / 97300 | checkpoint.json f5c99fc1731a43aaa17e883c4b114ef98c2191b7f3492738906b132dd2de4b84 |
| staged_rts24_saved_fresh_nfc_v2_non_authoritative | 11 / 811960 | checkpoint.json 5cb9ce80769e5b4fdf36ac74a4047328ad11b36d312af9b012f7802c71f6ef4f |
| staged_rts24_saved_fresh_nfc_v3_non_authoritative | 5 / 601738 | checkpoint.json dd669b1f06ce7e5e174ebd5c9cc8f0fc6b2fcebdd6fbe84ae8b69bfd15b28731 |
| staged_rts24_saved_fresh_nfc_metadata_read_v1_non_authoritative | 2 / 163288 | inspection.json 5181393e8b0da03d316513d7ba839ea335fe80a77159144b1685bf41534600d1 |

| 计费阶段 | 秒 |
|---|---:|
| v1 size + rejection checkpoint | 0.8044742999991286 |
| v2 size / register / unit / checkpoint | 0.7074386999884155 / 0.955513200009591 / 3.188146600004984 / 0.44659089999913704 |
| v3 size / register / unit / checkpoint | 1.3745537000067998 / 1.064674900000682 / 4.089947800006485 / 0.9246378999960143 |
| 单次只读metadata trace | 0.656758400000399 |

原包共**14.212736400011636/30s**，其中static6.934642000000167/22、unit7.278094400011469/8；22文件1674286B≤30文件/4MiB。单测只余约0.7219056s，不能用剩余总额度再开整组；不退款、不重置或转移旧余量。新scope均显式续记旧费用和次数，累计最多2个unit child/28次test call、0 cold。

最新累计账为static **320.00913560004415**、pytest **366.48897970000326**、unittest **89.98638920001758**，总 **776.484504500065s**，不接受 **34条**。这是既有capture计费口径，不是本轮开发墙钟；编辑/审查/Git、Python初始启动和最终记录写入沿前驱规则不计capture，无模拟小时推进。

## 已得到的新瓶颈证据

唯一≤2s无child的metadata诊断，完整检查自身0.6196334000123898s，合计计费0.656758400000399s。仅追踪显式Path.read_bytes：2496次、946个路径，1550次重复；读取96117780B，唯一39571662B，重复56546118B。路径读取次数分布为1次13、2次678、3次54、4次43、5次156、6次1、7次1。完整有序journal以压缩canonical JSON保存，由同一诊断脚本自重放核raw/compressed pins并重计；临时wrapper在finally恢复。独立reviewer随后成功独立解压和逐项聚合，2496行、946路径、重复字节和histogram全部一致；7输入pins、Source49/epoch、三端点与22文件1674286B也重新匹配，无open PRE_SEAL finding。该结果描述冻结check路径的重复形态，不证明本次timeout的具体因果，也不覆盖importlib/native隐式I/O。

## 下一步

1. **先解决验证DAG重复读取，再考虑新的真实窗口。** 从已经固定的expected pins/端点构造合法合并，发现同path不同expected pin必须拒绝；每phase重新fresh核每个唯一路径，保留所有旧特殊schema/状态/权限断言。不能把本次观测到的pin替换为外部expected truth，不能跨phase缓存或跳过source bookend。
2. 独立后继需先固定整个控制器路径和预算，覆盖before-test admission、test完成后校验、最终report、父端保存与关闭。v3的14 body完成只能复用为定位证据；原失败仍保持，不能改写成unit accepted或拿missing report当通过。原unit余量不足整组，不直接重启v3或静默续时。
3. 方法/元数据改进闭合之后，才重新审查有限import检查的资源与次数；当前实际证据仍止于旧PFC1真实512窗口，1024或自然返回尚未观测。完整import、OBSERVED profile、LIVE成功/故障矩阵、真实producer/owner/Job/bootstrap、ACK/issuer/permit、quiet/返回与父端采用仍未完成，F无可靠整体完成时间。

Source49原49 raw/epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875不变；60本地module图与本地显式model/Highs/solver调用0保持。E/U、独立TCB/native、完整runtime/P1/role/permit/F/science/resource/formal/run authority全部false。本轮0 adapter/模型/solver/真实role/Job；39项并行文稿/图件/文献及共享导航正文保留。Git只发布本轮范围和四导航前置段；远端hash以同步后的实时回读为准，不能声称全局worktree clean。

## 同步范围与恢复入口

发布准备期间，exec_command创建进程曾反复返回Windows os error5“拒绝访问”，随后恢复；没有更改Windows服务、ACL或安全策略。恢复后，独立reviewer和root分别完成只读audit，重新匹配22文件1674286B及完整journal。发布前HEAD核为522321cf673159f0bfc02a2f629092206ab5359c、index为空；root随后准备49个新文件与四导航前置段，53 blobs、39项范围外原字节已逐项核对。

`.git/codex_none1024_publication_baseline.json`保存原39路径精确pins；`.git/codex_none1024_publication.py`仅作本轮root分步audit/prepare/stage/verify/commit/push辅助，不属于科学输入或运行权限。导航工作区仅前置段+原baseline bytes，暂存仅前置段+HEAD bytes，保留共享正文dirty。Git发布以包含本交接的提交和实时remote回读为准；检查stage/commit每个blob、index空、本轮clean及39 unrelated dirty保留，不能把前次远端hash称本轮同步完成。恢复仍先核实际Git/process/root/source，不因本交接扩大任何运行门禁。
