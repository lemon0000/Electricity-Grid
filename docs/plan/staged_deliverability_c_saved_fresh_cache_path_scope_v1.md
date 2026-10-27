# B_S cache路径：本次调用内构造复用

2026-10-27，DRAFT_NONAUTHORITATIVE。起点ae59a87fb682d4ede857fecdd153a623455b31c8，继承[实际import交接](continuation_handoff_20261027_saved_fresh_runtime_import_timing_v1.md)。真实2s单样本位于_check_cache→pathlib路径比较，不证明全7–8s占比或旧超时根因。原所有源码/结果冻结，root唯一writer、独立只读PRE_SEAL，无official verdict/receipt/seal/run authority。

候选`bootstrap_import_cache_v1.py`仅改_check_cache：原initial identity循环、roots字符串、全current扫描与先后顺序不变；new key先exact str、再isabs，合格时每key构造一次Path；首个合格key才惰性构造两base Paths，后续只在本次调用复用。两个root的比较顺序、None/exact FileFinder/原始finder.path==key及异常消息保持；不跨audit缓存、不减少任何identity/commit/ownership/metadata检查。其余所有top-level函数和class成员AST不变，BS timing/watchdog函数保留原bytes语义。本轮只方法级验证，不arm watchdog、不import adapter。

等价前提为固定stdlib Path/os.path/FileFinder行为、固定合法ROOT/EXE root以及本次调用内对象稳定。候选在首个ROOT命中的key上提前构造EXE base；不声称覆盖Path内部构造器故障、monkeypatch或任意RAM。保留.`..`/大小写/UNC等原词法语义，不改为字符串前缀或resolve。原实现已在循环外求EXE.parent；不能计为新增收益。is_relative_to内部仍构造other/遍历parents。

完整路径：登记≤2s→8逻辑unit capture≤8s→独立PRE_SEAL记录≤1s→metadata saved≤2s，另预留≤1s终态checkpoint/失败保全与2s static余量。static≤8s、unittest≤8s、合计≤16s；最多1个unit child、0 cold child、0 ENTRY exec、0 adapter import、0模型/Highs()/solver/P1/hold/capture/replay/OwnedChild/Job/F。单阶段失败/超帽保留并停，不重试已执行字节。root `results/tables/staged_rts24_saved_fresh_cache_path_v1_non_authoritative` ≤16文件/2MiB，metrics≤64KiB，capture stdout65536/stderr16384；RAM只观测，不能替代实际import RSS。

8节点按顺序覆盖：原AST差异；root/路径边界与首拒绝项oracle；initial missing/equal-not-is；None/FileFinder/subclass/wrong-path；相邻audit变异；0/1/N explicit Path计数；完整helper validator与proof；有限三轮真实Path成本。方法级old/new使用等内容独立cache/guard，原函数为oracle，核异常类型/消息及拒绝顺序。构造计数使用独立instrumented逻辑context，不作真实wall。性能使用真实Path/os.path/FileFinder，32个runtime目录key×80 scans×3轮/variant，顺序old-new/new-old/old-new；另各20 scans记录空cache/单ROOT key。每轮记录wall、scan/key/root比较数和variant顺序，保存原值，不只均值。

预先固定采用条件：所有语义/身份/变化反例通过，代表32-key三轮new总wall≤old总wall的95%，且new中位数≤old中位数的95%。未达到则候选不采用、失败和metrics冻结，不补测等成功；达到也仅支持独立cold successor的后续验证，不证明全import提速或F准入。0 eligible时两者explicit Path均0；N>0时原为2K，候选N+2，K为实际root比较数。单个ROOT key旧2/新3，必须如实报告小case成本。

前驱累计static206.4446454000165、pytest366.48897970000326、unittest51.491678900001716，总624.4253040000215s，意外不接受22条；全部失败、旧120/540/import8MiB超帽保留，新帽不重置前驱账。Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875与49字节不变。编辑/审查/Git、Python初始启动和最终exit序列化不计capture，不是完整wall。

E/U、TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false。39项并行dirty保留；本测试没有真实guard/audit或runtime owner，不能以方法级fixture冒充完整runtime证据。
