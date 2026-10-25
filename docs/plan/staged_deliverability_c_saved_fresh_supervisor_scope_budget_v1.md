# C：saved supervisor、issuer 与实际角色执行的事前准入设计

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[owner补验交接](continuation_handoff_20261025_saved_fresh_owner_completion.md)，起始HEAD `e6871551f58c9872402d54e5da81d973f6c14abd`。本页是独立设计/只读算术诊断，不修改[原F科学scope与硬帽](staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)、SF49、canonical三源码、原guard/outer、P1或既有证据。实际saved F、solver、B/C/E科学重放和生产issuer均不执行。

## 本轮问题、预算与出口

当前同一源码epoch已有161个普通节点终态证据。下一实际链仍缺saved supervisor bootstrap、ACK-bound external owner、逐进程issuer、controller→parent watcher/reader、saved-specific角色driver和最终外部消费。普通driver和ordinary schema保持其边界；不能通过改一个mode或打开global issuer完成接通。

本轮只做三项：固定完整依赖DAG及每层权限；核嵌套调用/库存和时间费用；用独立标准库字节oracle验证协议容量设计。总检查预算90s，所有静态/保存检查实耗累计计入；单次baseline≤8s、oracle≤15s、保存复核≤15s，其余单次≤15s。失败/超时保留script snapshot、raw stdout/stderr和exit，不自动重试actor或增加科学范围。输出在 `results/tables/staged_rts24_saved_fresh_supervisor_budget_v1_non_authoritative/checks_01`，诊断输出帽8MiB/128文件；仅该明确non-authoritative目录可写。oracle不创建actual OUTPUT或其父目录、不构造F的Native owner/Job/StageChannel、不导入scientific adapter、不进行pytest或科学重放。外部捕获器仅启动这些标准库静态脚本。

诊断数据只写上述目录；本页、对应报告/交接及三导航前缀属于另行允许的文档交付，导航旧正文逐字保持。root唯一writer；按agent.md §7进行独立只读PRE_SEAL，复核只审设计和原始证据，不生成official verdict、receipt、seal、manifest、lease或运行授权。本轮完成须有现存源码定位、条件账本、协议raw/slot容量证明、旧字节/P1及导航原文检查；未实现/未测项目继续明确OPEN。

## 完整能力与数据依赖

| 节点 | 拟执行路径及持有者 | 必须保留的约束与当前缺口 |
|---|---|---|
| H0 | host independently capture selected49与完整caller image | 强持真实同进程HeldInput/原image；不能从broker offer反推expected。arming之前的费用仍计总调用账本；其停止/资源证据OPEN |
| H1 | host arm broker OwnedChild/Job，ready后START | 建立过程不生成context；ready/standby一次性，保留原identity与partial HANDLE；actual saved arming未实现 |
| B0 | broker在Job内make_context、create-only发布、offer | source/exe/env/P1/fixture与host期望一致，OUTPUT及receipt/root identities绑定；当前make_context内部还会capture |
| H2 | host纯RAM核完整offer，确认binding空值后ACK | ACK绑定request/caller/context/receipt/双方identity/nonce；busy不能证明不存在；ACK前不得构造controller |
| B1 | broker一次消耗ACK-bound controller permit并capture/release supervisor | 独立SavedSupervisorBootstrap/argv和owner seam；不能扩展SavedOwnerInputs的两条科学父子边 |
| C0 | supervisor完成bootstrap，G0，建立controller-local issuer | 仅一次controller→parent；绑定bootstrap对象/commit、PID/thread、request/ACK/context/tree/channel与earlier deadline |
| P0 | parent从原输入hold/replay并发布完整metrics | 只读原B/C/E，不得用parent结果推fresh预期；原科学禁用效果和src不变 |
| P1 | parent-local issuer只发一次parent→fresh permit | 复用原reservation start和single attempt-state；fresh永远没有issuer，失败不退款/重试 |
| Q | fresh独立hold/replay、metrics、terminal | 只写精确fresh-owned targets，不再spawn，不继承parent live evidence或缓存 |
| P2 | fresh完整quiet/close后读取、inner records、G1、比较、candidate、terminal | parent内容读取精确role_targets('fresh')；startup/process另验证。当前read_saved_after_quiet的prefix宽于该集合，接通前须收紧 |
| C1 | parent完整quiet/close后核两层owner/creator/identity子集与核心候选 | 独立saved record validator和controller reader；现ordinary validator/driver不能复用为saved权限 |
| C2 | G2→最终observation create-only/readback→G3→bounded controller return | 不做第三次科学重放；记录存在不自证发布后bookend；完整库存/原source/exe/caller仍必须核 |
| B2 | controller完整quiet/close后核return、写broker terminal并退出 | broker只传controller return的exact pin，不复制完整return；保留真实controller process record和progress前缀 |
| H3 | broker全Job quiet/close后分别读取两return、核绑定/资源/总截止 | host持真实owner，不由JSON替代。最终输入/输出读取、分配和发布的外部硬中断仍OPEN；不能从此前actor的停止能力推导host尾部已受控 |

