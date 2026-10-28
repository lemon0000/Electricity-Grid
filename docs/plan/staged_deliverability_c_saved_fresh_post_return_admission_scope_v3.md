# 独立profile配对与LIVE：未执行准备草稿

2026-10-28，DRAFT_NONAUTHORITATIVE；NFC10独立有界normal/LIVE诊断合同。首次受控size前仍可修订，此后已执行bytes冻结。承接[OBSERVED→CLOSED实测](continuation_handoff_20261028_saved_fresh_post_return_observed_v1.md)。完整F及相关正式权限继续未完成，宽goal仍active。Root唯一writer，wire_root_review仅只读PRE_SEAL，无official verdict/receipt/production seal。

冻结前驱NFC9 checkpoint SHA5fb9c83a6ec9e7933e684a7f4ca2491fa52d9d7e1a6a8b7cc3740d9eb30428da，17文件2285992B，diagnostic_accepted=true；累计937.488786600002s、不接受38条。105文件8636628B及旧预算/失败保留，本包余42.22140910002054s不转用。

NFC9仅import_discovery，未传独立import_profile，finish正确产生OBSERVED。下一后继须先设计独立参考profile的来源及新normal case连接；原NFC9 import_profile.json为501203B，必须按原raw/pin使用，不能删行、改路径、放宽类型/排序或重算到目标结果来迎合相等。相等只能产生条件性本地LIVE状态，不能授予角色、permit、producer或F权限。

准备顺序：

1. 核当前parent manifest/check_plan、case路由、create-only输出与profile匹配实际DAG；旧POST validator只接受import_discovery/OBSERVED，不能直接换case后复用。新normal/LIVE前置与关闭后CLOSED必须分别核验，所有旧失败和cleanup路径保持。
2. 枚举新root/transport/helper身份对modules/cache/path/finder profile的影响。完整固定输入/Source49与当前环境相同不自动证明跨child profile相同；差异必须保存，不能修剪参考。新startup/profile必须有自己的raw/PID与收尾，Source49/freshness/两次profile一致保持。
3. 固定参考profile复制或外部ref白名单、文件cap和input闭包，明确其原始NFC9 raw SHA及自身路径/transport provenance；检查normal分支JSONL/journal是否增加文件或产生其他历史重放，不能写满已冻结NFC9 root。
4. 给出新的完整次数/预算/资源/输出上界与故障矩阵，覆盖参考profile缺失/漂移、schema/false claims/TCB变化、OBSERVED冒充LIVE、boundary已闭合但finish不匹配、失败后清理、raw/derived/saved重开。再建立versioned constructor/oracle、unit和独立PRE_SEAL。
5. 只在上述短诊断合同闭合后考虑唯一有界配对路径；不启动native校准、P1/实际role/OwnedChild/Job、模型/solver或长实验。其他动作仍受原授权与agent.md第7/9节约束。

可复用的成本证据只限覆盖相同的路径：NFC9 parent6.2097452s、外层actual9.7616024s，30图21 namespace/9 adapter、5 Source49 bookends、finder_check10、adapter_check8、profile2；adapter图137 nodes/28501B、namespace2940/376728B。新参考读取、case/journal、比较失败及保存成本需单独界定。原sampled256MiB/process、512MiB/pair、40图/4MiB image、stdout131072/stderr32768与command30000等帽不能由旧余量自动扩张。

## 实际接线与预期不变性

NFC10：core37/probe35仅将manifest root迁至独立nfc_v10；不新增child imports、helper注册、sys.path或PathFinder查询。原namespace_post_return_v1、bootstrap_post_return_v2（完整14-name literal）、memory_drain_v1复用原bytes。parent34、live_profile_reference/validation/transform/checkpoint_v1及live_profile_v1 tests为新host plumbing；helper仍通过ModuleType+compile/exec私有加载，不进入sys.modules。静态证明只支持尝试，不替代真实normal的exact profile比较。

固定NF9参考501203B/SHA **a61fb973180f4031ebc024bb69ab162460955594c4bb53cc182d3da70559d3b6**，路径和checkpoint SHA均由reference函数body-local literal固定。每次读取重核原CP/profile/pin/Source epoch/canonical与false claims；同一次调用复用已读immutable raw，跨调用不cache。参考不复制到新root、不重写。profile_admission同时绑定本包startup、当前transport/registration/helper pins及原NF9 descriptor；parent normal manifest从同一admission产生固定外部ref。argv保留manifest raw SHA，child原read_file核pin并与内部observed raw精确相等才置LIVE；probe仍比较前一profile与finish返回raw。

parent启动前后fresh reopen admission、manifest和原profile，两个context须相同；parent独立decode observed raw再与NF9完整canonical bytes比较，不能只信child自报LIVE。saved/checkpoint重开相同引用、manifest、raw/pin、receipt与派生。新normal按create-only `probe_normal.receipt.json`保存，不进入旧七case序列journal；其他旧parent与记录冻结。实际profile漂移保存raw及字段级diff，diff不参与匹配或修改参考。

该状态只表示固定的非权威前驱观察相等。child无须额外嵌入参考literal：选择根在受绑定parent/admission代码与原artifact，manifest raw经argv连接，child消费该固定ref；不由此宣称独立TCB或任意RAM隔离。

