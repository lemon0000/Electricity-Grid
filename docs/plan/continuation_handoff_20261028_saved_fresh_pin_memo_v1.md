# SHA派生计算复用方法完成，继续准备真实1024窗口

2026-10-28，DRAFT_NONAUTHORITATIVE，起点a0cba881d6a4c25a3cf126dc6ccbc89aca49d084。承接[上一交接](continuation_handoff_20261028_saved_fresh_none1024_rejection_v1.md)。本轮为progress：完成保持全部fresh读取的方法反例、完整冻结check的双顺序对照和saved/checkpoint，得到不宜直接接入候选的新证据。宽goal保持active；完整F未完成。root唯一writer，既有wire_root_review只读PRE_SEAL，无official verdict、production seal或运行权限。

## 已执行的方法包

Scope在[pin-memo范围](staged_deliverability_c_saved_fresh_pin_memo_scope_v1.md)。helper为experiments/staged_rts24_saved_fresh_pin_memo_v1.py，tests为tests/test_staged_rts24_saved_fresh_pin_memo_v1.py。文件读取、路径、次数、顺序与所有旧expected断言保持；只对exact相同bytes复用SHA派生结果，返回fresh dict；非bytes/变raw/超帽执行原pin。每次原loader仍创建fresh module；不复用JSON、实际执行code/module或跨check结果。三个legacy文件为allowlist，实际每个new check包装4次module加载，不能将allowlist数当执行次数。

Normalized pin AST自动核同一纯公式与primitive依赖。原函数和actor wrappers核code/default/kw/closure tuple及每个cell identity/value；held primitive/module bindings与未管理globals在前后bookend核对；finally恢复pin/load并清空缓存，existing primary cause保留。类方法本身仍依赖冻结helper source，不构成任意RAM/Python对象或native行为认证。

唯一8节点普通unit通过，0 failure/error/skip，无child/native hook/cold。包括fresh dict不污染、逐duplicate持续变更、A→B→A、逐read异常同对象、expected冲突与alias、容量/nonbytes回退、SHA首错不缓存、原函数/actor wrapper/closure/global/primitive漂移和cleanup原cause保全。Registration的956 input pins、3 reference pins和4源码快照经独立reviewer逐项匹配；before-test admission先落盘后runner，完整stderr/report一致。

## 完整check对照及决定

固定顺序old/new/new/old，仅比较冻结NFC v3 check，未进入whole controller或cold。

| case | 秒 | 显式read数 | 与旧轨迹相同 |
|---|---:|---:|---|
| old1 | 0.7122484000137774 | 2496 | true |
| new1 | 0.5553024999971967 | 2496 | true |
| new2 | 0.5529372999881161 | 2496 | true |
| old2 | 0.5566523000015877 | 2496 | true |

总new/old为0.8733857582172452；两组配对为0.7796472410277864、0.9933261750405756。总比存在明显顺序/初次加载不确定性，不能表述为稳定12.7%提速；第二组差异约0.7%。每个new有2474次pin、1562命中、912 miss/entries、0 fallback，保留39577485B raw payload；结束后entries和resident均0、closed=true。payload约39.6MB不是heap/RSS或整链资源准入。

**候选保持candidate_adopted=false/production_helper_selected=false。** 暖态收益与约39.6MB raw缓存成本不支持直接接入后续F，不再为了寻求更好比例追加本方法基准。完整控制器和actual import收益尚无证据；不能据本方法包准入cold。原NFC v3 timeout仍是失败，缺最终report不因本轮8 unit通过而补成通过。

四个压缩trace均重开为相同2496行canonical path/length记录，压缩数据各19997B；独立reviewer核了压缩SHA、解码内容一致性及行数，raw SHA由冻结driver的saved/checkpoint重放，未再单独独立计算。Trace observer没有每read追加SHA，不冒称每行独立raw SHA。Input pins在阶段前后核对，Source49原49 raw/epoch不变。独立复核无open PRE_SEAL finding，但非official。

## 端点、费用与保全

Root为results/tables/staged_rts24_saved_fresh_pin_memo_v1_non_authoritative，8文件459235B；checkpoint.json SHA **e340c6ee3758175c78c2992c57586000a021ead268158e3e67571bb16243297b**。先读registration、unittest_admission/exit、pre_seal_findings、benchmark/saved exit和checkpoint，重开其中绑定的原bytes与全部false gates。

| 阶段 | 计费秒 |
|---|---:|
| register | 0.17416020001110155 |
| 8节点unit | 0.023983099992619827 |
| 4次完整check对照 | 2.7852182000060566 |
| saved | 0.16576309999800287 |
| checkpoint | 0.17172349999600556 |

本包static3.2968650000111666/8.5、unit0.023983099992619827/0.5，合计3.3208481000037864/9s。连前驱原30秒包为**17.533584500015422s**，static10.231507000011334/22、unit7.3020775000040885/8；30文件2133521B≤30文件/4MiB。所有失败和旧计费完整保留，不接受计数仍**34**，无退款/重置/挪用余额。

最新累计static **323.3060006000553**、pytest **366.48897970000326**、unittest **90.0103723000102**、总 **779.8053526000688s**。沿既有capture口径，编辑/审查/Git、Python初始启动和最终记录写入不计capture；这不是开发墙钟。模拟小时推进0，本轮0 adapter/model/solver/实际role/Job/F，0 cold。

## 下一步

继续完成真实1024/自然返回窗口，而非再造局部方法分数。已写[独立控制器预算草稿](staged_deliverability_c_saved_fresh_census1024_controller_scope_v1.md)：不接入本cache，固定legacy checker为leaf，避免新版本不断递归膨胀；保留原所有fresh观察点，新输入另外核。该草稿尚未实现/登记/运行，必须先核实际source/DAG/size、完整14节点unit和最终report、PRE_SEAL、新startup/profile，再唯一actual窗口。新包预算单独登记，旧unit余约0.6979225s不足整组，不能转用或重启v3。

当前真实import证据仍止于PFC1的512窗口；1024未执行，完整import未自然返回，OBSERVED/LIVE及producer/owner/Job/bootstrap、ACK/issuer/permit、quiet/返回与父端采用未完成。F无可靠整体完成时间。E/U、独立TCB/native、完整runtime/P1/role/permit/F/science/resource/formal/run authority全部false。

Git按本轮method/scope/tests、完整八文件root、此交接和后续未执行预算草稿加四导航前置段发布；只暂存导航的新段+HEAD正文，工作区正文和39项并行文稿/图件/文献dirty原字节保留。最终hash以含本交接的提交和remote实时回读为准，不能称全局clean。恢复仍先核Git/process/current root与Source49；已执行的本包代码/文档/结果全冻结，后续实现走独立路径。
