# F：完整 DAG、条件调用量与授权后继设计

2026-10-29，DRAFT_NONAUTHORITATIVE。接续 [Parent40 检查点](continuation_handoff_20261029_saved_fresh_complete_parent_v2.md)，沿用[原 F 范围与预算](staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)、[科学采用 DAG](staged_deliverability_c_scientific_adoption_dag_v1.md)和[外部调用能力合同](staged_deliverability_c_saved_fresh_invocation_development_contract_v1.md)。本设计由 root 唯一写入，独立只读 PRE_SEAL；只形成静态计数和后继实施条件。完整 F、整体性能审查、资源准入和真实运行授权均未完成。

## 原始范围与实际依赖

范围固定为 `saved_P1_actual_21_and_journal_5h`。parent 与独立 fresh 分别从原 B 的政策和 initialize 重建 h=-2..2 的 21 个 actual/reference/recovery 点、五个 accepted hour，再由原 journal reopen 核 130 个 CAS。原 P1 为 683 文件/2,950,863B，journal 137 文件/427,629B。两侧独立生成 query/typed evidence；不能传递 live PointEvidence、另一侧 CAS query 或科学结果缓存。

| 阶段 | 依赖和真实动作 | 关闭条件 |
|---|---|---|
| F0 | approved external host 先持有 source/request/exe/environment；broker 发布 exact context，host 核 RAM 原字节并 ACK；outer capture 后 release | G0、caller image、同一次 context/owner/nonce/绝对时钟 |
| P | parent 独立完整 B/C/E 重建及 parent metrics | 全部 21 点、五小时、原政策/parent/KKT/状态和来源 |
| F1 | parent 预扣唯一 fresh reservation；创建、capture、认证 release | 原 child/argv/transport/manifest/source/context；失败不退款 |
| Q | 新进程从磁盘和同一 context 独立完整 B/C/E 重建 | 相同范围与全 metrics，独立输出 |
| F2 | 内层完整 Job quiet、close、terminal，之后才消费 fresh 内容 | 全历史成员/身份、原流、handles/readers/pipes/writer 和 caps |
| F3 | parent 比较两侧、重核 F.G1/source/caller，发布 comparison candidate 后退出 | candidate 只是候选，不重复第三次 B/C/E |
| F4 | controller 完整外层 Job quiet 后消费 parent/fresh 内容 | 两层成员去重、退出/commit/输出会计；未知只保留 metadata 诊断 |
| F5 | supervisor 独立核两层实际 owner/process/candidate/full metrics、F.G2 | 独立 Parent P1 grant 与整套物理读取义务另行实现 |
| F6 | create-only final observation、canonical 原流读回，再核 F.G3/source/最终会计 | 发布后漂移保留文件和 SHA、采用仍 unknown |

全部 19 个 metrics 字段继续为：`state_sha, state_cas_sha, summary, independent_audit, scientific_outcome, publication_outcome, terminal_entry_present, state_certainty, closed_entry_present, unaccepted_attempt, failure, pending_terminal_checkpoint, pending_cas_objects, unreferenced_final_cas_objects, genesis_sha, head_sha, final_entries, saved_objects, resume_permitted`。另核 21 个 ordinal/role/query/evidence SHA、genesis、五个 accepted state SHA 和六个 prefix binding。

保存终态保持 missing_input/committed/known、accepted=5、last_hour=2、entries=6、CAS=130、next_hour=3、余额0、resume=false、coverage=false 和两个 null；typed CAS 根为 `29517379c102b40b0f0a0b77711db4d936357025e4f53283f5bdec04fcbc7a41`。完整 F 最终局部返回字段仍为 `saved_P1_fresh_process_verified` 和 `saved_P1_parent_adoption_verified`；本静态设计中两者均 false，P2、科学、完整139/F-X、formal 等既有边界保持。

## Parent40 叶片的递归倍数

[静态模型](../../experiments/staged_rts24_saved_fresh_workflow_cost_model_v1.py)绑定 20 份实际 source/spec/旧计数证据的完整 bytes/SHA，并为相关函数给出 AST witness。它只用 stdlib 读取和解析，不 import/exec 目标源码，不读原 P1；以下是人工展开、独立只读核查的条件成功路径，不是运行测量或一般上界。

