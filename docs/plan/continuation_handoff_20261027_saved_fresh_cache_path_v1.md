# C/F：cache路径构造复用通过方法级验证

2026-10-27，DRAFT_NONAUTHORITATIVE。接续[actual import交接](continuation_handoff_20261027_saved_fresh_runtime_import_timing_v1.md)，范围见[cache path合同](staged_deliverability_c_saved_fresh_cache_path_scope_v1.md)。root唯一writer，独立只读PRE_SEAL，无official verdict/receipt/seal或运行授权；宽goal继续active。原RTI1/size/RTI2及所有历史源码/失败字节冻结。

## 改动和证据

新增`experiments/staged_rts24_saved_fresh_bootstrap_import_cache_v1.py`，仅改原BS timing1的`_check_cache`。保留initial identity循环、roots字符串、全current扫描、exact str/isabs短路、root顺序和None/exact FileFinder/原始finder.path检查。每个合格key构造一次Path，两个base Path在本次调用遇首个合格key时惰性构造并局部复用；跨audit不缓存，其他函数与class成员AST逐项不变，identity/commit/ownership等检查不减。

等价范围依赖固定stdlib Path/os.path行为、固定合法ROOT/EXE与调用内状态稳定；不覆盖Path内部构造失败、monkeypatch或任意RAM。没有改变`.`/`..`、大小写、drive/UNC等词法语义。原EXE.parent已在循环外求值；is_relative_to内部的other构造及parents比较仍在，不能把外层次数收益当作整体成本比例。

8/8逻辑unit终态通过，0 failure/error/skip，charge**1.4801534/8s**，child正常exit0、未kill，HANDLE/pipes/readers终态，peak working set42086400B。覆盖原AST、路径边界/首拒绝顺序、initial missing/equal-not-is、finder类型/path、相邻调用变异、0/1/N构造次数、完整helper proof及三轮成本。构造计数为隔离逻辑context，性能组使用真实Path/os.path/exact FileFinder与独立cache/guard；未安装真实audit/owner/runtime。

固定32个runtime目录key、每轮80次完整方法扫描、每variant三轮，old-new/new-old/old-new交替。原始wall秒：

| 轮次 | old | new |
|---|---:|---:|
| 1 | 0.1052109000 | 0.0909083000 |
| 2 | 0.1051404000 | 0.0905705000 |
| 3 | 0.1055251000 | 0.0913337000 |

总new/old **0.8636685108**，中位数比 **0.8640578115**，均满足运行前固定的≤0.95条件；该fixture方法成本约降低13.6%。每轮explicit Path构造次数由独立计数oracle推导为10240→2720；不含Pathlib内部构造。

小case如实保留：单ROOT key的20 scans为old**0.0002226s**、new**0.0002385s**，新方法较慢；空cache各20 scans为0.0000653/0.0000318s，这个微量差异不作稳定提速证据。没有追加轮次等成功。独立只读PRE_SEAL未发现must-fix。

这些结果支持方法级等价与局部成本改善，**不证明完整cold import提速、预算内完成或F准入**。`candidate_adopted=false`，本轮0 cold child、0 ENTRY exec、0 adapter import、0模型/solver/P1/F调用。

## 保存与预算

root `results/tables/staged_rts24_saved_fresh_cache_path_v1_non_authoritative` 当前**12文件/294107B**，在16files/2MiB内。依次读取registration、unit admission/report/exit与raw stderr、metrics、pre_seal findings/admission/exit、saved_snapshot及saved.exit。所有文件及已执行helper/test/controller冻结，不原地修复或重跑。

scope static**0.6404031999991275/8s**、unittest**1.4801533999998355/8s**，合计**2.120556599998963/16s**。全历史static**207.08504860001563**、pytest**366.48897970000326**、unittest**52.97183230000155**，总**626.5458606000204s**，意外不接受仍**22条**。前驱失败与旧120/540/import8MiB超帽完整保留，新帽没有重置历史。编辑/审查/Git、Python初始启动和最终exit序列化不计capture，不是完整wall；无模拟小时推进。

Source49 epoch **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**及49个原字节不变；registration另pin了当前EXE/python312.dll、Pathlib/ntpath/importlib源与实际Python版本，均只是当前字节承接，不是独立expected truth或native认证。39项并行文稿/图件/文献dirty保留，只发布本scope及四导航新增段。

## 恢复与下一步

先核Git/process、Source49与上述saved.exit/metrics/helper pins，复用RTI2的真实partial import raw证据。当前旧runtime仍绑定BS timing1；本候选尚未接入真实cold，不得把方法级通过说成原超时已解决。

下一项应为独立cold successor：替换诊断root、绑定本candidate及原namespace timing helper，复用prefix-zdict但重新核完整实际command≤30000、payload及startup profile；先固定全路径/两child/一次adapter import/停止与保存预算，单位测试和只读PRE_SEAL闭合后才可执行有界诊断。对照本轮原始局部收益与RTI2阶段/栈，判断完整import是否前进；不直接扩大旧帽，不因局部13.6%推断完整F资源准入。逐事件identity/commit成本也仍未量化，单次cache栈不能作全时占比。

E/U、独立TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false；完整B_S import、M/D与NumPy政策的此runtime闭合profile、native cancel/完整收尾及后续实际producer/F均仍OPEN。
