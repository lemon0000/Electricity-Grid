# C：successor 当前进程身份锚开发证据

2026-10-25，DRAFT_NONAUTHORITATIVE。起始HEAD `572d56a11394cd487f77a06ea9b3fe2d9e474871`，按[合同](../../../docs/plan/staged_deliverability_c_saved_fresh_successor_self_anchor_contract_v1.md)推进[五角色38节点协议](../staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/capability_edges_v3.json)。root唯一writer，独立只读PRE_SEAL；本轮固定角色专用上游切口并实现共用self-anchor primitive，未实现或声称完整role bootstrap。没有seal、official verdict/receipt或运行授权。

## 实现与观察边界

`open_saved_self_anchor()`无caller身份或factory注入参数，用GetCurrentProcessId/GetCurrentThreadId确定当前对象，OpenProcess(0x1000,False,pid)/OpenThread(0x0800,False,tid)保留真实query-limited HANDLE。核两creation FILETIME、thread→process归属、不可继承flag、kernel image path及系统原始command line。对象普通构造/序列化关闭；entry/raw要求同创建process/Python thread/native TID、commit相同、原native函数及签名不漂移、query helper的function/code/default/kwdefault/closure相同，再重查HANDLE和原观察。原command line不从sys.argv或sys.orig_argv重建，未声称它已等于未来role expected argv。raw≤128KiB。

close先核intrinsic ownership，query helper/native binding/观察漂移仅成为primary，不阻断自有资源清理。两个HANDLE逆序独立尝试；helper返回后由强持的原GetHandleInformation得到ERROR_INVALID_HANDLE(6)才清pending。no-op close保留两pending并进入unresolved。一个失败仍关闭另一个；primary与secondary均强持，不可序列化、无自动重试。状态或所有权自身损坏时停止，避免误关foreign handle。数值HANDLE关闭后若被并发复用也保守未决，不能据数值自动重关。测试仅显式释放自身主动阻断关闭且仍经独立API确认身份的HANDLE；poison对象仍维持未决状态。

该primitive提供当前进程/线程的local self观察，不证明角色启动、direct main、source/EXE文件pin、环境/时钟/context、外部observer持有OwnedChild/HANDLE/Job、full input/runtime或permit。局部helper绑定不认证构造之前的任意Python RAM，完整cold import/runtime仍OPEN。raw中role_bootstrap_verified/external_owner_verified/full_runtime_closure_verified/full_P1_content_verified/run_authority/F_launch_admitted及五gates恒false。

完整角色依赖已固定于合同：host/broker先于context，保留H0/request/arming/START/context/offer/ACK顺序；controller需要request/context/ACK/mailbox，parent需要controller permit/G0链摘要，fresh需要parent permit/parent hold链摘要且无issuer。expected argv由已持上游对象推导，三者原active/closed deadline分别start+155/165、+110/125、+80/90。本地self、外部retained owner和full-input/runtime是三个独立需求；ACK/permit不能写回create-only context。

## 当前源码和普通验证

| 项 | pin或结果 |
| --- | --- |
| epoch | `d217017c11d0b9c82e67b6300b0b413342da71f23816bf1a74c6d75889b3bbb4` |
| ENTRY | 298431B / `474ee2f89fceceb0c2120159c638ec2c49a3a8ece0b598bb535fce5c884a3e76` |
| tests | 198313B / `abbafff0a43ad501f309ed190eb304c71505abb73aeac6e887e28d170f172326` |
| scientific adapter | 17247B / `26b919e385f9d7042587db490dab694fc5bf1643665ab4bf94a1c9bac8087396`，未改 |
| 当前集合 | 34新self节点+184相关回归=218唯一nodeid，全部终态exit0 |

| 组 | 节点 | wrapper wall/cap (s) |
| --- | ---: | ---: |
| self_smoke_19 | 2 | 2.921/10 |
| self_rest_20 | 32 | 5.109/14 |
| data_smoke_07 | 3 | 3.969/12 |
| data_a_08 | 59 | 15.172/25 |
| data_b_09 | 59 | 15.438/25 |
| source_expectation_10 | 12 | 16.407/23 |
| expectation_a_11 | 17 | 27.765/32 |
| expectation_b_12 | 16 | 22.109/26 |
| binding_13 | 18 | 30.172/40 |

