# C：successor 冷入口与父端独立比较开发证据

2026-10-25，DRAFT_NONAUTHORITATIVE。起始HEAD `ea2cd5e1629486158be6cfa6b8372bd43641a44a`，按[执行合同](../../../docs/plan/staged_deliverability_c_saved_fresh_successor_direct_entry_contract_v1.md)和[机械包装合同](../../../docs/plan/staged_deliverability_c_saved_fresh_successor_direct_entry_package_contract_v1.md)推进真实bootstrap所需cold-entry mechanics。root唯一writer、独立只读PRE_SEAL。本轮ordinary direct child与独立parent均实际运行；没有actual F、science、Job/OwnedChild或角色能力发行。

## 两侧结构和真实观察

child没有expected packet，也不从incoming argv重建expected。`SavedDirectEntryObservation`只采集真实direct `__main__`/spec、canonical alias、初始与ROOT-first sys.path、flags/cwd、Python可见os.environ完整映射、argv/orig_argv、SF49/EXE实际bytes/identity、self PID/TID/两creation/image/raw OS command line。active module frame code与磁盘ENTRY编译对象相等，仅证明该module code，不扩大为global/runtime闭包。

source49使用原闭集、前置metadata与最终实际pin.bytes合计≤2MiB，单文件≤8MiB；文件均ordinary/reparse/single-link约束，EXE允许既有hardlinks。lstat/open/fstat/bounded read/fstat/lstat与parent链书挡，文件HANDLE即时关闭，准确称read/identity bookend。真正保留的是self两个query handles及parent Popen process HANDLE。Python可见环境强制白名单和六固定值、拒绝注入键，不声称隐藏OS环境block已认证。观察对象普通构造/pickle关闭，强持main/self-anchor/路径/字节和dependency身份。

parent的expected raw、完整argv、env、cwd、源/EXE独立image在Popen前冻结；reader独立stdlib，不import ENTRY/canonical/source helper。Popen后独立GetProcessId/GetProcessTimes/QueryFullProcessImageNameW核process HANDLE的PID/creation/kernel image。exit后才比较child actual record与held expected，随后Close并用GetHandleInformation核ERROR_INVALID_HANDLE(6)。raw commandline是child self观察，与parent-held完整argv按固定Windows quoting比较，不声称parent外部读取了command line。

normal record全canonical/duplicate/closed字段、精确类型及all-false校验。六RAM fault另固定各自primary type/message、精确secondary layer顺序和final-bookend error image相等；不能用统一的无关错误冒充所有拒绝。错误像限制depth、24总节点、每层8子项及type/message长度，保留primary/final_bookend/alias_restore/path_restore/restore_witness/self_anchor_close层；这些是序列化数据，不是原异常对象identity。

close使用与完整binding分开的原资源/creator/路径ownership tuple和独立一次cleanup state。commit漂移成为final-bookend错误，最低ownership可信时仍restore自身alias/path并关闭原self-anchor；foreign alias/path不覆盖，最低ownership也不可信则强持未决。未决不可序列化、不自动重复cleanup或发行cap。

## 八个真实cold probes

| case | parent target wall (s) | 真实终态 |
| --- | ---: | --- |
| normal | 0.844 | child exit0；held expected、PID/creation/image、source/env/paths/flags/code/OS line比较通过 |
| argv | 0.516 | child exit1；control drift，final_bookend |
| alias | 0.500 | child exit1；control drift，alias_restore与restore_witness完整 |
| path | 0.516 | child exit1；control drift，path_restore与restore_witness完整 |
| environment | 0.516 | child exit1；Python-visible environment错误及final_bookend |
| helper | 0.500 | child exit1；dependency changed及final_bookend |
| commit | 0.500 | child exit1；immutable错误，仍清自身资源 |
| oversize | 0.375 | stdout_limit，真实kill/terminal wait/reader threads/pipes/process HANDLE清理 |

合计4.267/24s。每个parent自身exit0、cleanup为空、真实process HANDLE关闭；normal与六RAM case child self handles也确认closed。八份started记录是Popen后的identity数据，不是terminal。每case预期/stdout/stderr/result及外层execution记录均保留。

parent使用两个固定容量缓冲stdout131073B/stderr4096B、4096B读块；超过stdout或任意stderr立即kill，不用无界communicate。oversize child固定输出147456B后等待，真实在131073B捕获帽处停止，kill_requested=true、child terminal、reader threads/pipes/parent HANDLE关闭。buffer容量不等于host RSS或Job资源准入。timeout逻辑只有FakeProcess检查，真实OS timeout窗口仍OPEN。

child audit从ordinary dispatch至cleanup覆盖声明的Python process/P1/actual access/file write事件，八case计数均0；Python启动/site与任意native副作用未被宣称全覆盖。parent audit精确允许每case一次Popen，其余process/P1计数0。标准库Popen HANDLE不是retained OwnedChild/Job witness，Job_quiet_proved恒false。ordinary child不读取P1/actual OUTPUT、不创建Job/目录/共享映射、不import science。对象/stdout/比较结果永久ordinary，所有role/run/F/science/resource/formal flags false。

