# 168h/≤24h整链预算状态

当前计算出调用量并补齐候选的若干局部成本，完整整链资源预算尚未闭合。原科学合同E=168、F≤24、episode event cap=14和恢复/右删失规则不变。候选未接owner，下面条件路径不能当已实现节省。

| T192工作量 | 原owner路径 | 候选条件路径 |
|---|---:|---:|
| 独立historical Reader | 1546 | 1546 |
| Reader prefix-hour | 149380 | 149380 |
| parent遍历 | 3092 | 1546 |
| source Job replay | 597520 | 298760 |
| M5 stage replay | 2987600 | 1493800 |
| 条件M232 stage replay | 138624640 | 69312320 |
| 新增model dependency snapshots | 0 | 3092 |

每个候选snapshot还读取全部声明model source files、7个distribution版本及2个platform版本，并在其前后扫描guard；source/replay入口和post guard另计。JSON按当前源码计算这些子项，明确不是完整新增成本分解。重放不会生成对应次数的native solve；192个真实232-stage normal生产另有44544个stage slots，当前没有其整链实测。

本轮H1旧56.969790s、新28.378482s，H3新83.976012s。模型依赖检查的真实alias及模拟外部metadata返回值故障已测，两个H3 Reader各一次parent、metric为exact True。所有时间保留saved synthetic source/catalog/manifest seam，不含真实manifest来源重审，不能乘到T192。旧完整3h、hour0及两小时主体按原hash复用。

完整路径包括enrollment与genesis、ready/attempt/N生成、current join、共同Rref与各active Actual、intent/paired前fresh/outcome/post replay、phase terminal、按需缺源、checkpoint、close、fresh-process replay、报告及失败清理。T192至少576个operational events，旧cap32无法覆盖；三lane始终活跃时，仅ready/post的业务历史长度下界28311936。single-event/DB/holder、normal/Rref/Actual档案、保留失败、scratch/checkpoint/report/reserve/concurrency成本仍未知。

1900cell研究范围、2032个剩余planning arm-cells及既有解析排除继续复用；8020-node图无runtime request/causal key/solver task或solver reuse edge，不能折算native次数和资源节省。solver/license/真实规模、objective-blind pilot、同合同LB/UB与具名policy holdout、正式出版与seal/独立official review有各自依赖，见16门清单。

总wall、峰值RSS和storage准入仍为null，长连接不准入。现阶段先处理source路径的适用故障/依赖/确定性边界和完整成本，再为真实168h/≤24h连接形成具体预算；不依据局部时间顺延或启动长链。所有formal/native/resource/full192/seal/official状态为false。