现存复用基础：`_role_reconstruct/_role_compare/_role_input_bookend`中的只读科学操作、固定target发布、`_watch_owned_stage` kernel/RAM核心和single attempt-state。saved-specific实现须保持ordinary入口、descriptor、读权限和validator的拒绝域。bootstrap/issuer只在实际已ACK角色中建立，owner创建后清理依赖held issuer/permit，不回读可变global。生产发行端继续关闭。

## 条件调用账本：不能沿用旧基数直接准入

原E实测每侧4319次P1读 = B2152 + E801 + 两个完整库存2×683；这只是其冻结代码/输入的基数。新DAG成功路径若采用H0独立capture和B0当前make_context：

- top-level capture：host1、broker1；hold：G0/parent/fresh各1，hold内部再次capture，所以capture body总计5。
- replay2；每次成功replay末尾各一次完整inventory。
- 显式G1/G2/G3各一次完整bookend，共3；G0已经计入其hold的capture，不重复加一次。
- full inventory总数10；P1读条件合计 `2×(2152+801)+10×683=12736`，比原12500帽多236。
- 若H3对host初始HeldInput再完整P1书挡，则11次inventory、13419次P1读，超帽919。

这两个数是拟接通路径的条件算术，不是实际F读数，也不是所有失败路径上界。`replay()`异常处理会再full bookend；晚期末次bookend失败可发生第二次inventory尝试。按actor/horizon列parent early、fresh late和double-bookend失败前缀，计入已完成与已尝试读取，不能退款或把unknown写成零。

原source核心B/E条件基数每侧1912+78。每次capture调用sources两次、每次成功replay调用两次、G1/G2/G3各一次，故adapter.sources为17次；每次49读并至少复读已loaded的adapter自身1次。若按当前通用helper展开33个完整check_context，则单该组合的条件下界为 `3980+17×50+33×51=6513`，尚未加其他loaded src、catalog、fixture、额外EXE/anchor和新supervisor书挡，已超过6500。33只属于本页“保留当前完整helper调用”的实现模型，接通后的实际调用尚待计数，不能作为运行实测或对所有未来实现的最小值。最初oracle把_role_compare的parse误记成_role_context，AST edge断言拒绝该35次模型；原失败snapshot/raw保留，当前按33次计算。

下一代码分支应先证明operation内重复验证的依赖闭包和失效窗口，消除重复capture/context解析/完整source读取，或重新提交独立successor范围审查；不能放宽12500/6500、删G0–G3、跨进程缓存P1或减少B/C/E原审计来获得准入。原compile84/import42/snapshot42、typed pack≤320和政策/审计边界保持。优化前后必须用同输入、完整metrics/refs/state/typed SHA及全部失败书挡验证等价；当前整体call ledger仍未闭合。

## 嵌套时间：更早的绝对截止优先

当前名义串行向量至少为共享F0=10 + parent stage125 + controller final_check/publish30 + controller自身quiet/terminal10 + broker自身quiet/terminal10 =185s，尚未包含broker return的正费用。parent125已含其自身5+10，不能替controller/broker再次付费。该算术不证明实际wall超时，证明各帽同时兑现与180s成功不相容。

原阶段cap保持为局部fail-stop上限；任何层都同时受earlier absolute deadline截断。拟定正预留R_b=2s（broker在controller close后的校验/写槽/terminal）和R_h=3s（host末尾），仅用于下一开发合同，不是实测保证：D=t0+180；broker完整close≤D−3；broker active≤D−13；controller完整close≤D−15；controller active≤D−25；parent完整close≤D−55，即t0+125；parent自身5+10后active≤t0+110。再为fresh close后的inner records预留5、parent_compare预留15，则fresh完整close≤t0+90、fresh active≤t0+80。若parent在t0+10开始且parent phase用满45，fresh到t0+55才开始，其可用总时长仅35s。所有phase取满时预期fail-stop，不能宣称同时具有原全部余量。逐边deadline须进入issuer/permit/binding的immutable commit，不能仍只带context的180s。

fresh的原reservation→returned总窗口仍是50s，必须包含其后parent发布inner records；不能在fresh watcher用完50s后再授一个新的5s。下一实现须绑定同一个episode deadline，watcher close截止还须取min(上述全局fresh close、episode deadline减尚需发布预留)，或证明monitor和caller共用原terminal5s。当前saved watcher返回之后的caller发布尚未受该episode约束，此项仍OPEN。deadline_v2继续列出fresh截止；旧未列到fresh的ledger原样保留为审阅前记录。

R_h中的host末次读取/分配/编码若没有受控owner，deadline公式不能产生硬中断能力。arming/kernel调用、host final I/O和瞬时资源上界继续OPEN；真实F启动受此阻断。不能仅增加一个计时器、线程timeout或“检查时未超时”的bool来关闭它。