## 当前源码和普通回归

| 项 | pin或结果 |
| --- | --- |
| epoch | `00ef897eb83d55f79491804cc49ee5302d766dd533ee3d8615ffff84b6a1e83a` |
| ENTRY | 315525B / `a54b532b20066c620231864a502e09adab58b7b9c881fb6346dd16260f804147` |
| tests | 210285B / `150da50a700d9a68ef2e2816310b34d083e8b4da34736412b537118f7a9eea13` |
| scientific adapter | 17247B / `26b919e385f9d7042587db490dab694fc5bf1643665ab4bf94a1c9bac8087396`，未改 |
| 当前唯一nodeid | 64新增+218相关回归=282，全部终态exit0 |

| 当前组 | 节点 | target wall/cap (s) |
| --- | ---: | ---: |
| direct_compare_09 | 64 | 7.625/12 |
| self_smoke_06 | 2 | 2.891/8 |
| self_rest_07 | 32 | 5.063/10 |
| data_smoke_08 | 3 | 3.938/11 |
| data_a_09 | 59 | 15.094/25 |
| data_b_10 | 59 | 15.297/25 |
| source_expectation_11 | 12 | 16.875/23 |
| expectation_a_12 | 17 | 29.375/32 |
| expectation_b_13 | 16 | 22.625/26 |
| binding_14 | 18 | 30.187/40 |

当前282 target wall合计148.970s。此前59 comparator/runner普通节点7.344s属于另一source epoch，原样保存，不计当前282。全部pytest target wall156.314/240s，当前组帽212+先前7.344=219.344，在重新准入前仍留20.656s。64新增覆盖imported-main/普通构造拒绝、独立parent comparator正例和字段/类型/unknown/canonical反例、严格分层failure及错case拒绝、fixed-buffer oversize/timeout逻辑；纯fixture均明确为synthetic comparator/控制流，不与实际8cold probes混为角色证据。

pre-seal阶段修复了pipe事后长度检查、failure宽松解析/层次压扁、parent读文件安全及image查询、ownership与commit分层、case-specific错误和Source实际合计书挡。初版collection/proposal和已通过59节点均保留；本轮没有未预期execution失败或超时被覆盖，六child exit1与oversize kill均为预登记反例的正确终态。

## 计时、冻结和包装

执行目录static/probe target wall20.003s，含8cold probes4.267s。审阅确认旧capture wrapper没有计其自身source/helper前后hash，因此这些数是target subprocess slice，不能声明整个workflow或交互wall≤320s。原记录不改，whole_workflow_wall_budget_verified=false。机械wrapper从pre-inventory起计至post checks，另列0.5s尾部reserve，仍共享原80 static/240 pytest/320总账；reserve不是实测或严格OS上界。机械本次stdout只含前次已终态账，本次wall由外部exit补记。完整workflow wall/RSS/storage/失败成本仍须后续审查，资源门禁保持false。

`checks_01`全部执行终态为220files/4,847,222B，≤原224/16MiB，此后冻结只读。独立`final_package_01`≤32files/2MiB仅机械索引/oracle/helper快照/三次原记录，组合≤256/18MiB，不能把新增目录称仍在原224帽内。旧epoch、stdout/stderr、started/result不移动、不压缩、不改写。execution inventory先固定exact names/count/bytes/root；support清单由finalizer stdout/exit及saved/terminal snapshot同pin锚定，support exact10项。saved snapshot再pin finalizer四原记录，terminal再pin两轮八原记录；terminal自身四份由最终Git逐blob/远端hash承接。

[保存oracle](final_package_01/saved_checks.py)纯stdlib，先核execution exact inventory/root，再核4epoch/282精确union、8probes、3815历史paths/P1全683和文档/导航，最后调用已hash固定且不import当前ENTRY的隔离旧oracle。它不import当前ENTRY/current helper，也不拿可变实现执行作冻结真值。CLI严格current source/nav；未来archive源码漂移只留冻结282和current0，其他47漂移直接失败。

ENTRY只追加273行、tests174行；原200/229函数/类和scientific src16定义AST保持。SF49集合、其他47、原F8MiB/64files/17targets、guard/outer保持；3815历史路径与外锚`c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473`不变。P1仍21点/5模拟小时，无新模拟小时。pytest沿用固定NumPy/subprocess pin/stack/args的唯一lscpu阻断+False fallback，Native owner guard保持；测试import策略不变更生产probe政策。

下一步连接角色专属request/context/ACK/mailbox/permit和原reservation，再接context文件书挡、外部retained OwnedChild/Job及原绝对deadline，之后才是full input/runtime/store/issuer/owner。生产NumPy政策、33根传递binding、source6500/180s、whole-workflow成本及host硬停止仍OPEN。实际fresh与最终父采用、整包科学采用、资源和正式门禁未开放。[恢复交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_successor_direct_entry.md)。
