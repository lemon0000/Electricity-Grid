# 保存结构只读核算

一次静态核算exit0。固定旧completion SHA后逐字节核531/558007B与138/286322B核心文件；四个分析源码SHA与已保存runtime map相同，677个唯一输入首尾一致。没有模型、策略、replay、solver或新数值点；成功逻辑读取1354次，具体bytes与source pins见[report.json](report.json)。这不是新性能测量或物理磁盘I/O。

| 位置 | keys | CAS bytes | entry bytes | state bytes | records / cohorts |
|---|---:|---:|---:|---:|---:|
| genesis | 3 | 4989 | 5902 | 1223 | 0 / 0 |
| hour0 | 27 | 23789 | 2450 | 2350 | 1 / 0 |
| hour1 | 56 | 47671 | 4538 | 3662 | 2 / 1 |
| terminal | 57 | 49467 | 4614 | 3662（复用） | 2 / 1 |

最终root17504B。按已绑定源码对两hour+terminal计算的CAS inventory读取子项879514B、root inventory加_check内读取子项273966B；不含genesis创建、fresh、publish/get/readback、runtime、其他case与报告。不得与原probe总read counter比较为提速。

分层增长及优化见[成本审查](../../../../docs/plan/staged_deliverability_c_retained_cost_review_v1.md)。累计key/state物化量可能二次，writer全量扫描累计读取可三次；当前两小时解析保存形状不能推公共wall或C/D/E资源。无剩余静态核算finding不构成official审查、seal、native授权或formal结论。
