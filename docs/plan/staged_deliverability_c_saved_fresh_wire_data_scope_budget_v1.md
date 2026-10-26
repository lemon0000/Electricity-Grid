# C：wire 数据校验与 startup join 实施范围预算

2026-10-26，DRAFT_NONAUTHORITATIVE，起始HEAD/origin `cdcc931c9fee0939ec004e2f6de4aa380f663f80`。接续[45域合同交接](continuation_handoff_20261026_saved_fresh_wire_contract.md)，root唯一writer，既有独立只读PRE_SEAL。采用已读karpathy-guidelines；本轮是data contract/普通跨模块验证，不改变科学模型、旧冻结结果或运行权限。

## 实现出口

仅向原ENTRY末尾、旧CLI guard之前追加实现，并向原测试文件追加有意义的行为测试。旧函数/类AST、CLI、科学adapter、Source49名称集合及其他47个Source路径保持。保全4290前序路径、wire root41与其两份外部新文档，合计4333路径；原45域/94节点/50+3与两个设计epoch保持原字节。

实现固定pin的45域shape/type/canonical校验，44B physical framing/zero-tail/digest/marker codec，mailbox kind/sequence/predecessor和原start/deadline链，entry四slot完整prefix，projection bundle→原packet SHA逐项校验，三种固定角色wire-data结果，以及三种固定startup-join结果。stage独立header+16帧，bootstrap index0、原descriptor逐phase与吸收terminal/error，成功总帧12/7/3；早期error不产生bootstrap。包含五类failure的索引/遗漏/quiet声明/出版不确定性及JSONL预留，具名return reference/status矩阵、controller binding和constructor diagnostic。生产CLI、issuer/permit/owner/Job保持关闭。

普通RAM fixture须连通独立context/request→header/READY/START/offer/ACK→controller entry/header/capture/self proof→parent entry/header/capture/self proof→fresh entry/header/capture/self proof，并覆盖返回/失败。fixture用独立stdlib构造字节，不调用被测validator/codec生成预期。单节点计数不能代替这条连通性证据。

新增不可变data结果只强持原bytes、原context/contract对象、原upstream结果、其id/commit和创建进程/线程；clone、换context/同字节换upstream、跨thread和pickle均拒绝。每次operation以visited DAG只去重节点本征复核；每条入边仍逐次核role/field/type、object identity/commit/creator、同一context及SHA。gray检测环，完整成功后才标done，不跨operation缓存。四份本地caller-basis声明（handshake及三role）另有closed keys，固定本地对象引用、独立name/nonce、episode、receipt/tree及projection pin；这些不是45个wire schema，不进transport，不认证任何producer。原21 development声明/三data-only API不扩域或自动转换。

父端私有capture与child self proof分别输入join；独立declared owner/self身份参与相等关系，不从双方自报值互推预期。现context数据类型没有创建者字段，本轮不证明其原creator。registry/template/DAG及原10域/模板的expected pin编译固定于ENTRY；caller只能提供待核raw，不能同时决定expected truth，basis没有改写schema/cap/hash-domain/status的权限。合同registry中历史Source49 map仅为设计来源，不能当作当前Source期望；新context使用本轮真实Source bytes。所有clock参数均为caller声明，不读取时钟。

所有结果保持data_only；actual kernel/FS/source/runtime/clock、独立producer认证、真实quiet、bootstrap/issuer/permit/owner、读取权限、完整P1/科学hold、actual fresh/最终父端采用、run/science/resource/formal flags全部false。接口允许核对声明中的quiet/full-content等字段，但声明不能成为能力。failure原异常/partial owner的真实强持、实际commit-last/并发/abandoned mutex/硬停止及真实读取门禁仍待独立producer/owner实现，原36项runtime fault矩阵不改成通过。

## 检查、分组与预算

普通总预算≤540s：全部pytest尝试≤420s、静态/collection/admission/保存≤120s，单组≤45s。先baseline保全与raw snapshot，再锁collection、Source epoch、互斥nodeids和caps。先新smoke和其余新增测试/独立审查，Source稳定后再跑全部前序480节点，不把旧epoch通过继承为当前执行。

预算依据是前序480成功charge约224.523s（旧失败另保留）；重排降低重复冷导入：旧role-data198重分三组，各cap37；其余前序282沿原互斥七组合计cap178（legacy18、binding36、data_a22、data_b22、expectation_a32、expectation_b26、source22）。旧合计cap289。新smoke≤18、其余新节点三组各≤23，总新cap87，计划合计376，pytest余44只用于已定位失败的预登记重核；实际Source变动则重审affected/current覆盖，不用部分dot继承成功。

静态预登记baseline≤15、collection≤20、admission≤15、saved/terminal各≤30，帽合计110，余10只作已定位短诊断/失败余量。每次pre/post核Source49、4333历史路径和实际helper，按执行bytes保存snapshot、stdout/stderr/exit及所有失败；initial wrapper解析失败亦需外部原记录和实际费用，不丢弃。capture含自身准备/目标/前后pins并另列0.5s未实测tail reserve；Python启动、编辑/review/Git另列，不称完整workflow wall或硬停止已证明。stdout≤262144B/stderr≤32768B、4096B读块，超流/timeout kill/wait direct child，记录reader/pipes/cleanup终态。

ordinary harness沿既定精确NumPy lscpu拒绝fallback及OwnedChild/P1/实际F写guard，repo import之前安装，单次明确attempt1/blocked1；不作为生产NumPy政策。现有其他native/Job历史测试不纳入新scope，未知新增测试不得被filter丢弃。任何超cap或pin漂移先停dependent actions并保存，不延长540/420/120。

## 保存和继续

新root `results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative`：checks_01≤180files/14MiB、final_package_01≤24files/2MiB，合计≤204files/16MiB；三新文档≤1MiB，外部checkpoint≤64KiB。源快照可重用前序exact content-addressed snapshot，修改的ENTRY/tests及每helper执行版本另保存原bytes。main freeze在最后测试的外部exit和文档索引之后建立，saved/terminal只写独立package；oracle不import当前ENTRY/测试helper，仅核原records/snapshot及pin绑定前序stdlib archive，Source变化时旧480只作为frozen历史。

四导航保留原header+双LF+本轮prefix+完整旧body。独立只读PRE_SEAL、targeted/相关回归、hash/diff/link/process核验后按已有授权精确commit/push并核远端/空porcelain。宽goal保持active；下一步才是实际producer、retained owner/Job及bootstrap能力连接。33根runtime闭包/NumPy政策、source6500/180s、整链资源/停止及具体actual F运行授权仍OPEN。
