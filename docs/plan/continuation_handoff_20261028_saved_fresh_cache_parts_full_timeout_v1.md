# Cache词法优化已验证，完整导入仍未返回

2026-10-28，DRAFT_NONAUTHORITATIVE。起点`d725b1c6b2ca2a81fa15c3b263157d0e55bfcf97`，承接[256前缀交接](continuation_handoff_20261028_saved_fresh_prefix256_v1.md)。本轮[原范围](staged_deliverability_c_saved_fresh_cache_parts_full_scope_v1.md)及[独立后继范围](staged_deliverability_c_saved_fresh_cache_parts_full_scope_v2.md)均保留。root唯一writer，既有reviewer只读PRE_SEAL，终态must_fix_open为空；没有official verdict、production seal或运行授权。宽goal仍active，完整F未完成。

## 本轮真实结果

独立helper `bootstrap_import_cache_parts_full_v1.py`从full v1派生，**仅改变_check_cache的body**。每event重读cache、predecessor identity、key/type/isabs、finder kind和finder.path检查保留；同一调用内使用规范化Windows Path.parts前缀比较，减少反复构造ancestor。其余完整AST、全部header、full-return wrapper、identity/defaults/ownership/image pin/source checks不变，没有跨event状态或文件系统解析。等价结论以当前未变异的Windows Path/parts行为为条件；source/runtime pin不等于live descriptor或独立TCB认证。

ful_v3的size、registration、10/10 unit、PRE_SEAL、startup/profile均通过。128个词法case、predecessor/finder变异、第一失败顺序、同一OSError primary identity、无跨event状态和helper metadata变异拒绝均验证。原full的五项方法/报告测试继承，首项改为cache-only AST/proof；实际10个node与静态发现一致。command **29997/30000 UTF16**，原payload字节变换、位置AST及CodeType等价通过。

方法benchmark固定11个predecessor+37个new项，共48项；3轮AB/BA/AB，每arm每轮32次，共192个benchmark调用。旧方法总 **0.09061500000098022s**，新方法 **0.018003800003498327s**；total new/old **0.19868454453791948**，median new/old **0.19736607168374398**，均达到预定≤0.90门槛。方法fixture耗时约降低80.13%；顺序略不平衡，结论只限该fixture，不能解释完整import超时或证明实际整链收益。`cache_metrics.json`保留三轮原值、顺序、keys、Source SHA和全部false gates。

**唯一真实完整import仍失败。** 外层full_import charge **7.526859199999308/8s**；父端case charge **6.584699899998668/cap7.060286899999483s**。本轮直接保存`drain_reason=timeout`、killed=true、child exit1。receipt原primary仍为`AssertionError:`，不把它改写为child TimeoutError。

stdout为空，stderr完整787B，无截断；15对graph之后只有`loader_ready`和`before_adapter_import`。没有adapter返回、后续stage、child report、import profile或OBSERVED证据。最后观测到的是调用前marker；不能断言importer未进入，也不能推算其确切运行时长。child self-close、runtime/boundary/resource最终phase、M/D/NumPy状态和child primary/secondary均**unknown**。

父端HANDLE、stdin、pipes、writer/readers均终态，cleanup、reader/writer errors为空。direct child peak working set **115752960B = 110.390625MiB**、error=None，只是本次被终止child的观测；不能据其大于旧run推断导入进度，也不形成整链RAM上限或资源准入。15对graph计时合计 **0.6321325000026263s**，首graph到before_adapter_import差 **1.0574204000004102s**；这不等于冷启动总wall或import耗时。

## 失败、后继与不可变字节

ful_v2的首次size在parent迁移清单拒绝：helper路径在同一manifest行中用于path与pin读取，共2处，原计数误写1。size_failure charge **0.4336923000009847s**、rejection checkpoint **0.42837929999950575s**，合 **0.8620716000004904s**；没有unit/cold。原root四文件、原代码/测试/文档全部冻结，未回写失败计数或覆盖后重跑。

