# 完整模型结构身份计算的等价优化

状态：DRAFT_NONAUTHORITATIVE。针对licensed H25完整赋值路径71.429665秒超过60秒门的开发缺口；不改变模型、数值/最优性验收或原生检查位置。

## 作用范围

新增 `grid_structure_fast.py`。结构字段、变量/约束/目标排序、父Block活动状态、linear standard repn、非线性拒绝、常数/系数/边界/fixed值的float.hex规则与旧continuous_grid_candidate._structure保持相同。只在单次调用内记住变量名称，避免同一变量在线性系数中重复生成名称；每次调用都会重新读取全部结构，不跨调用缓存名称、模型内容或摘要。tuple/list及primitive优先编码，其他类型回落旧_encode，JSON字节格式保持。

helper实现身份 `5a508864e2bde6ff30310ca6e1275fce17f5f7423999301357b40230fc239b71`，绑定自身与旧native/encoder源码。目前未接入任何native、normal或正式执行路径。

## 等价与失败检查

helper23项覆盖前后bounds/fixed/value、参数、domain、父块/约束/目标活动状态、sense、Unicode名称、跨调用rename、外部变量引用、非线性拒绝及原始编码字节。独立23项通过（1.44秒），另只读核对子类、dataclass、嵌套容器、负零与nonfinite的等价输出/异常。

fake-native20项在成功、timeout、缺失变量、错误目标/界/状态、options/结构/活动状态漂移、加载改变及无解等分支比较整个GridSolveEvidence，旧新逐字段相同（5.47秒）；仅pytest注入，没有真实solver调用。

probe初版独立pre-seal发现缺少runtime零solver guard、阶段前后构模依赖绑定、严格进程观测验证，均已补齐。补guard测试曾发现误用不存在的declared入口名称，已改为实际run_declared_normal。最终helper/probe/native组合87项通过（9.05秒）；之后新增preparation/model/encoding实际read_bytes漂移三项通过（4.37秒）。独立probe44项通过（5.48秒，在最后3项加入前）；三项finding闭合。测试为分组终态，不是单次90项统计。

## 预定H25无求解比较

runner `experiments/diagnose_rq2_grid_structure_fast_v1.py`，SHA256 `7a065e3399cfe06d3e86d69390652244d3eb40440e3eb29c3ac505c5a36ba8e2`。固定读取licensed声明及旧reader SHA，Windows Job120秒/768MiB；独占 `results/tables/rq2_grid_structure_fast_probe1_non_authoritative`。完整prepare和单次构模后按legacy/fast/fast/legacy顺序计算四次结构身份，每次必须为既有 `e18f8f95846b33f4c358fe8d2a47082660ea19f161e317ca672ccd657e3f40f0`，实际规模必须22275变量/28004约束。

child封锁所有登记的solver/normal/declared入口，写结果前要求forbidden_calls=0；task/source/model/preparation/normal execution五身份在阶段前后及父端读取前后重核。请求、launch、process、comparison由summary摘要交叉绑定。process必须对应真实启动pid/creation与pin、exit0/Job静默、配置commit limits、合法samples/peaks及非授权flags。

该单次比较已完成：四次结构身份均等于既有e18f摘要；legacy两次1.8339100/1.7887619秒，fast两次1.2879648/1.4330975秒。完整prepare31.9226241秒、单次build4.2906463秒；Job47.891秒、exit0且静默，commit峰475471872 bytes，solver calls=0。

这是相同模型、一次ABBA序列的局部耗时观察，不是独立重复样本或全链性能验证。此幅度不足以支持“完整normal约11.43秒超时已解除”的主张，最优性缺口也未改变。因此本helper暂保留为已验证开发产物，不立即机械后继整条执行链。

下一项优先处理完整输入身份编码：既有numeric probe的costs.json已记录numeric_input_identity_seconds=4.3547956、post_numeric_input_identity_seconds=4.2227902，而validation约0.00381秒、dependencies约0.01496秒。当前kernel在完整赋值路径多次重算完整输入身份；这说明编码是有证据的优化候选，但旧测量与本次不能直接相减。后继必须保留全部检查位置及原编码字节，不能缓存完整身份或跳过年度输入。

新118项证据索引为results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/grid_structure_fast_probe1_evidence.json，SHA256 fb1291f309030428ee9377c25d8593969188e55f31e51945faf33edcb574287b；另16个历史索引/829条旧证据已由root复核一致。helper、probe、三个测试文件及五个运行JSON均已绑定。本比较不改变normal/正式/安全/容量门。

独立只读结果审计已闭合：118项新证据及829条历史证据、五运行JSON交叉链、执行身份/进程/资源和四次结构身份/计时均复算一致，无开放实质finding。其结论限于本次局部观测，不构成official verdict或正式门授权。
