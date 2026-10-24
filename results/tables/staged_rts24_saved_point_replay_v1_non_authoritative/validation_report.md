# 单点保存raw科学重建检查点

2026-10-24，DRAFT_NONAUTHORITATIVE。遵循[科学采用DAG](../../../docs/plan/staged_deliverability_c_scientific_adoption_dag_v1.md)及[单点合同](../../../docs/plan/staged_deliverability_c_saved_point_replay_contract_v1.md)。本轮只实现DAG节点C的独立读取组件；原七输入、outer/checker/guard/parent、数值接口、codec/journal和B1–B3/P1保持原字节。

## 交付与科学范围

[saved point replay v1](../../../src/staged_rts24_saved_point_replay_v1.py)先验完整outer quiet，再以调用方持有的完整query、frame、point库存和选定源为锚。完整typed CAS、raw/log/result/process关联、独立compile、原snapshot/import（第二次compile）、原代数审计和精确typed evidence SHA形成单点链；完成CAS、双库存、source及调用方预期书挡后才返回。三族为经济QP KKT、child LP KKT、anchored经济primal-only；不允许选择较弱证据族。numeric未决只在原异常逐字复现且无evidence时单列，不能推数学不可行。

实际加载的20个src模块都核路径/字节，选定来源共23文件。raw成功字段及numeric可选诊断、API事件、observer五字段/scope/counter-time闭合；P2必须有注册SHA。网格形状按冻结case核为24 buses/33 generators/38 branches；32个QP二次项不等于33个发电机条目。完整query外部来源、动态actual/前缀、legal-X、journal/fresh及整包采用仍由后续节点负责，返回的global adoption/139/F-X/resource/formal均false。

原monitor对point调用扫描的是整个package，P1 point0001保存terminal为27文件/166782B，而当前该point去除process.json只有13文件/66243B。因此本组件校验原自报帽及“package counters覆盖local必要库存”下界，明确full_historical_package_storage_reconciled=false；不把local当作历史整包总量。

## 已运行检查

最终同一四来源pins下，`units_08`为47项针对性检查，`related_02`为170项原数值接口、FakeApi backend、child KKT和开发模型回归，全部exit0、无超时、首尾pins相同。collection核217个不同node，两个组无重叠。无新solver/native、P2、完整journal运行或长实验。

解析小例的primal/dual独立给定，raw手工构造；保存evidence采用原writer会产生的importer精确表示。测试覆盖三族、每成功点恰两次构模、numeric warning/time/no-dual、primal-only不采用无效dual数组、signed-zero值相等但typed SHA不同、伪造自洽raw/log/CAS/authority/frame/来源、超范围网格/资源前置拒绝、全库存漂移、未知quiet零读取，以及失败但quiet的包仅作局部诊断。

P1回归从冻结fixture与reference_requests独立构造h=-2的root query；再使用新重建root的point/economic构造两条recovery query。原point0001/0002/0003分别重建经济、恢复下界、恢复上界证据，其typed根SHA逐一等于原保存值；原683文件在该测试首尾逐字节核对不变。没有从当前point CAS反推预期query，也没有启动新的native。该三点不代表五小时业务/完整319/139的科学采用。

## 调用量与保留失败

独立计数单测观测成功M=6对象：source86读、point52读、direct pack5；warning M=3：source86、point34、pack3。对应公式source=2×(23＋20)=86、point=6M＋16，成功pack5/numeric3。319点仅source逻辑读取为27434；成功新增638构模/319 import，和旧point路径相加为条件1914/957，其他未来路径另计。均为直接调用/逻辑内容次数，不是OS读量、wall/RAM/storage上界或提速结论。

保留失败：`units_01`严格CAS门拒绝手写证据与importer的signed-zero表示差异；fixture改存原writer导入表示且独立比对数值，没有放宽SHA。`units_03`的oversize反例因重复bus index在构造时被旧schema先拒绝，后修成独立有效索引；`saved_01`暴露初始32-generator规模声明错误，在构模前拒绝原33-generator case，随后只修开发形状门。所有失败与中间终态原样保存。PRE_SEAL五项finding（整包/局部会计口径、loaded来源、闭合字段、P2注册和规范log path）已闭合，无official verdict/receipt/seal。

## 保持与下一步

标准库postcheck核672个旧发布路径、三导航完整旧正文和旧stdout原字节；P1/B1–B3/685及原双记录上界证据复现保持。新版未接入旧outer注册或改写旧source组。

下一步优先B：用独立政策和已接受state串联参考/恢复/actual预期query，再接C逐点raw重建；D的firm/legal-X对照、E的trusted journal政策/余额/期限重放和F的fresh/最终发布仍单列。P2实际319数据尚未生成，C整体、139/F-X、D/E现实输入/方案/选择/敏感性/留出与完整资源准入均OPEN。fresh60s＋最多5s收束相对65s无进展帽仍没有父端余量；不由本轮单点测试扩展运行权限或预算。
