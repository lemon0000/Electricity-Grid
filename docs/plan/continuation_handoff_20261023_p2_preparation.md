# C：P2请求图与成本准备交接

2026-10-23，DRAFT_NONAUTHORITATIVE，目标“推进计划”继续active。接续[shadow v2](continuation_handoff_20261023_shadow_v2.md)，起始HEAD/origin为`b5809dcc27f45e11db2fb29f0b73859458d9e5c1`。本检查点发布状态以其后的远端readback和worktree为准。

## 本轮实质进展

[接线成本决定](staged_deliverability_c_candidate_integration_cost_decision_v1.md)明确：2547个实际digest caller中2254个原类getter与118个child直接旧别名不能靠局部facade替换；真正candidate-only需要版本化类型/registry/codec/policy/audit/journal身份。plain_v2保留为固定保存域等价候选，当前先准备原栈P2，不增加大型接线副本或修改旧科研栈。

[准备合同](staged_deliverability_c_p2_preparation_contract_v1.md)及新kernel/CLI固定on_time/early/full_temporal、h=-2..7，registration_end4/observation_end8。319槽=41 actual+278 contract（h1/2各139），160QP/159LP、12/159/148证据类别，完整成功1276构模/638import为结构上限。DAG包含串行前驱、父slot、carry、actual参考集合、actual_finished；后者仅循环完成，未来仍需finish→fresh。父完整point/economic KKT在BoundQuery之前。

309静态request SHA由原compiler逐槽重算，10动态actual request SHA及全部未来BoundQuery/父point/KKT SHA为空。prepare静态请求对象会计958=326+316+316，不能称查询数、槽数或实测数值工作。完整后续1431/4273和D/E范围未缩减。

唯一metadata CLI exit0，外wall6.760574s、准备主体5.059443s。`results/tables/staged_rts24_p2_packet_v1_non_authoritative/packet_01`仅三文件505285B，55源/40 application modules/74 functions/20类/211 stdlib绑定及完整module库存首尾核对；warmup只新增email两模块。没有P2执行目录、科学构模/native/journal writer或replay。native_authorized/execution_supported/resource_admission/formal_result均false；没有seal/official receipt。

38项最终普通针对性检查通过（22.05s），六源保持；相关冻结回归60 passed/1 failed（旧测试要求已完成P1目录尚不存在）。独立新进程已确认该测试之前的三组preservation断言和无psutil import均成立；失败日志及原测试保留，不称全组通过。PRE_SEAL实现/领域只读审阅无剩余High/Medium。

[报告](../../results/tables/staged_rts24_p2_packet_v1_non_authoritative/validation_report.md)和[后核验](../../results/tables/staged_rts24_p2_packet_v1_non_authoritative/postcheck_01/postcheck.py)记录最终packet_03 exit0：独立边/事故ID/计数/文件核对，160个runtime文件；原P1683文件2950863B、B1–B3118、685旧路径和前四次发布196路径保持。四份原stdlib postcheck stdout精确复现；后核验两次草稿错误、初轮单位检查失败与相关历史测试失败共同保留。

## 下一工作与约束

下一步为具体P2 controller/provider/point-worker/fresh无原生开发及失败语义验证，保留原科学类型与验收；原P1硬编码31点cap、worker/注册路径不得直接承接319点。先补完整DAG性能与昂贵失败审查、十小时writer/保存/关闭/fresh增长，再确定有依据的有界测量包与独立审查。当前准备包不能直接执行，不应据此请求批准一个尚未实现的P2运行。

3600s package/10s point/5s solver、1GiB RSS/Job2GiB、64MiB/8192文件等均为拟议停止帽，未准入、非ETA。原P1 point wall96.902s与native内部0.0856292s为分解依据，差值不全是启动，inclusive时段不相加。没有P2性能测量或RAM采样。原P1唯一native授权已用；没有新P2/D/E/native或长实验授权。

主范围仍RTS-24，两母线为机制回归。P1五小时仍missing_input/coveragefalse、method/full双null；本次十小时只是请求准备，没有补齐观察结局、139数值或F/X时序。C整体性能、STAGE现实输入与D/E快慢×工程×三方法、选择/平局/敏感性/时域、独立留出来源/split/seed/reveal仍OPEN。

恢复先读AGENTS、agent第7–9节、本页、C计划与blocker并刷新Git/进程。root唯一writer，子代理只读且不分叉；保护B1–B3、P1、两轮shadow及全部历史/失败工件。复用已闭合证据，只补未覆盖项；按精确NUL范围、raw bytes/index、远端hash和clean worktree同步。
