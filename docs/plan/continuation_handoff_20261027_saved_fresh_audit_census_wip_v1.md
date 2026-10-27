# C/F：audit census草稿登记拒绝，四项PRE_SEAL finding待修

2026-10-27，DRAFT_NONAUTHORITATIVE。接续[RCI交接](continuation_handoff_20261027_saved_fresh_runtime_cache_import_v1.md)，实现合同为[audit census范围](staged_deliverability_c_saved_fresh_audit_census_scope_v1.md)。root唯一writer，子代理只读；无official verdict/receipt/seal/run authority，宽goal仍active。当前没有census实测，不得把草稿或计划写成测量结果。

## 当前代码与执行事实

新增BS census1、core15/probe12/parent12、14节点unit文件及controller/checkpoint草稿。拟在实际import前启用固定64个guard-passed open前缀，保留原_audit body和_audit_entry检查顺序，按identity/runtime link/cache/globals/ownership/image/machinery聚合；没有源码数据参数输出。clock、IO、native primitives及census依赖函数默认强持，统计不进入authority commit；新stop类直接继承BaseException。以上只是实现意图，尚无unit或cold通过证据。

唯一已执行路径为register。它保存helper_snapshots、transport和command_size之后，在command≤30000 UTF16处拒绝：**实际30049/30000**，transport29731B，pin为dcab3d6b574c64f24d48692d9aa9459c27c6dee2a0be8bebcfc78803a18c703b。static charge**1.6851643999980297s**。没有registration.json，没有unit/cold/adapter执行；不得接续旧driver的unit或冷路由。

原6个登记工件及全部snapshot中的6份源码冻结，不能原地改版本或重跑。随后仅运行create-only `rejection_snapshot.py`，核原transport/helper raw、RCI root map和Source49，charge**0.02226570000493666/1s**。它不修复失败，也不是PRE_SEAL通过。AOC root现有**8文件/327820B**；未执行checkpoint脚本及scope由本次Git提交保留，不在该rejection snapshot/helper snapshot的绑定集合内。

## 必须在独立后继修复

独立只读review列出四项未闭合finding：

1. `_census_open_begin`应在任何计数/状态更新前，用默认强持的getpid/get_ident核same creator；目前foreign open会先entered，再由原guard拒绝。补foreign/reentrant不计入前缀的反例。
2. `_census_start`应拒绝installed预置非0，证明本次sentinel严格0→1；目前预置1可以跳过真实状态迁移。补preseed与state替换反例。
3. import primary加观测故障时，`_finish`可能已抛同一个primary；finally不得把该primary加入cleanup再构造包含自身的cause group。应保留已有cause、恢复原pending异常，测试primary identity与group不含primary。
4. parent帧schema需锁定完整schedule与状态关系：begin只能seq1/count0/active；progress仅1/8/16/24/32/40/48/56且entered=passed、rejected0、observed=passed−1；prefix64严格终态；return/error末帧inactive且非inflight；bucket count/sum/max逐帧单调。补重复begin、伪progress、伪terminal与倒退反例。

另需扩充AST oracle到class非method节点和import白名单；现有14个测试只是未执行草稿，不能借其名称声称覆盖已完成。四finding不可在本冻结v1上修复。

## 保存与累计账

root `results/tables/staged_rts24_saved_fresh_aoc_v1_non_authoritative`：读registration_failure、command_size、transport.snapshot、helper_snapshots及rejection_snapshot.py/json。后者root_map覆盖生成前7个文件，含自身源码。静态scope已用**1.7074301000029664/20s**，unit**0/8s**；总帽28s不构成重试授权，后续不得沿失败路由继续运行。

全历史static**219.6256489000109**、pytest**366.48897970000326**、unittest**54.345750399999815**，总**640.460379000014s**，意外不接受**23条**。原所有失败、旧120/540/import8MiB超帽保留；新帽不重置前驱账。编辑/审查/Git、Python初始启动和最终JSON写入不计capture，不是完整wall，无模拟小时推进。

Source49 epoch **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**及49个原字节不变。39项并行文稿/图件/文献dirty保留，发布只含本scope及四导航新增段。

## 恢复入口

先核Git/process和本交接、AOC rejection_snapshot/原raw，再读四finding。下一独立successor应先修上述语义/测试问题，同时做有限static command admission，不能盲加帽或直接启动unit。可复用parent v5已有token间prefix空白压缩算法；若采用，须重新用实际minified prefix作zdict，保持payload逐字节、含位置AST/CodeType，明确prefix列位置变化并核token/AST语义、实际argv与bootstrap code自检。当前没有该方案对本census payload的实测尺寸，不能写成已达帽。

完成新登记、unit与只读PRE_SEAL后，才可按新的有限scope取证。固定前缀仍只代表guard已放行审计尝试，第64物理open被诊断停止，不是64次I/O完成；超时尾段未知，不能补算。outside-guard残差不等于I/O时间。完整B_S profile/OBSERVED/LIVE、实际producer和F仍须后续独立证据。

E/U、独立TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false，cache_candidate_adopted=false保持。
