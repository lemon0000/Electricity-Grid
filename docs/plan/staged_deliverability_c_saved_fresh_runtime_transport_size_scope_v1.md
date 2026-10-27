# actual import 诊断：有限 transport size admission

2026-10-27，DRAFT_NONAUTHORITATIVE。RTI 登记在 command≤30000 UTF16 检查拒绝，static charge1.2287622s，unit/cold均0；原4文件、已执行helper与controller冻结，累计不接受22条。前驱全历史610.6189090000219s加此失败，不退款、不覆盖。

本次只做一次静态分析，≤2s、0 unit、0 child、0 adapter import、并发1。固定8种候选：zlib default/filtered各mem7/8/9共6种，另default mem7/8以原bootstrap明文prefix作为只读zdict共2种。复用既有6参数搜索证据，不重复运行child。zdict仅来自当前完整命令中既有prefix bytes；decoder在payload前从实际sys.orig_argv取同一prefix，不读取文件、不引入新codec/native依赖。每种候选必须有限解码、eof与unused检查并逐字节等于同一原payload，保持payload AST/CodeType及所有guard字节；唯一变化为transport压缩与相应解码构造。

记录当前精确command长度、每个候选长度、roundtrip和pin，选择最短候选；不扩大30000 UTF16、131072 payload或任何policy上限。未达到上限则只形成否定size证据，不运行后续。达到上限也只允许为独立successor登记提供机械编码方案，仍须核实际新版本完整command、unit与独立PRE_SEAL后才可有界cold诊断。

root `results/tables/staged_rts24_saved_fresh_rti_transport_v1_non_authoritative` ≤6文件/1MiB，保留原transport、逐字节payload、chosen transport及size report，写入均create-only。原RTI与NGT pins、Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875逐项核验。新static charge接续前驱累计账，不改变旧120/540/import8MiB超帽与历史失败。编辑/审查/Git、Python初始启动和最终JSON写入不计capture；不是完整wall。

所有E/U、TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority保持false；此分析不证明import完成或任何运行准入。root唯一writer，子代理只读，不修改39项并行dirty。
