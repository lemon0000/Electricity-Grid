# F：1024控制器单测完整终态，后续预算拒绝

2026-10-28，DRAFT_NONAUTHORITATIVE，起点7ad9c6f81d38c353459002855116a9ce1e44539f。接续[pin方法交接](continuation_handoff_20261028_saved_fresh_pin_memo_v1.md)，本包合同为[执行前scope](staged_deliverability_c_saved_fresh_census1024_controller_scope_v1.md)。宽goal保持active；本轮是progress，完整F未完成。root唯一writer，既有wire_root_review只读PRE_SEAL，无official verdict、receipt或production seal。

## 当前端点

真实import证据仍到PFC1的512窗口；本轮0 cold，1024未运行。NFC4首次取得当前14节点的完整30帧、最终report与子进程exit0；随后根据实测控制器开销主动拒绝后续性能准入，未进入startup/profile或actual1024。checkpoint也因自身1s帽不足记录accepted=false。不能把单测闭合写成整个包通过，不能把本轮pre_seal写成超时或两次check的实测。

Root为results/tables/staged_rts24_saved_fresh_nfc_v4_non_authoritative，**7文件726621B**；checkpoint.json为2222B，SHA **774f4978e333bb05b79f6245f86e2e4b6faf4b2d3ff566046712f2dc84be6b4d**。size、registration、unittest.exit、pre_seal.exit和checkpoint均已执行冻结；源码、scope、policy及其他input同样不得原位修改。恢复先读这些原bytes，不重跑v4。

## 已完成的实现与核验

固定NFC v3 check为leaf，保留其全部fresh读取；不接入pin-memo候选，不再递归增加历史checker。core31/probe29/parent28由固定constructor只迁移路径，helper census1024_none_v2原bytes保持。继承输入924与227精确无冲突union为933；当前直接输入345、effective输入1051、helpers12。登记203个runtime origins；显式预载pickle、unittest.mock及继承测试使用的stdlib，size/register/unit前后origin集合相等。

独立PRE_SEAL先发现并在首次size之前修复：缺失import_policy、register缺fresh origin census、registration可同步删项/改控制字段、checkpoint无用途的重复leaf，以及继承测试引入pickle/mock后的确定性origin漂移。policy直接复制冻结NFC v2原4745B，SHA 4b731fc38ed2b52bff727acf0b02e4b8da7396cb17f2354225b34348155d9e9c，进入输入、manifest和16文件/4MiB布局。整个registration按fresh集合、graph、source、migration、command、helpers、snapshots及控制字段重建，以canonical JSON核精确键集合和值；test07加入9类删项/预算/node/authority/JSON类型反例，原14节点和全部原断言保留。

唯一unit有序30帧（admission、14组start/end、最终report），**14 run / 0 failure / 0 error / 0 skip**，runner本体1.983s，stdout4195B、stderr2230B，child PID752、exit0。HANDLE、pipes和readers均关闭，无kill/truncate/reader error/cleanup error。独立reviewer重算345直接输入及49 Source pins、7份新增helper快照均零差异，并核原raw streams SHA和完整帧序；unit findings已闭合。该review不是official状态。

## 预算、拒绝与后续门槛

| 阶段 | 终态 | 计费秒 / 原帽 |
|---|---|---:|
| size | accepted | 1.5642850000003818 / 2 |
| register | accepted | 1.2997981999942567 / 2 |
| 14节点unit | accepted，完整report/exit0 | 7.213357899992843 / 8 |
| pre_seal | rejected，性能finding未闭合 | 1.4894225000025472 / 2 |
| checkpoint | rejected，自身超帽；原元数据已写入 | 1.402561800001422 / 1 |

Unit总开销减runner约5.23s，包括四次完整check和启动/收尾；不能当作逐check独立计时。但结合register1.2998s，已不支持pre_seal在2s内执行两次完整check的估算。原check完整重建current registration也比仅固定legacy leaf更贵，先前只用leaf约0.56–0.71s估算是不充分的。

因此本轮向唯一pre_seal输入canonical findings：unit_must_fix_open=[]，must_fix_open为pre_seal两check的2s帽与checkpoint的1s帽。driver在第一次check后因finding非空拒绝，原findings完整保存在pre_seal.exit的packed artifact；没有执行该阶段第二次check，也没有启动cold。随后唯一checkpoint实测1.4026s并accepted=false，保留两条新增不接受记录，不重试/续时/退款。registration charge是producer计时并经类型/范围核验，不是独立时钟认证或任意FS防篡改。

本包static **5.756067499998608/22s**、unit **7.213357899992843/8s**、合计 **12.96942539999145/30s**；剩余static16.243932500001392、unit0.786642100007157，总17.03057460000855s，均留在原包，不转移。前驱原30s包17.533584500015422s及旧余量、所有失败原bytes保留。

最新累计static **329.0620681000539**、pytest **366.48897970000326**、unittest **97.22373020000305**，总 **792.7747780000602s**，不接受 **36条**。这是沿既定capture口径的费用，编辑/review/Git及Python初始启动等不在其中，不是全部开发墙钟。旧30文件2133521B原样保全；加本轮为37文件2860142B，不能将分开的storage caps合并解释为资源准入。模拟小时推进0。

## 下一步

停止v4，后继先依实际full controller开销重排整包DAG与caps，见[未执行后继预算草稿](staged_deliverability_c_saved_fresh_census1024_phase_budget_scope_v1.md)。不为取得更好局部比例再跑pin-memo基准；目标仍是唯一actual1024/自然返回窗口及saved/reopen完整终态。新后继需固定source/constructor/输入集合/布局，完成受影响检查与独立PRE_SEAL，再按其自己的包执行；v4通过的14节点是精确当前bytes证据，不自动替代新driver的验证。原v4源码和上限不变，新分配不得伪装为原包续时。

Source49原raw与epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875保持。原Oct26两项数据根风险的已闭合范围仍见[根修复交接](continuation_handoff_20261026_saved_fresh_wire_data_root_repair.md)；本轮没有重新打开这些已闭合的数据合同，也没有把其验证扩展为真实producer真实性。

OBSERVED/LIVE、真实producer/owner/Job/bootstrap、ACK/issuer/permit、quiet/返回与父端采用仍未完成。无实际P1/OwnedChild/Job/F、model/solver、native校准或长实验；所有F/science/resource/formal/run authority字段false。现场只有VSCode Jedi服务，无活动实验。39项并行论文/插图/文献dirty原bytes保留；四导航只暂存本轮前置段+HEAD正文，不能报告全局clean。最终发布hash以包含本交接的commit及remote实时回读为准。
