# Reference validation 同步窗口后继范围

状态：DRAFT_NONAUTHORITATIVE，设计未实现。2026-10-19；root 唯一 writer。
依据：parent_window_review 对现有 Parent-validation3、post-negative2、Handoff5 的独立只读分析。
本文不能代替 Parent4 验收、完整性能审查、scoped PRE_SEAL 或正式运行权限。

当前 reference-window1 仅服务 Parent4 自己的 Actual run/validate，固定一个 owner 和两个 parents。
Handoff 内部另外克隆 snapshot._build 的路线不会经过它；仅替换 Parent import 不能完成优化接线。

| 现有同步窗口 | 可复用 reference logical calls | 新书挡目标 | owner 明细 |
| --- | ---: | ---: | --- |
| 每个 bundle | 48 | 2 original + 46 borrowed | 三 Actual 各16，Rref为0 |
| 单个 records_bundle | 102 | 2 original + 100 borrowed | 三 Actual 各34，Rref为0 |
| 每轮 post-negative bundle | 48 | 2 original + 46 borrowed | 三 Actual 各16，Rref为0 |

Actual validate 的12次来自 Parent._source 内 prepare/bind，经 request_document 和 snapshot.rebuild；
另外4次来自 output inspection 的 entry/tail source rebuild。records 为每个 Actual 两次 validate，
中间一次 rebuild 额外调用两次 _build，因此是3×(16+2+16)=102。
Parent-validation 的13个 bundle 加1个 records_bundle 合计726 logical，目标28 original/698 borrowed。
三轮 post-negative 必须分别关闭：合计144 logical、6 original/138 borrowed，不跨轮保留。
这些是静态调用计数，不是耗时或预算估计。

canonical output sequence.inspect 仍全部执行。每个 bundle/post-negative 的10个 validation body
分别为7个Rref和3个Actual；records有20个 validation body及Handoff records额外4次直接inspect。
这些检查验证各Parent自身的保存输出，不属于嵌套reference dependency cache。

建议复用边界沿用现有 outer source window：四个guard已被原Bundle取得，三个Actual的reference mark
已设置，窗口内部是同步验证；records窗口在mkdir、journal append、retention callback之前关闭。
不为缓存引入新锁顺序或延长至callback、Job、下一窗口、下一post-negative调用。

新validation helper应有两个静态私有入口，分别固定 bundle=48/records_bundle=102 和
post_negative_bundle=48、host schema、精确clone caller。不能伪造两-parent row适配现有_bind。
四-parent admission同时绑定原Rref owner/completion/raw/issued bytes/guard，三个Actual各自的
owner/raw/guard/lane及其reference owner/completion，四个held guard、三个_reference_held、creator、
共同source binding与reference root/terminal/request/archive cap。

科学key允许在三个Actual间相同；读取site须逐owner计数，Rref frame不许借用。继续要求完整context
递归类型/签名、exact clone _build及直接rebuild的code/globals、完整saved namespace/files首尾view、
每borrow/tail/clear的ReplayResult深层类型/签名。第二key拒绝，失败sticky，主异常保留。
source tail materialize及签名相等后才能做reference tail；body失败不新做tail I/O。
finally独立关闭reference generator并确认gi_frame=None，再清除source cache与owner-site inventory；
全部收尾成功后才产生complete receipt。

新receipt明确cross_actual_reference_payload_reuse=true、same_per_parent_reference_observation_schedule=false，
并记录每owner logical counts、original/borrowed、entry/tail各1、bookend_only_freshness、两cache清理。
actual_output_inspection_cached=false、cross_window_reuse=false、between_owner_calls_ABA_covered=false。
不声明旧逐owner失败顺序或逐call freshness等价。

接线仍需版本后继：Parent-validation4、post-negative3、Handoff6及其Common/Genesis私有route图、
integration helper/harness后继。旧canonical snapshot/sequence/数学/输入/阈值保持原字节。
所有新路线需定向owner/caller/key/site计数与失败注入、当前scoped PRE_SEAL、真实保存payload oracle，
再做新的固定资源完整four-Parent/paired/close/reopen诊断。完整优化链及正式门仍OPEN。