## Saved wire容量合同：value、packet raw、physical slot分开

ordinary `INVOCATION_SLOTS`不修改。原两个return的physical=131072+44只容纳最多131072 packet raw，payload外还有binding envelope；broker还包装status/progress/value。仅知道process record≤131072不能推出它加上任何metadata和controller return仍能放入同帽。新saved协议先固定如下proposal，启动前必须实现并验证全部前置value/extra/wire guards：

| saved slot | max value bytes | max packet raw bytes | physical bytes |
|---|---:|---:|---:|
| header | 4096 | 4096 | 4140 |
| request | 32768 | 36864 | 36908 |
| ready/start/ACK/constructor_probe（各） | 3072 | 4096 | 4140 |
| context offer | 2097152+8192 | 2097152+16384 | 2113580 |
| controller binding | 32768 | 36864 | 36908 |
| controller return | 32768 | 36864 | 36908 |
| broker return | 131072+8192 | 147456 | 147500 |

request只传host已持caller/source/input pins、exact source/exe/env及scope/budget摘要，不把完整caller image放进32KiB。broker仍从原输入独立构建完整context；host必须与自己的HeldInput.image逐字比较context.caller_core后ACK。context raw≤2MiB，offer除context之外的canonical extra≤8192，外envelope≤8192；不能因当前560KiB左右的logical fixture能装入就宣称最大2MiB已证明。

controller return固定小schema：bootstrap proof≤16KiB、最终observation/pins、G0/G2/G3、固定16-target inventory、总绑定及local结论，不含metrics/record正文或整个source/caller map；整体value≤32KiB。broker success value保留完整controller process record≤128KiB，但只引用controller-return pin，其他字段extra≤8192。host在broker quiet后直接核独立controller-return slot及其exact pin，不靠broker重复复制。broker packet envelope+status/progress wrapper合计extra≤8192；progress仍须真实连续ready/context/binding三前缀与逐slot pins。

failure不沿用嵌套原始异常树作为wire保证。拟定compact error仅复制首次bounded image的type≤64和message≤256个code point，单项canonical≤4096；cleanup≤4项，layer为固定ASCII≤32；primary+cleanup和固定phase/refs等总value≤32768。同一observer进程的constructor/monitor/cleanup原异常及partial HANDLE可以由其非序列化capability强持；child application原Python异常不会跨进程保留，上层至多持有bounded diagnostic、stage error code和process record。不能把broker/child退出后的wire摘要称为host所持原异常对象。unknown不补success record；不能将大record截断后称已完整保存。所有successful四persisted records仍各128KiB，external mailbox额度不扩展17 targets/8MiB/64files或5,537,792B reservations。

容量与失败可交付性分别验收。ready之前失败无合法broker terminal前缀；ACK后binding前失败只持真实partial owner，不能合成controller record；已提交broker terminal后不能再改写为failure packet。各窗的observer、原错进程、wire/filesystem条件分别登记在failure_availability_v2.json，所有diagnostic guaranteed字段均false。transport闭集为none、invocation_mailbox_terminal和stage_channel_error_frame；inner角色依赖writer/relay、下一frame slot及channel状态，不套用broker prefix/terminal规则。application窗同时覆盖controller G0/G2/G3、parent/fresh replay、inner记录、compare/candidate、最终observation发布/readback；publication unresolved保留may_have_published，缺return不推断文件不存在。原failure15s只消费当前remaining earlier deadline，不追加15秒；余额不足或mutex/目录/receipt未决时只保存已观察事实和本进程能力，不能承诺failure target必达。旧v1矩阵作为审阅前记录保留。

本轮oracle只证明上述component cap合成的字节不等式、Unicode escape计数、原slot的cap组合反例，以及条件call/time算术。BMP逐一穷举65536个code point（含DEL与lone surrogate），astral只独立核四个边界/代表值；最坏12 bytes/code point是统一surrogate-pair编码分支的上界假设，不称全部astral穷举。不证明将来driver已正确执行这些guards、实际record最大值、OS分配/RSS或完整失败路径成本。controller-return字段级最大编码、constructor/startup/返回schema及真角色连接仍须下一实现和独立复核。

## 开发顺序与停止点

先完成call ledger/重复验证优化的可证依赖和saved wire schemas/field bounds；再独立实现SavedSupervisorBootstrap、ACK-bound controller owner和逐进程issuer；随后接saved-specific parent/fresh/controller driver及精确quiet reader/record validators；最后执行预登记普通故障矩阵与whole-path计数。每个源码epoch保存独立snapshot，不继承161为新源码通过。whole-runtime、最大合法四record/return、昂贵失败、external硬停止与资源证据均闭合后，才讨论那一次真实P1 F验证的专项授权。

本页所有F局部verified、F_launch_admitted、整包scientific_evidence_adopted、resource_admission、formal_result维持false。没有新模拟小时、native或formal结果；完整319/139/F-X、C整体、D/E现实输入、原65s余量及留出义务仍OPEN。
