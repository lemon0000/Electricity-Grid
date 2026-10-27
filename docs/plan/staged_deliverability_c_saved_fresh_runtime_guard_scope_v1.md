# runtime guard：三项信任根修复与有界接线准入

2026-10-27，DRAFT_NONAUTHORITATIVE，起点63810564fd967265775b8be66674b0ba845ee322。root唯一writer，独立只读PRE_SEAL；不产生production seal、official verdict/receipt或运行授权。上一runtime_handoff17文件/771531B、两代代码、一次timeout及唯一repair全部冻结；新scope不重算或扩大旧帽。

## 必须交付的行为

建立core v7、B_S v3、parent/probe/tests各v3及独立controller/root。Source49和ENTRY/科学adapter不改，epoch仍acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875。原namespace v2复用。

1. Bootstrap validator接收probe定义时持有的完整native builtins tuple，在proof构造前后核完整keyset和逐value身份，proof强持全部成员；helper的builtins dict必须是该原dict。不能从篡改后的运行时重造expected。
2. Boundary强持同一runtime proof及由其导出的全部函数对象；审计分类以原生type/len/str和对象身份匹配其code/defaults/kwdefaults setter，立即sticky拒绝。动态M/D函数继续保护。审计busy路径只用identity verifier，不读code/default getter。
3. 删除_req槽；_entry先held full verifier，_audit_entry/_ownership先held identity verifier，再用held原checker或native reject核proof/owner/commit。close的root失败必须落入分层errors，惰化hook、FAULTED并缓存primary/secondary，不能把校验异常放到cleanup框架之外。

新增27个固定unit nodes：保留20个逻辑回归，加完整builtins替换、pin/phase各code/default setter四项、已移除_req注入、tuple漂移贯穿close各一项。Exact-type stage0逻辑boundary seed保留原_entry/_audit_entry/_ownership/_image/verifier，实际安装原回调并发sentinel；只使用当前unit machinery，不声称factory B3/flags或native准入通过。所有构造、元数据替换及hook最终惰化，逻辑HANDLE各close一次。科学adapter只用原逻辑AST图fixture，不运行科学函数。Root失败的异常由zero-global failure factory持原生alloc/init/tuple/put构造，先惰化FAULTED再缓存，避免依赖已漂移builtins。

## 路径、复用与成本

完整开发路径：登记原字节/pins与新helper snapshot → 27节点unit → PRE_SEAL关闭三finding → 独立startup discovery/admission → 独立B_S import discovery/admission → normal及precommit/postcommit/blocked-install/handoff-middle/M-only/after-D六故障窗口 → metadata/raw/pin保存核验。所有cold必须在finding闭合后才启动；不直接调用旧repair_driver。

生产cold完整持Source49 raw、ENTRY双exec、唯一native owner commit、pending hook/审计交接、同一path list4→6、meta_path B3→B3+M→D+B3+M、实际adapter import、M/D源函数认证、直接adapter global/class图、独立profile匹配、分层cleanup。每child最多2次ENTRY exec/1次adapter import。仍不构造模型、Highs()、solver，不调用hold/capture/replay/P1/OwnedChild/Job或F。Native扩展import属已声明的条件性distribution叶；第三方内部/registry内容/native行为未认证。

优化复用：不重跑旧失败或旧scope的20-node helper；新27节点只对新版本验证。普通owner fixture只读ENTRY raw，adapter图用完整49；cold仍完整49。复用旧固定policy原bytes、Source49 expected map、native parent bounded drain/capture实现，不能复用旧instance/profile或把旧unit当新成功。上一20-node8.584s是新主组18s估算依据；七项guard反例增加约3–5s。Cold成本尚未观察，故先独立discovery，任何超帽即停止当前路径并保存，不扩帽或连续重试。

新scope static≤80s、unittest≤30s、总≤110s。登记≤3s；unit主组≤18s、只预留一次显式repair≤12s；PRE_SEAL记录核验≤1s；startup discovery≤8s/admission≤3s；B_S discovery≤10s/admission≤3s；七例cold总≤40s（normal≤8、其余每例≤5，逐例先确保完整预算）；saved≤6s。静态声明上界74s，留6s失败余量。最多9个cold child、并发1，普通unit最多两个独立capture child。PRE_SEAL未闭合不得启动cold；phase失败保留原bytes/raw/exit/费用并停止后续链。

为控制command长度，新parent压缩前仅将payload的非代码comment文本替换为等长空白，保持所有物理行和代码列；登记时强制含位置AST及完整编译CodeType与原payload相等。源码原bytes仍逐字绑定，实际传输bytes另有pin，不改变已执行旧transport，也不新增压缩native依赖。

新root results/tables/staged_rts24_saved_fresh_runtime_guard_v1_non_authoritative ≤40文件/8MiB；Source49 raw≤2MiB、helper≤128KiB、transport command≤30000 UTF16、stdout≤131072/stderr≤32768、metadata raw≤1MiB经有界zlib/base64传输、module/cache各≤4096。只保存强refs/metadata，不复制第三方目录。RAM只观察，不声称hardcap或整F资源准入。

前驱累计static169.32181660001083、pytest366.48897970000326、unittest30.03583439999784、合计565.8466307000119s及16条意外不接受记录续记；旧static120/540/import8MiB超帽保持。新scope有独立帽，不称全累计落任何旧帽内。编辑/审查/Git、Python初始启动和最终exit序列化不计capture，不等于完整wall；不推进模拟小时。

所有E/U、独立TCB/native认证、full runtime/P1、roles/permit/F、科学/资源/正式/run authority仍false。新scope只形成开发及成本审查证据。发布时只同步本范围和四导航前置段，39并行dirty正文/图件保持。