假设本次 producer 所需全部历史工件存在、历史 profile 与独立 external anchor 合法，且两个非 startup exact graph 已有新合同。D 是 startup profile 中 disk_file_observations 的文件数，0≤D≤128，每文件≤8MiB、合计≤32MiB。D 不是 P1 的 683 文件。

| input_context 种类 | 次数 | 每次 generic call | 每次逻辑内容读 |
|---|---:|---:|---:|
| discovery | 7 | 24 | 87 |
| import_discovery | 4 | 31 | 98 |
| producer capture | 1 | 38 | 109 |
| producer pre-release/post-quiet | 2 | 33 | 99 |
| 合计 | 14 | 396 | 1308 |

额外 generic call 为 saved memory guard 22、live guard 1、producer data callback 1、固定步骤 15；内部合计 **435**，source_dispatch 的 capture/run wrappers 再加 2，得 **437**。program 构建内部 6（dependencies5+capture1），加 source_dispatch 为 **7**。source_module26、transport14、startup_relation7、profile_relation4、audit_saved11、replay12、open_saved_receipt调用22、child decode调用23、memory guard23。每次open_saved_receipt分别解析receipt与retirement evidence，故实际JSON decode为 **44**。14 个 context 反复读 Source49 共686次、source control14次、exe/runtime98次；它们已包含在总读数，不能再次加总。

额外内容读为 explicit import dependency10、dependency source5、DRAIN1、packet codec1、startup Core7，加7D；内部 **1332+7D**，外部读取 Parent40 source 原字节另加1，得 **1333+7D**。D=128 时内部2228次；仅 startup disk 重读部分上限224MiB，不代表所有来源 bytes、RAM 或 OS I/O。

Parent 数据 replay 顶层 callback 为 decode1/unwire1/显式restore1；unwire 内部又 restore1，每个 restore 又 decode1。物理总数为 **restore2、decode3、decompress1**。当前同一 packet 的两次完整恢复有优化空间；后继须保持独立关系校验和失败语义。

上述成功前提目前不成立：真实 profile anchor=None、import/producer exact contract=None、Permission1 的 public issue/verify/claim 永久拒绝、Source49 legacy issuer 关闭。仅填 None 常量也不够，旧 closed schema 要求 permit/run/F 等 false；真正授权需要版本化后继。Parent40 还是 post-spawn owner，没有 launcher 或 P1 reader。启动/入参检查先失败的路径不能冒充成功路径测量。

## LC6 / Helper7 局部倍数

一个叶片的成功序列为 claim → run → LC.G2 → LC.G3 → close。LC.entry 为 **1+7+6+6+3=23**。LC 导致的 runtime.entry 为 **23+prepare1+RUNNING2+CONSUMED2+close1=29**，source bookend24。Project37 graph capture1、check30，实际 `_build`31；37 模块的实际节点、bytes、wall 和内存均未知，50,000节点/256深度/8MiB只是停止帽。

Helper7 前置 construction/bundle 阶段 runtime.entry8，五个 bundle 操作的 verify_bundle 各再调一次，共 **13**。LC 与 Helper 局部合计 runtime.entry42，仍未包括 Loader5 的两次 entry/source bookend、Core import/handoff、namespace 内部图及科学回调和其他进程。原 construction43、producer107或 validator256停止帽均不能作为完整新图的 exact contract。

## P1 读取预算缺口与复用条件

原 E 的[实际旧计数](../../results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/validation_report.md)为 **4319=683 初始库存+2152 单点+801 journal+683 最终库存**。当前 adapter 的同一次 capture/hold + replay 成功分支保留该结构；改变 coordinator、输入范围或重放路径后不能直接沿用。replay 异常 catch 还会加一次完整683库存，另有失败前 partial reads，失败上界尚未闭合。

LC6 固定成功成本为 **2102=53 expectation+683 hold+683 LC.G2+683 LC.G3**。LC.identity 对 held raw/metadata 的核验没有再读 P1 内容。LC 的 G* 与 F 的 G* 属于不同 owner/进程或时间窗口，必须逐一证明关系。

