# namespace graph：冻结reader外层时标诊断

2026-10-27，DRAFT_NONAUTHORITATIVE。Cache候选34项完成，唯一失败是实际ENTRY旧/新SHA均696而未减少；图/objects等价检查已先通过，合成共享DAG5→3不代表实际收益。候选NSv3及失败完整冻结，不接冷路径，累计意外不接受21。

本后继复制冻结NSv2为entry_namespace_timing_v1，仅在全图reader外加default-held wrapper：每次实际调用发enter/exit时标到已有stderr，finally发exit；原freeze_namespace_graph源码函数节点含位置必须相等，CodeType除所属helper文件名外递归相等，原图、objects与错误保持。Wrapper不跳过、缓存或跨entry复用任何认证。新增core11/parent8/probe8接该诊断helper，BS3原bytes复用。Schema与Source49不改；独立profile，不用watchdog/setprofile/settrace。

先以6项逻辑unit核原reader code相等、old/new graph+对象序等价、异常exit帧、原生default roots绑定、完整ENTRY alias/cleanup及wrapper/reader无global opcode。然后PRE_SEAL、独立startup discovery/admission、唯一pre-import child；B_S安装/audit handoff/PATH6后固定diagnostic_stop_before_adapter，最多2次ENTRY exec、adapter import0。该stop预期失败不称LIVE/B_S完成。若timeout保存partial时标与unknown self-close，不继续原import验收。

static≤20s、unittest≤4s、总≤24s；登记≤2s、unit≤4s、PRE_SEAL记录≤1s、startup≤4s、profile≤2s、pre-import≤6s、metadata≤2s，余static3s。并发1，unit最多1 capture child，cold最多2 child，无自动repair/扩帽。stdout131072、stderr8192/最多64帧、command30000UTF16、payload131072；root results/tables/staged_rts24_saved_fresh_ngt_v1_non_authoritative ≤24文件/4MiB；RAM只观察。Payload仍含位置AST/完整CodeType与源码相等，Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875。

前驱累计来自cache rejection_snapshot：static189.15025950001586、pytest366.48897970000326、unittest48.92709509999986，旧失败/超帽保留。时标只给真实多次图成本和间隔，不把源码静态15次下界当实测，不把helper图等价推成整链提速。无模型/Highs/solver/P1/hold/capture/replay/OwnedChild/Job/F；全部E/U/TCB/native/完整runtime/P1/role/permit/F/科学/资源/正式/run authority仍false。已执行字节冻结，保留39项并行dirty。
