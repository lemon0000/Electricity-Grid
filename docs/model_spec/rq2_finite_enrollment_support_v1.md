# 有限登记的来源覆盖核对

2026-09-28，`DRAFT_NONAUTHORITATIVE`。用户已选择有限登记合同；本核对使用原参数建议中的
168小时登记、24小时follow-up、24小时stride作条件计算，不注册这些参数或权重。
实现 `enrollment_support_audit.py`；入口 `experiments/audit_rq2_enrollment_support_v1.py`。

## 来源与结果

从两个已绑定的公开边缘包重新读取小时行，重做既有continuation audit，要求chains与已保存SHA
及内容完全一致；同时核验原summary、config、builder和package pins。只在同一chain/split/seed
内寻找后续小时，两类来源保持各自时钟。RTS事故是模拟benchmark，workload不是实测功率。

每个已有168小时登记起点都保留，不按尾部可用性重新抽取192小时窗口。登记区间采用闭端点
[start,start+167]，所需最后观测为start+191；链末未覆盖部分逐窗口列出。

| split | 原登记配对全部保留 | 两侧均有24h后续来源 | 至少一侧缺后续来源 |
|---|---:|---:|---:|
| training | 14,644 | 14,040 | 604 |
| holdout | 14,336 | 13,743 | 593 |

training power登记523窗、完整尾部520窗；holdout为512/509。workload两split均为28/27。
缺尾部的分类分别是training：power-only81、workload-only520、两侧3；holdout：81、509、3。
所有1,091个边缘窗口的来源、登记末时、所需末时、实际末时和缺失小时均保存。

holdout raw workload>1的6个原始小时影响登记期10个窗口；将实际存在的follow-up也计入来源检查，
再增加1个仅follow-up超界的窗口，共11/28。源值不clip，也不删除这些窗口。
这里不批准整窗拒绝或任何风险评分规则；若采用原候选的全输入预验证，必须明确是否将检查范围
扩展到follow-up，不能沿用168h的10/28报告解释192h范围。

## 科学边界

以上是来源覆盖及映射障碍，既不是运行结果，也不是恢复成功率。即使缺尾部，登记cohort可能已
提前偿清；因此604/14644及593/14336不能自动作为未知履约质量下界。反之，尾部数据齐全仍可能
存在映射失败、未验证网侧动作或未按期恢复，不能算成功。跟踪的都是已有边缘，不是共同观测时钟
或经验联合分布。uniform product分数仅作为条件算术，未注册概率。

源行存在不等于normal/reference/actual dispatch已算出，也不等于允许未来信息。新normal覆盖、
输入揭示和follow-up物理动作仍需绑定；所有新义务继续入物理账，登记评分不递归扩成无限birth集合。
登记长度、期限、预算期/预算尺度、策略类和完整请求范围仍待自包含科学合同审阅。

## 验证

core含空支持、零follow-up、闭端点、不同来源时钟、跨split不得借尾部、重复/缺seed/重叠chain拒绝；
真实源集成测试独立枚举全部配对核对计数。新16项及旧source-window/continuation共56项通过3.08秒。
随后给原summary增加固定SHA入口，最终新16项通过0.48秒；全部窗口及summary与前次完全一致。
最终报告 `results/tables/rq2_finite_enrollment_support_v1_non_authoritative/coverage_168_24_verified.json`；
初步报告保留。代码、命令、报告及哈希见同目录 `development_checks.json`。
无solver调用、下载、正式结果或认证状态升级。