| 条件场景（额外未知成本未计） | P1 内容读小计 | 相对原12500帽 |
|---|---:|---:|
| 原两侧 E + 四次 F.G 库存 | 11370 | 算术余1130 |
| 独立增加一个 LC 与 Parent683 | 14155 | 超1655 |
| 独立增加两个 LC 与 Parent683 | 16257 | 超3757 |
| 一个 LC：同 owner HeldInput 复用，省683 | 13472 | 超972 |
| 再以同次 E final 库存履行 LC.G2，省683 | 12789 | 超289 |
| 再证明 Parent683 与同次 F.G 库存是同一物理读取，省683 | 12106 | 算术余394 |
| 两个 LC：各复用 hold 与 E final、再共享一次 Parent/F.G，共省5×683 | 12842 | 超342 |

这不是对实际新 DAG 选择一个或两个 LC；两侧独立科学重建始终存在。后继要先明确各 owner 的 LC/adapter/Parent 角色，逐调用映射到完整 F，再决定哪个条件算式适用。任何一行都不构成完整上界或准入；未登记的启动、额外 permission/guard 读取、失败、最后 source/anchor/目录成本不能写零，也不能自动提高12500帽。

可证明复用必须同时满足：同一个 exact live HeldInput、owner/thread、raw map、caller image、source/root/anchor bookends；同一次物理 inventory 在同一观察窗口完成两个明确义务，结果由实际 retained actor 提交；root/ancestor identities、freshness 和失败保存完整。只有 SHA相等、字段同名、目录一致或历史 pins，均不能消除独立物理读义务。expectation53发生在 hold 前，不能倒用未来 raw；若要改变时序或派生方式须新协议和独立审查。

Parent40 的历史 dependency 审计可设计成 actor-local HistoricalDependencyProof：绑定五份 immutable raw、accepted receipt/retirement、manifest/profile/admission/registration、validator/Parent/transport/source epoch、helper/env/exact graph/external anchor，且先完整 saved replay。条件上可将重复 discovery7次、import4次缩为各一次；capture/pre-release/post-quiet 的 LiveFreshnessSnapshot 仍须真实内容/identity书挡，不能缓存整个 input_context 跨 release/运行/quiet。可消除同次 capture 重复读 import dependency5份、复用已构建 transport 的程序但保留每窗口3份源码 fresh读、复用 held Core、共享同窗口递归审计与末次书挡。以上尚未实施，不计入当前费用节省。

## Source / exe / anchor 读取预算缺口

原两侧 source/runtime 条件基数 **4176** 也不构成新链上界。Parent每个context的严格source/exe/runtime子集为 **84=transport3+Source4949+exe/runtime7+attachments3+helpers22**，14个context为1176；dependencies5、DRAIN1、codec1、startup Core7、外部Parent raw1再加15，得 **1191+7D**。另有 source-control14次，模型分别列出计入与不计入6500帽的值，分类尚未定。原每侧末次anchor复读1、两侧2也另列；严格子计没有把这些读数写零。

LC6的24次source_bookend每次实读Source49，共 **1176** 次。没有整合复用证明时，条件附加路径为：

| 场景 | 严格source/exe/runtime条件小计 | D=0时超过6500帽 |
|---|---:|---:|
| 原两侧路径+Parent+1个LC | 6543+7D | 43 |
| 原两侧路径+Parent+2个LC | 7719+7D | 1219 |

若source-control属于同一帽，两式再各加14；原anchor末次另加2，其他anchor和loaded-module复读、Helper/Loader/Core、外部授权/profile/outer、failure/publication成本仍需完整核算。这些是**原4176路径保持、各附加组件独立执行时的条件加总**，不能称未来优化实现的绝对下界；复用或替换旧路径须新闭包和计数证据。所有场景budget_admitted=false，完整上界仍null。因而P1与source两项帽都要求先完成连接、合法复用和完整计数，当前不能直接拼接各局部通过路径。

静态模型的inventory_domains_distinct只列LC/F域；E.capture/E.final与独立Parent读窗口另在P1场景中表示，不声称已经列全每个读取窗口。

## 保持外部能力架构并实现真正授权

使用原 Host → broker OwnedChild/Job → controller → parent/fresh 的 held capability 与 pagefile mapping/mutex 协议。broker 先发布 exact context，host持有并ACK后才构造controller；十个固定 slot、direction nonce、commit-last、100ms mutex帽、真实 quiet 后 return 消费、历史成员 HANDLE 及主错/secondary 保留继续适用。descriptor/JSON/本地随机 token、同进程 self-test 或一个 pipe 都不单独构成 external authority。

