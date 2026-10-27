# B_S image pin真实audit：按实测分配同一总帽的剩余秒

2026-10-28，DRAFT_NONAUTHORITATIVE。完整矩阵/资源/归档与codec修复承接[AOC7合同](staged_deliverability_c_saved_fresh_image_pin_cold_scope_v2.md)。AOC7 size/register/PRE_SEAL/startup均通过；profile校验error=null，但charge1.0872899999958463超过阶段1s，故phase accepted=false、禁止audit。拒绝终账accepted仅指metadata保存，scope static6.240888099993754s，累计679.6172726000179/count27，实际仅startup cold1、ENTRY/adapter/audit0。全部17个root文件及输入冻结，不能沿原路继续。

AOC8在原static/total22s内将剩余1s分给profile（1→2），阶段最大值为size2/register2/PRE_SEAL2/startup3/profile2/audit8/saved2/checkpoint1=22s。依据是AOC7实测size0.9731、register0.9339、PRE_SEAL0.9265、startup1.6784、profile1.0873、拒绝metadata0.6418；profile耗时包含前后完整历史/input pin重核。没有增加总帽、audit8s、次数、Source49或科学/校验接受阈值，不退款/重置旧费用。无新unit，旧9/14/4原pins复用；最多新startup与strict64两个串行cold child，失败保全且不重跑。

core22/probe19/parent19相对冻结AOC7仅6 literal（OUT2/1/1、parent CORE/PROBE各1），控制器只换新路径、接续AOC7拒绝账并调整profile时长；codec公共预载、严格来源表相等、exact64与异常链、saved/checkpoint、metadata quota/预留槽、Popen/ENTRY/adapter次数及全部门禁不变。AOC7 checkpoint新增字面量SHA和完整root/input pins进入前驱DAG；新前驱总账只取该679.6172726000179/count27，不重复相加旧诊断。

root `results/tables/staged_rts24_saved_fresh_aoc_v8_non_authoritative` ≤24文件/4MiB；先重新size/codec/manifest、登记与非官方PRE_SEAL，再新startup/profile和唯一strict64。所有cold/role/permit/F/science/resource/formal/run authority仍须原独立证据，不因本scope或未来固定前缀通过而打开。Source49 epoch与39项并行dirty保持；累计static243.65770360001193、pytest366.48897970000326、unittest69.47058930000276，总679.6172726000179s、不接受27条。编辑/审查/Git及既定启动/最终记录写入不计capture，不是完整wall。