当前218 wrapper合计139.062s。包含此前失败/部分通过的所有pytest attempt合计151.686/240s；静态、collection和保存另60s，总300s、单次≤40s。collection14后tests全文件原字节未改；后两次修正仅ENTRY，admission21核相同tests字节后复用exact nodeids并固定新epoch。组帽207+此前已花12.624=219.624≤240，重验前仍有20.376s预算空间。完整静态终态由`checks_01/*.exit.json`按kind累加；oracle stdout只含调用前已终态记录，本次wall由wrapper退出后补记，不能把观察中值当终态。

新增34覆盖真实当前self与独立ctypes API交叉核验、原始OS command line不随sys.argv数据改变、同process/thread约束、普通构造/pickle/旧域拒绝、9项状态tamper、native函数/签名漂移、query旧观察重放、各观察字段替换拒绝、开第一/第二HANDLE失败、初/末查询失败、构造primary+cleanup双错、单HANDLE cleanup失败仍关闭另一个、no-op close未决且不重复close、raw cap、精确access/current IDs及actor/transport/FS/科学导入拒绝。API参数trace只包装并调用原OpenProcess/OpenThread，其余真实查询和HANDLE身份仍由独立API核；没有logical角色正例。成功及故障测试对所持真实HANDLE做明确最终无效核验，故障中的显式恢复不授予生产恢复语义。

## 修正、历史与保存

pre-seal发现的query replay与no-op close风险在开测前修正，原收集/准入证据保留；没有把旧27节点计划称作34通过。实际执行另保留三个失败：

- smoke05：kw canonical bytes被直接放入commit JSON，3.984s、exit1，在打开process/thread HANDLE前失败。改为pin(kw)。
- admission17：误读前序不存在的group_admission_03，0.094s、exit1；原helper/error/snapshot保留，新helper修正路径。
- rest06：22过1失败，5.718s、exit1；query helper漂移导致close在cleanup前退出、状态仍live。该失败attempt未证明其局部HANDLE关闭，不能计为清理成功；其pytest进程已终态。修正intrinsic/query检查顺序后，当前epoch完整重跑218。

旧smoke16的2过与rest06的22过共24部分通过仅属旧epoch，不计当前218。全部失败、早期计划、原helper和执行快照逐字保存；未覆盖或改称成功。保存oracle精确区分五source epochs、两个pytest失败和一个静态失败。

ENTRY仅追加191行、tests仅追加304行；原190/211顶层定义及scientific src16定义AST保持。SF49闭集及另外47文件逐字不变，3649前序路径与P1全部683文件保全，外锚仍`c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473`。原P1仍21点/5模拟小时，没有新增模拟小时。旧F的8MiB/64files/17targets、guard/outer不变；本普通证据另帽12MiB/192files。三导航只前插，完整旧body suffix保留。

pytest沿用固定NumPy/subprocess pin/stack/args的唯一lscpu阻断+OSError False fallback；每个pytest进程attempt1/blocked1，声明的其他process/native-owner/P1/actual写事件为0。整个窗口的OwnedChild构造guard在任何仓库import前安装并恢复；它不禁止本合同明确的当前self query HANDLE，也不证明任意native effects为零。生产probe政策仍UNDECIDED_BLOCKING。

[saved_checks.py](checks_01/saved_checks.py)独立stdlib oracle核分epoch终态/全attempt成本、执行source/helper原字节snapshot、current218精确union、旧24与三个失败、固定false flags、保全/导航/文档和已hash固定的前序oracle；不import当前ENTRY/validator/helpers，不用当前可变实现作为冻结真值。CLI严格要求当前源码/导航相同；未来archive调用verify()允许两mutable或导航前插变化，但源码漂移时只报告冻结218和当前0，另外47漂移仍失败。

下一步按合同接通role-specific upstream、direct main/argv/alias/path/env、source/EXE/context handle书挡、外部retained owner及原绝对deadline，再补full input/runtime与store/issuer/owner。生产NumPy probe策略、33根传递绑定、source6500/180s/失败/wire/host硬停止仍OPEN。实际F、fresh科学重放和最终父端采用均未执行；整包科学采用、资源、正式门禁保持false。恢复见[交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_successor_self_anchor.md)。