8份当时输入的raw/pin保存在独立`results/tables/staged_rts24_saved_fresh_ful_v2_inputs_non_authoritative/inputs_snapshot.json`，329739B，SHA **fde9883c5ad68336aa868d2c4aaf1eaa7e55b517ba799b774e740e5508b13f1d**。它在失败后、后继编辑前生成，明确`prerun_input_binding_established=false`；不能据此补称v2具有prerun输入绑定。原v2 checkpoint的`executed_input_bytes_verified=false`继续保持。

ful_v3复用同一helper，不改优化算法；core26/probe23由core23/probe20只机械迁移root 2/1处，v2 child envelope与runtime_preclose保留。parent23以parent20为基线，四个路径变换及drain_reason三处元数据变换均精确计数，helper path+pin允许2处、其余1处，末端完整raw/AST相等。test successor v1→v2也只允许OUT/probe/core/parent四处唯一路径变换，末端完整raw/AST相等。size保存migration，register重新计算比较，基线raw先由失败snapshot固定，不能以当前自选pin替代原允许变换。

## 预算、存储与恢复入口

ful_v3 root：`results/tables/staged_rts24_saved_fresh_ful_v3_non_authoritative`，**24文件/912842B**。ful_v2失败root四文件37331B，加snapshot一文件329739B，archive共 **5文件/367070B**。包合计 **29文件/1279912B**，上限35文件/4MiB；writer每次预留从4MiB中先扣archive，旧失败未被删除以释放额度。checkpoint写后不向旧root追加或改写。

| ful_v3阶段 | charge秒 | 结果 |
|---|---:|---|
| size | 1.0102244000008795 | accepted，帽1.5 |
| register | 1.1612983000013628 | accepted，帽1.5 |
| 10项unit及方法benchmark | 2.703774399997201 | accepted，帽6 |
| PRE_SEAL | 1.4998723000026075 | accepted，非official |
| startup | 1.9169844999996712 | accepted |
| profile | 1.2234680999972625 | accepted，writer/admission统一131072B |
| full import | 7.526859199999308 | not accepted，帽8 |
| rejection checkpoint | 0.8991886000003433 | accepted，仅metadata |

ful_v3 static **15.237895400001435/21s**、unit **2.703774399997201/6s**，总 **17.941669799998635/27s**。加ful_v2失败0.8620716000004904，包实际 **18.803741399999126/28s**。后继size/register各1.5使最坏21+6+原失败0.8620716≤28；完整import帽始终8s，没有退款或重置预算。实际1个unit child+2个串行cold child，均已终态。

累计static **297.2437945000304**、pytest **366.48897970000326**、unittest **76.99093709999943**，总 **740.7237113000331s**；未接受 **28→29→30**。两个checkpoint的accepted均仅指rejection_metadata_only，diagnostic_accepted=false。编辑/审查/Git、Python初始启动和最终记录写入沿原口径不计capture，非完整wall，没有模拟小时推进。

恢复先读ful_v3 `checkpoint.json`、registration、size内的migration字段、unit报告及`cache_metrics.json`、PRE_SEAL findings、各exit与`probe_import_discovery.receipt.json`；再读ful_v2的size_failure/checkpoint和post-failure snapshot。v3登记831项输入，继承AOC9的788-input祖先及HISTORY8，包含所有旧失败和输入raw；Source49 epoch仍 **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**，49份raw保持。

## 下一步

cache候选的词法等价与方法门槛已有证据，完整import仍未闭合。下一步先在优化helper上设计有界的真实计数/分段诊断，覆盖256之后的执行，固定规模、采样、输出、预算与收尾条件，以确定实际cache/image/其他guard成本及外部加载分布。现有full日志不足以区分这些原因，不能因为方法fixture降低80%就宣称完整链已提速，也不能直接重复或延长本full CLI。

之后仍需完整B_S import、OBSERVED profile、LIVE成功/故障矩阵、真实producer/owner/Job/bootstrap、ACK/issuer/permit、quiet/返回与父端采用。E/U、独立TCB/native、完整runtime/P1/role/permit/F/science/resource/formal/run authority全部false。本轮只保存开发实现、方法验证与失败诊断。

39项并行文稿/图件/文献dirty保留；Git发布覆盖本轮成功方法证据、两次失败、source snapshot与独立后继，四导航只前置本轮状态段。远端提交号以发布后实时读回为准。
