# Source v3 保存诊断与整链预算 v7

historical v3/source batch v3/validator v2 已接入全部已处理小时的 packet 再验证、三轮 parent namespace 检查、最终 bookend 和独立 cleanup。已有 owner 保持原路径，并实际拒绝新 batch 类型。全部16个正式准备门保持 OPEN；总 wall/RSS/storage 准入上界继续为 null。

一次保存 H3/M5 双 Reader 已终态 exit0：batch 88.385155s、worker 90.296220s、outer 94.000000s。294 项 unit/fault/回归通过；18份unit snapshots和24份probe snapshots与对应源字节一致。21个detached拒绝项包括old owner拒新类型。旧950 bindings、465 case/444 owned和1322启动pins fresh核验；未新建Job/selector，native为0。

每个 Reader 只有一次 constructor traversal、各重新验证3个packet、各做3轮namespace、token独立。临时packet+selected-frame内容估算为122826/120546B。2秒采样tree RSS峰值197238784B；输出目录循环内logical峰值537988B，均非完整资源上界。case read-open累计23102；滞后heartbeat为18987，读取活动不等于科学进展。

科学核对是 saved audit identity-bound 的内部一致性重构，复用原join/projection、shared manifest resolver、显式one-field stand-in，还借用新current的normal decision；未直接读取旧raw science，也不是独立oracle。执行worker的输出字段重命名未列入其三项源码替换列表，已在postcheck.provenance_correction明确补记；它不改变科学路径。

| Reader | constructor s | all-H再验 s | final bookend s | 含cleanup总s |
|---|---:|---:|---:|---:|
| 1 | 43.386240 | 0.055859 | 0.522184 | 44.979971 |
| 2 | 38.454273 | 0.057908 | 0.537793 | 39.900041 |

这些时间嵌套于batch，不重复相加。与旧H3 83.976s并非同次交替对照，不作提速或H192预测。

T192、W=0且assessment.needs_next_hour=false的条件调度仍有773 source batches /1546 Readers /149380 prefix-hours。当前owner基线597520保存Job replay（M5 2987600 stage；M232仅结构条件值138624640），不扣减。若未来合法采用v3，条件Job replay为298760；还需149380次validate_current、298760次full packet digest、154018次新增model dependency snapshot、13914个根listing及23963次named guard扫描。这些是代码结构推导，不是运行时计数。隐式Path stat、normal内部hash/数值模型及完整owner的成本没有穷尽。

E168/F≤24、recover_then_check、primary births只取enrollment、followup债务保留、缺必要source为U的合同和旧边界/target-business证据继续复用。q=g+c≤f*w 与 q+r≤D 分开。H168成功且无需next时为504 events；H192为576（均含额外terminal调用）；alternate witness每个加2且尚无独立W上限。旧32-event toy cap不足，archive/physical资源仍需具体profile。小时数本身不允许终结，有pending primary时保持attempt。

失败unit_01的bytes编码6fail、unit_03的copyreg懒cache1fail及所有当时bytes保留。当前guard先预热标准dataclass cache再exact pin；runtime记录由独立seal检查，公开checker漂移由独立程序拒绝，半构造Reader提前保留，finally直接cleanup并清私有引用。constructor-failure证据是actual AST + exact-MRO stand-in owners；真实保存文件/owner故障矩阵、private backup任意反射和bookend间ABA未闭合。

单Reader128MiB加values64MiB的重叠内容cap合计320MiB，不包含observed、model、allocator或RSS。全部16门、owner adoption、真实H168/≤24 producer连接、episode终结、writer/crash、M232、合法reuse DAG、same-contract bounds、seal/fresh official与具体formal/native authority仍需完成。本scope只读pre-seal findings没有official verdict。当前canonical plan/blocker已在旧950包pin中，字节保持；没有formal gate变化。