后继实施顺序：

1. 先绑定 approved external host 的实际 source/held request、限定 scope、绝对 deadline、费用帽和本次一次性 reservation；记录失败后的已消费状态，不能复活 Source49 `_SavedLaunchIssuer`。
2. 为 outer/Permission/LC/Helper/Coordinator/replay/schema 建立独立版本化授权闭包：release前精确核实际 child PID/creation/HANDLE、exe/argv、transport/manifest/source/environment/context SHA 与 nonce。child 由真实受控入口获得不可转移的创建能力，限定同一个 LIVE owner，claim 一次；过程数据不能冒充创建能力。
3. child 在授权后的 construction/runtime 窗口按 exact source/root/ancestor/held image 自核，真正 producer 消费同一个 grant；终态同时保留 revoke、resource close 与 namespace/registry retirement。真实 discovery/import profile 必须来自更早 distinct child 的 accepted 原流和独立可信 anchor，并设计 genuine schema，不填 synthetic profile。
4. 单独设计 Parent 的 P1 grant：绑定实际 retained Parent owner、quiet 后窗口、完整683读、root/ancestor/source/context/child packet；它不能继承 child 的读许可或靠 map equality 宣称独立读取。若兼任 F.G1，需要证明同一物理读、同一 authority/window、failure/publication 时序。
5. 把两侧 B/C/E、LC、Parent、outer/profile、failure/retirement、全部 read/graph/packet/编码成本连接到同一个 full F DAG；普通有意义的故障测试和独立 PRE_SEAL 先完成。之后按 agent.md §9 准备实际 Native/P1 有界诊断的具体包及专项授权，当前没有该授权。

OS机制支持上述能力设计，但不能替代 approved source/TCB。Windows 的[显式 handle list 与 Job list](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)控制继承的 kernel handles 与 Job 分配；[句柄继承](https://learn.microsoft.com/en-us/windows/win32/procthread/inheritance)沿用同一内核对象及权限。由此推断：单凭 PID/image/传来的 JSON 不能证明所执行的 Python 对象闭包，仍须固定可信入口、能力来源与实际 child 绑定。

## 绝对时间、资源和剩余准入

原 source 的 stage allocation 为 prepare10、parent45、fresh40、inner_quiesce5、inner_terminal5、parent_compare15、outer_quiesce5、outer_terminal10、final_check15、final_publish15、failure15，合计180s；成功阶段分配165s，失败预留仅消费总预算余量。fresh envelope50s，parent envelope125s；阶段和全局时钟不能续期。180s是设计帽，不是 ETA、实测或当前可执行全链停止证明。

Python [subprocess 文档](https://docs.python.org/3.12/library/subprocess.html)说明部分平台的初始 process creation 不能被该层 timeout 打断；[anonymous pipe](https://learn.microsoft.com/en-us/windows/win32/ipc/anonymous-pipe-operations)的同步写可能阻塞。因此外部 host 必须通过已 armed broker Job 覆盖 START后的构造、同步 I/O 与发布等待；arming本身费用和停止能力另列。host 最后编码/保存尾部、kernel调用硬停止和瞬时RAM仍 OPEN，不能以 wait(timeout) 或线程超时替代。

Job树 sampled RSS≤1GiB、process commit≤1GiB、Job commit≤2GiB，host另计；嵌套成员按 PID/creation 去重，不能叠加重复 Job样本。输出原17targets、8MiB/64文件、member_handles1024、record128KiB保持；四份 terminal记录共512KiB/4slots预留已包含在总帽。pending/create-only、root/祖先书挡和最终会计继续保留，设计输出 root本轮不创建。

完整 wall/RAM/storage、实际 graph与 packet尺寸、真实profile和outer成本、失败 partial reads/cleanup/retirement、发布末尾和最大合法编码仍未知。模型以 null 表示，不以零替代。现有23项普通 Parent测试、此前各单模块/微型进程结果与本轮静态测试均不作为完整 F资源或运行准入。下一步优先完成上述版本化连接与合法复用，再提出具体有界实测包；完整 F 继续 OPEN。
