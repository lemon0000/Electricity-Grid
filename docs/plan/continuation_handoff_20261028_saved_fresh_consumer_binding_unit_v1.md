# F：一次性消费接口开发验证完成，真实连接待执行

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[冻结profile匹配LIVE交接](continuation_handoff_20261028_saved_fresh_profile_matched_live_v1.md)，本包合同为[producer/consumer实施范围](staged_deliverability_c_saved_fresh_producer_binding_admission_scope_v1.md)。这是可供新对话继续的开发检查点，宽goal仍active，完整F未完成。root唯一writer；既有wire_root_review只读PRE_SEAL，未发official verdict/receipt/seal。

## 实际完成与证据边界

新core38加入同步一次性 `prepare_consumer/consume_once`；namespace helper v2从held Source49建立固定10-member binding计划，实际目标为ENTRY `_expectation_binding_entry`。计划在IMPORTING且boundary CLOSED时准备，六adapter成员逐项连接已认证的14-root tuple；四leaf的函数/code/default/globals/module/path从prepare开始强持，不上溯为更早的import身份连续性。固定tuple内保留可变对象，逐次核原对象和metadata。host独立AST oracle绑定NFC10 checkpoint和49 source pins，核11个精确声明/default表达式；child不从可变ast属性派生默认值truth。

消费状态为PREPARED→RUNNING→CONSUMED/FAILED；runtime保持LIVE到close。固定ENTRY consumer只收到binding，返回adapter的身份必须与原adapter一致；前后检查成功且held close成功后才交还≤2048B canonical data。失败保留primary和post/cleanup secondary。core首个check、entry、dispatch、source-bookend、seal、cleanup及put/type/length所用原代码或primitive在定义时固定；builtin全局名阴影也进入bookend。旧源码、49-source epoch、科学adapter和所有旧执行记录保持原字节。

**41/41 unit，0 failure/error/skip，完整84帧；独立PRE_SEAL、saved重放和checkpoint全通过。** 其中原25个冻结测试复用，本轮16个测试覆盖同code clone、equal default、kw内容、四leaf同步替换、固定manifest/edge/source清单、plan与creator、retention、callback中变更/异常、重入/重试、post/close失败、partial commit、首次全局替换、malformed result及cleanup secondary。测试在logical fixture中实际执行原ENTRY consumer字节码；native owner、entry、bookend和close均有明确synthetic边界，**本包没有真实LIVE→consumer正例**。

新probe36已经写入prepare→finish_import→consume调用顺序，但未执行cold/startup/normal，也未创建未来NFC11 manifest。最近真实运行仍是NFC10 child12980的profile-matched LIVE→CLOSED，该对象已经关闭，不能从摘要或旧PID恢复。所有producer capability、完整P1/角色/permit/OwnedChild/Job、资源、科学、正式、运行和F门禁仍false。

## 不可变结果与费用

Root `results/tables/staged_rts24_saved_fresh_consumer_binding_unit_v1_non_authoritative`，精确 **7文件915192B**。checkpoint SHA **549fe7b12a498c8fdde4e67e5397a2b4dd137881c42dcd54411436b562e8e509**；accepted=true、diagnostic_accepted=true，范围 `logical_binding_consumer_development_only`。registration SHA **9186a6b9e39c1e5e061bc2b14921875d3e9e80635368f43de9dc87ef0a494b57**，1134个effective inputs；原121文件10460646B全量archive pins一致，连同本包为 **128文件11375838B**。size/register后绑定的全部source/scope/inputs/result bytes冻结。

|阶段|charge秒|cap秒|
|---|---:|---:|
|size|3.0178968999971403|5|
|register|0.3039237999910256|4|
|唯一41-node unit|15.095170100001269|30|
|PRE_SEAL|0.9832027000084054|5|
|saved|0.9795156999898609|5|
|checkpoint|0.7030731000122614|4|

本包static **5.9876121999986935/60s**、unit **15.095170100001269/30s**，总 **21.082782299999963/90s**，余68.91721770000004s留原包。累计static473.5091595999795、pytest366.48897970000326、unittest158.23761210000157，总 **998.2357513999843s**；不接受仍 **38条**。NFC10余45.33581750001758s和所有旧剩余/失败保持，不退款、重置或跨包转用。费用为受控动作capture，不含工程编辑、人工复核、Git及Python启动wall；新增模拟跨度0h。

Unit runner 12.745s，PID37684/exit0；raw stdout13663B、stderr6803B，原pin和canonical帧已重开。846个healthy native memory样本，parent33436、child37684、原HANDLE556、80B结构全部连接。采样peak WS parent80007168B、child103628800B；同次两个peak字段之和最大183635968B。原memory_drain_v1复用：256MiB/process、512MiB/pair为采样停止帽；非连续/descendants/128MiB retention证明。进程HANDLE、pipes/readers全终态，无kill、timeout、truncation、reader或cleanup error。

## 新对话从哪里继续

先读本交接及既有agent.md第7–9节、当前计划/阻塞登记和真实Git/进程。不要重跑旧WIP或NFC10；先完成真实连接包的性能/资源准入。

1. 复用已验证的core38/helper v2/probe36。真实child必须重新由合法bootstrap建立相同LIVE owner，再调用已写好的固定consumer；不能用本包logical boolean替代。新parent需选择新helper路径并采用新result schema，完成独立source/metadata/retention/owner/PID连接。
2. 先解决传输上限。原parent34命令max29996/30000 UTF16仅余4；新增core/probe尚无可执行的exact command准入。此前旧payload的XZ静态比较只表明可能释放空间，未证明新payload可装入、startup等价或normal profile相等。本包未修改旧zlib loader。若用新codec，必须versioned transport、精确raw/AST/recursive CodeType等价、解码/内存/输出/单stream完整性反例及DLL-directory cleanup，然后重新startup admission；normal仍逐字比较原NF9 profile501203B/SHA a61fb973180f4031ebc024bb69ab162460955594c4bb53cc182d3da70559d3b6。
3. 新parent/validation/controller/checkpoint需纳入consumer result和CONSUMED/CLOSED终态、增加后的实际graph/source-bookend调用量、完整stdout/stderr与失败窗口。先算DAG、fixed call caps、RAM/存储/输出/硬停止和全包费用，使用独立后继预算，承接本包checkpoint/1134-input closure和38条不接受记录；不得递归运行所有旧controller。
4. 获得真实same-LIVE-owner consumer正例后，仍需父端采用、真正producer/P1数据与完整能力/资源闭包；原root catalog的33 legacy roots均未因此变成已替换或可复用，旧catalog保持原样。若需P1/actual role/native校准/模型/solver/长实验，按原合同与现有明确授权边界处理。

主要新文件：`experiments/staged_rts24_saved_fresh_pre_entry_lease_v38.py`、`experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v2.py`、`tests/staged_rts24_saved_fresh_runtime_handoff_probe_v36.py`、`experiments/staged_rts24_saved_fresh_consumer_binding_source_oracle_v1.py`、`tests/test_staged_rts24_saved_fresh_consumer_binding_v1.py`及本包driver。

Git收尾沿用四导航“新增前置段+原HEAD正文”的单独暂存；39项并行文稿/插图/文献dirty保持。同步后的commit/remote hash以实际回读为准；不能报告全局worktree clean。用户此时询问是否新开对话；建议在本检查点同步后新开，从真实连接准入继续。
