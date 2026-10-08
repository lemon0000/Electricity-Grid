# H1 native export 对应性开发 guard

R3 DRAFT_NONAUTHORITATIVE。新增 `experiments/h1_native_export_guard_development_v1.py`，不修改原 native collector、数值接受规则、grammar 或封存闭包。此模块没有 solver 调用。

`live_export` 从当前 canonical Pyomo model 枚举完整变量对象，以对象身份核验 forward map、reverse map 与 native variable 全集严格一一对应。拒绝缺项、重复 native handle、外来同名 Pyomo 对象及非逆映射。读取已存在的 native objective expression，限制最多362项、拒绝重复变量项，并以二进制浮点的精确 Fraction 核验 constant 与聚合系数。只支持单个 active linear minimization objective，同时要求调用者传入的 native ModelSense 为精确 built-in int 1；maximize、bool及float均拒绝。

该 live 接口要求传入同一批 retained native handles；尚未以新 native adapter 运行证明所有实际 API getter 保持该对象身份。不能用 fake native objects 的测试声称 native export 总覆盖已成立。若未来 adapter 返回不同 wrapper，必须另行证明其句柄对应性，不能退化为只比较变量名。

`saved_report` 接收完整原始 bytes 和当前阶段的 canonical model。先检查 v2 条件 grammar 与原始 canonical serializer bytes，再核验变量全集/唯一性、fixed值、constraint计数、referenced assignment及hash、两路objective terms引用与assignment值、精确algebra和exact objective。对应性判定不采用新增容差，不做投影或修改 raw。所有形状和语法均须满足891变量、1272约束、362 terms和38-byte UID token的开发边界。

报告没有保存 live reverse-map handles，因此 saved-report 成功不能证明当时执行过 live check。返回字段仅为 `report_shape_and_objective_correspondence_checked`，并明确 `full_scientific_replay_required=true`；没有核验完整constraint structure。对应性也不证明约束可行、optimality、数值接受或 native认证；这些仍须既有完整科学重放。超界/缺provenance/不一致抛出 `ExportUnresolved`，不是不可行证书。

调用次序要求 raw ingress 完整写盘/fsync/读回及 receipt 后，再调用 guard 和科学消费者。测试验证 guard 异常后 exact raw及receipt保留、入口poison且无retry。模块自身没有存储写入；尚未接production capture、worker或独立hour Job，也不保证在 raw尚未返回、超过旧16MiB ingress cap或存储失败时可以保存完整raw。

验收包括fake live映射及algebra反例、全部232份已保存v3 origin raw逐阶段canonical model对应性、缺失/重复/外来assignment、term/引用/algebra/exact/flag/constraint错配，以及raw-before-guard失败窗口。保存origin的232份检查不作未来carry覆盖证明。

`native_export_coverage`、`resource_admission`、`scientific_acceptance`、`formal_result` 保持 false；没有产生新的 native 运行权限、封存包或 official verdict。

独立只读开发审查已闭合，无开放finding；测试及容量证据的精确范围见 results/tables/rq2_h1_saved_source_parent_v1_non_authoritative/development_checks.json。非official verdict或运行许可，以上开放边界保持。
