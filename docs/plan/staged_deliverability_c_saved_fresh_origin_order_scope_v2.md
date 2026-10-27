# AOC6来源差异：补齐UTF-16命令编码顺序

2026-10-28，DRAFT_NONAUTHORITATIVE。接续[首轮只读诊断](staged_deliverability_c_saved_fresh_origin_order_scope_v1.md)。首轮metadata执行成功，但两个重建表都等于size保存表，未复现拒绝；不得写成已找到原因。其register重建省略了实际在runtime_leaves之前执行的`list2cmdline(...).encode('utf-16-le')`，本次只补这一步验证是否引入延迟加载的stdlib叶。

独立v2 root/collector，原v1与AOC6全部字节保留。沿用两普通metadata child各≤2s、总inspection≤6s、stdout65536/stderr16384、root≤4文件/1MiB、并发1与create-only失败保全。0旧CLI路径调用/旧root写入、0cold/ENTRY/adapter/模型/solver/F。复用v1输入与终账pins，比较added/removed/changed，不因结果不符合预想追加运行。

累计从v1 accepted inspection继续：static236.02143820001515、pytest366.48897970000326、unittest69.47058930000276，总671.9810072000212s、不接受26条。所有旧费用/失败不重置；Source49与39项并行dirty不变。完整runtime/TCB/native/producer/F/科学/资源/正式/run authority均false。