## DAG、优化与固定预算

执行DAG：size→register→唯一25-node unit child（原21+4组新fault tests）→独立PRE_SEAL→唯一startup child→startup/reference admission→唯一normal child→saved replay→checkpoint。startup/admission失败不启动normal；normal失败停止后仅保存失败元数据checkpoint，不重试或延长。当前无长实验、native校准、P1/实际role/OwnedChild/Job/F、模型或solver。

child名义工作仍为30图=21 namespace+9 adapter、5 Source49 bookends（1pre+4post、196 post高层reads，其中98 active hook）、close EXE+4external读、auth1/finder_check10×14行/adapter_check8/profile2；新增一次501203B参考profile read/byte compare，不增加entry/图或source_bookend。host按代码DAG的保守上界每phase至多24次reference重新打开（每次1 CP+1 profile），另有direct inputs前后bookend，约≤13MB额外raw profile读；无递归重跑历史controller，只用原v3 leaf和已冻结记录。保存与checkpoint也核相同闭包。

不缩减source/graph/finder freshness扫描；跨回调ABA等价无证明，未采用跨调用cache。host原始reference重读+decode属于当前可测小成本，同一调用内只保留raw与小descriptor，不累计样本/整包memo。NFC9实测支持约10s normal外层的量级，新增参考、admission和diff上界由固定30s诊断验证，不当完整F性能准入。

独立预算 **85s=static65+unit20**：

|阶段|cap秒|依据/次数|
|---|---:|---|
|size|6|原1.886s，新增host ref/validator与输出闭包；一次|
|register|4|原1.761s，新增固定ref inputs；一次|
|unit|20|原21项9.786s，新增4组reference/LIVE/failure checks；一个child|
|PRE_SEAL|5|原3.330s，完整fresh closure与unit重开；一次|
|startup|6|原3.939s，同imports/环境新transport；一个child|
|startup/reference admission|5|原3.078s加固定NF9引用检查；一次|
|normal/LIVE actual|30|原9.762s，加501KB读与parent前后bookend/diff；一个child|
|saved replay|5|原3.198s，加reference/manifest比较；一次|
|checkpoint|4|原2.039s，加同链字段重开；一次|

旧937.488786600002s/38条不接受及各包余量不退款、不重置、不转用。capture不含全部工程编辑/人工review/Git wall；模拟小时新增0。所有资源/科学/正式/run gates仍false。

## 输出、停止与恢复

Root≤17文件/4MiB；成功预计16文件，normal仅plan+receipt、参考在旧root。新host参考/validator/25-node streams增加快照，登记前明确registration帽从786432改为1048576B、unit exit从32768改为65536B，saved固定body从4096改为6144B；这些只容纳诊断元数据，不改变任何科学接受阈值。driver源码≤65536B、profile decode≤1MiB（eof/无尾巴）、两receipt各≤1MiB、saved≤65536B、stdout≤131072B、stderr≤32768B保持。census21680+graph5400+22stage1292=28372B；saved packed理论≤60084B。原单图node50000/depth256/image4MiB、总图40及getter每类1000000帽保持。

命令需分别算startup与normal：工程值discovery29996、normal29993 UTF16；size/register必须重算两者、记录各case与最大值且≤30000，不能因normal文件名较短忽略startup。任何source/input/path/metadata漂移拒绝，已执行bytes不原地修改。

原memory_drain_v1 bytes14253/SHAe0c54dc42657c223a81e7df8e2316289de58f95ce60457080b27fdf52931bc2d；held actor/API/handle/PID/80B结构与cleanup前后metadata保持，每进程256MiB/pair512MiB sampled peak WS/private停止、0.01s请求、最多4096样本、last_live_poll_only/O(1) maxima，无exit后补采。continuous_bound_verified/combined_retention_verified/resource_admission=false，不推导128MiB retention或descendants/连续覆盖。

任何timeout/无进展、query/PID/HANDLE/clock/内存/样本/输出上限、reference/metadata/profile/graph错误均拒绝并保留raw、primary/secondary与费用；主线程deadline和原采样/输出机制不变。parent kill/wait、pipes/readers/writer/stdin/HANDLE须终态，child未知状态保持未知。成功必须before-close LIVE、runtime_was_live=true而live_at_report=false、最终runtime/resource/boundary CLOSED、primary=null/secondary=[]、原5 bookends/30图及auth2/pendingfalse全部成立。

新unit重点：reference缺失/同长度改写、admission/manifest path/pin/transport/source/authority篡改、四profile字段分别mismatch、第一次与finish内profile不同、match后entry失败、LIVE后close失败、child伪LIVE但parent raw不等；完整raw与所有旧failure测试继续。PRE_SEAL只读审查与实际终态复核均非official。

LIVE之后仍需真实producer binding、父端采用、当前F完整闭包及适用资源/硬停止证明。loaded Python graph、registry/finder behavior、任意RAM ABA、连续/descendants/128MiB retention、native effects、独立TCB与科学/正式结论仍OPEN/false；这些是实质剩余边界，不由文档、goal状态或本地测试改变。
