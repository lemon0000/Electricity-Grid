# None identity 方法候选完成，真实入口接入待闭合

2026-10-28，DRAFT_NONAUTHORITATIVE。起点273f96bf16b99b4545962afe9253fe5f4bba958c，承接[真实512窗口](continuation_handoff_20261028_saved_fresh_parts512_v1.md)。按[原方法范围](staged_deliverability_c_saved_fresh_image_none_scope_v1.md)及[登记修正后继](staged_deliverability_c_saved_fresh_image_none_scope_v2.md)执行。root唯一writer；既有wire_root_review只读PRE_SEAL，无official verdict、production seal或运行权限。宽goal保持active，完整F未完成。

## 本轮结果

新helper仅改_image：default持有native id，在每次调用内惰性复用id(None)，首次None和全部非None仍按原顺序调用native；原image_pin、字段读取、tuple结构不变。probe25仅新增_image default的逻辑held-proof检查，不运行真实probe、不迁core/parent、不进入真实import plan。第二次以后的None审计事件及其第三方hook副作用被有意消除，因此不能称完整observable/异常轨迹等价；all_unselected_events_verified=false。

v1 register误读前驱registration不存在的python字段，0 unit/0 cold。原driver、registration_failure、rejection checkpoint共三文件冻结；六份源码另存独立post_failure_not_prerun snapshot，executed_input_bytes_verified=false。v2改读已绑定PFC import_policy的python字段，test只机械迁移OUT一次；原helper、probe、constructor、方法及阈值未改。v1失败和全部费用保留，不重置原14秒包。

v2 register登记893输入、8 helper；12/12 unit通过，0 failure/error/skip。包含全image/canonical/digest、全部依赖变异、pin独立与生命周期、字段getter顺序、native id事件序列、首个None/最后非None异常primary、被刻意减少的第二None事件、default替换拒绝，以及独立metrics validator的20个伪造/NaN/Inf/type/order/flag/ratio/counter反例。新事件序列恰为旧序列删除首个之后的None项。

唯一fresh unit child安装一个native audit hook，默认与结束均惰化、不可卸载，随child退出。成本门槛只覆盖synthetic active-state/nonselected B_S _audit分发，没有真实owner/kernel。每轮每variant 48次image+digest，old/new、new/old、old/new三轮：

| 量 | old | new |
|---|---:|---:|
| 每轮native id事件 | 12336 | 7248 |
| 每轮None事件 | 5136 | 48 |
| 每次image的native id/None | 257/107 | 151/1 |

有分发总耗时new/old **0.7216235352290478**、中位比 **0.7010460076315919**；各variant另20次gate惰化调用的总比 **0.9647897448368878**。三项达到预设≤0.95/0.95/1.20。gate惰化时hook仍安装；不能称无hook测试，也不能把这个方法比例外推为真实完整import收益。

child PID9340 exit0；HANDLE/pipes/readers全部终态，无kill、cleanup/reader error或截断，stderr1786B、stdout0。direct child peak44982272B，仅为该unit观测。独立reviewer核893 input/8 helper、unit前置pins、三比例/计数/hook及统一18个false gate，无open PRE_SEAL finding；非official。saved/checkpoint已独立重算metrics并接受这个方法诊断，candidate_adopted=false、production_helper_selected=false。

## 终账和恢复

v1失败register **0.15544039999804227s**、拒绝checkpoint **0.12902730000496376s**，合计 **0.28446770000300603s**。v2：

| 阶段 | charge秒 |
|---|---:|
| register | 0.36433820000092965 |
| 12项unit | 2.5347946000038064 |
| PRE_SEAL | 0.6304626999990433 |
| saved | 0.4889495999959763 |
| checkpoint | 0.5007141999958549 |

v2 static **1.984464699991804/7.5s**、unit **2.5347946000038064/6s**；两attempt原包合计 **4.8037269999986165/14s**。三root共 **17文件/794344B**，含失败archive195943B，≤原20文件/2MiB。v2 root13文件/598401B，checkpoint后不再改写root。

累计static **313.074493600044**、pytest **366.48897970000326**、unittest **82.70829480000612**、总 **762.2717681000534s**；不接受累计 **31条**。旧费用/失败/快照保留，未把旧余量重置为新额度。编辑/审查/Git、Python初始启动及最终记录写入沿原口径不计capture，非总wall；无模拟小时推进。

恢复先读image_none_v2_non_authoritative的checkpoint.exit.json、registration、unittest_admission/report/exit、metrics、pre_seal_findings/admission、saved_snapshot与saved.exit；再核v1失败三文件及独立inputs snapshot。PFC1原真实512证据完整保留；Source49 epoch仍acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875，49份原raw未改。

## 下一关口

1. **先补真实入口proof**：现有_audit_entry只核identity，没有连续核_image code/default/native-id identity。本候选不可直接接入cold。独立后继须在读image字段前核held method code/default/native-id，并覆盖同步替换default+重算image、调用中漂移及fault/cleanup窗口；保留全部fresh image/bookend/ownership/source检查。
2. **再做尺寸和有限窗口准入**：PFC1命令已29972/30000 UTF16，新增proof可能超帽；先证明source/payload允许变换及实际尺寸，不凭估计启动。固定问题/次数/预算后，才可考虑原8s内1024或自然返回窗口，不能因局部0.72比例直接重复完整import或放宽deadline。
3. 完整import尚未自然返回，仍需OBSERVED profile、LIVE成功/故障矩阵、真实producer/owner/Job/bootstrap、ACK/issuer/permit、quiet/返回和父端采用。512之后成本未知，F整体无可靠完成时间估计。

E/U、独立TCB/native、完整runtime/P1/role/permit/F/science/resource/formal/run authority全部false。本轮0 cold、0 adapter/模型/solver/真实role/Job。39项文稿/图件/文献并行dirty保持；Git仅发布本轮scope及四导航前置段，原正文保留，远端号以发布后实时读回为准。
