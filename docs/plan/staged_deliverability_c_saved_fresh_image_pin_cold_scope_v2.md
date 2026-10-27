# B_S image pin真实audit：统一codec预载的独立AOC7

2026-10-28，DRAFT_NONAUTHORITATIVE。完整行为/strict64矩阵/archive配额承接[AOC6合同](staged_deliverability_c_saved_fresh_image_pin_cold_scope_v1.md)。AOC6 size29972/30000通过，register因来源表不等拒绝，终账static1.997565s、累计670.4226138000188/count26，cold0。旧core20/probe17/parent17/controller/checkpoint与8个结果文件全部冻结。

只读origin v1花1.5583934s，未复现；其重建遗漏实际登记前的UTF-16 argv编码，不能据此写成无差异。[v2诊断](staged_deliverability_c_saved_fresh_origin_order_scope_v2.md)补此步骤，花1.3953773s，复现register相对size仅新增`encodings.utf_16_le`，added1/removed0/changed0；size仍与原表一致。两个metadata root原样保留，均无cold/ENTRY/adapter。累计static237.41681550001817、pytest366.48897970000326、unittest69.47058930000276，共673.3763845000242s、不接受26条。

AOC7唯一行为修复是在controller的`runtime_leaves()`公共预载中明确import `encodings.utf_16_le`，之后仍对size/register的整个来源表做严格相等；不忽略或放宽新增module。子进程bootstrap/BS helper不改此行为。core21/probe18/parent18相对冻结AOC6仅6处literal：core OUT2、probe OUT1、parent OUT/CORE/PROBE各1。机器存旧新pins、counts、归一raw/AST等式；image-pin1 exact9/9、原census14/terminal4按19项复用链承接，无新unit，不重跑旧CLI/失败或任何实验。

前驱DAG新增AOC6拒绝checkpoint及两个origin inspection的字面量SHA、精确inventory、全部input/root pins和累计账。相同22s总/static帽内，将PRE_SEAL从1s改为2s，覆盖新增前驱pin链回读，消耗原2s余量中的1s；阶段上界变为size2/register2/PRE_SEAL2/startup3/profile1/audit8/saved2/checkpoint1=21s，余1s。unit0、最多startup与fixed64两个串行cold child，audit8s、全部stream/file/RAM/command/payload/Source49与失败保全合同保持；新帽不退款或重置旧账。controller/archive在专属root单writer下先保留exit/checkpoint槽，parent元数据配额wrapper不修改child policy；严格saved与checkpoint绑定不变。

root `results/tables/staged_rts24_saved_fresh_aoc_v7_non_authoritative` ≤24文件/4MiB。先新size/codec/manifest与独立PRE_SEAL，后新startup/profile、唯一strict64。任何来源漂移、超帽、缺帧、timeout/kill、primary/secondary或收尾不匹配均拒绝并create-only保存，不原路重跑。all_unselected_events_verified/candidate_adopted及E/U、独立TCB/native、完整runtime/producer/P1/permit/F/科学/资源/正式/run authority全部false；通过也仅为固定selected open前缀相容性。Source49 epoch与39项并行dirty保持，编辑/审查/Git不计capture，不是完整wall，无模拟小时推进。
