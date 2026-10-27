# AOC6登记拒绝：只读stdlib来源差异诊断

2026-10-28，DRAFT_NONAUTHORITATIVE。AOC6 size已通过29972/30000，register因runtime origin表不相等拒绝；旧root与全部输入冻结，cold/ENTRY/adapter均0。rejection checkpoint只接受metadata保存，累计670.4226138000188s、不接受26条，不将该拒绝改为通过。

本次只读重建两个启动顺序：同一EXE/-B/-s、同一frozen driver前缀定义，分别按size与register中达到runtime_leaves前的纯计算顺序调用previous/migration/source/transport及snapshot编码。明确不调用size_admission/register/run/one_case，不写旧root、不创建cold、ENTRY或solver。两个普通metadata child各≤2s，整体inspection≤6s（含输入pin/收尾），最多2 child、并发1；失败保留，不重复测量。

root `results/tables/staged_rts24_saved_fresh_origin_order_v1_non_authoritative` ≤4文件/1MiB；stdout65536/stderr16384/child，capture使用既有冻结bounded helper，保存全部raw stream、pins、正常终态与charge。新script和本scope、AOC6 size输入/终账、capture源码均重开；输出来源表与保存size比较added/removed/changed。若复现不一致也原样报告，不推断原因。它是诊断，不是旧register重跑或新cold准入。

累计从AOC6终账续记static234.46304480001277、pytest366.48897970000326、unittest69.47058930000276，总670.4226138000188s。不接受从26续记，旧失败和所有帽不重置。Source49与39项并行dirty保留；完整runtime/TCB/native/producer/F/科学/资源/正式/run authority全部false。
