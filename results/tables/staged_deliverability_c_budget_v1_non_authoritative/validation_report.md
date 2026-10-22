# C公共整链预算的机械对账

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL。按[核算合同](../../../docs/plan/staged_deliverability_c_workflow_budget_reconciliation_v1.md)仅执行一次纯元数据CLI，exit0。未启动P1、数值编译器、模型、writer/reopen或native；源代码、保存JSON与SHA被读取，科学对象没有重建。

## 保存核验

[audit.json](audit_01/audit.json)为167614B，SHA `0644a06315612eaab1cf855be437d230a919fb8af64b742aeb07e52df13e26bd`。677个不同输入，1364次逻辑读取、8147368B，metadata处理wall1.0996074s；上限1800次/12MiB/20s和单文件2MiB均未超。该wall从Reader创建到结果形成，排除解释器启动、结果JSON编码和落盘，不是公共实验耗时。

输入包括原P1注册及13源、28个runtime source entries、既有network_frames、saved-cost checkpoint/五源及626个结果文件，并绑定本轮工具/测试/合同三源。入口SHA固定，全部读取后逐文件bookend。没有在本轮重校验应用二进制或环境性能，environment_revalidated=false；metadata解释器的版本、路径、argv和flags另存。

[独立postcheck](postcheck.py)不导入核算工具或科学模块，以显式前缀展开重算访问；两遍复核全部677个input pin，核24个不同普通检查及保存日志，并将原audit SHA再次bookend。[verification_01.json](verification_01.json)exit0，自身处理1.0215999s；这一后处理时间也不是代表性性能成本。

## 静态执行会计

P1条件满成功路径的结果如下；**本轮实际科学编译次数仍为零**。

| 范围 | selective calls/描述 | full calls/描述 | numeric及Pyomo编译 | import |
|---|---:|---:|---:|---:|
| 包含已完成的原注册准备 | 185 / 583 | 8 / 1140 | 124 | 62 |
| 未来执行命令部分 | 180 / 567 | 6 / 855 | 124 | 62 |
| 其中worker | 120 / 378 | 4 / 570 | 62 | 31 |
| 其中31个point child | 0 | 0 | 62 | 31 |
| 其中独立fresh | 55 / 173 | 0 | 0 | 0 |

writer+finish、worker本地reopen、独立fresh各55/173。两次reopen必须分别计入；五小时的重复selective访问权重为[55,46,37,28,19]。52次audit_execution处理135条历史row，另有131次fingerprints和5次preserve（包含原注册准备）。31是native尝试槽，124来自四次compile/point；不等于31次模型构建。33个逻辑child launch不决定实际Job成员数。

这些数以所有必要祖先成功、无策略提前停止为条件；失败保留真实较少工作，不能填齐预期。嵌套数值审计、梯度/行活动/父点KKT、cohort/Fraction、完整prior摘要、fingerprints二进制读取、CAS inventory/_get/pack/fsync、日志/终态及OS工作尚未逐子函数穷举，也未测公共wall。不能把未测层填零或宣称整体性能审查完成。

公共包上限由实际路径与合同层分别加总：

| 声明包 | actual | 合同层 | 总数 | QP / LP |
|---|---:|---:|---:|---:|
| 三方法actual代表单元 | 21+41+41 | 单列 | 103 | 按各角色另列 |
| P2：full十小时、两合同frame | 41 | 278 | 319 | 160 / 159 |
| 单方法十小时、各小时完整合同 | 41 | 1390 | 1431 | 720 / 711 |
| 三方法十小时、各小时完整合同 | 103 | 4170 | 4273 | 2160 / 2113 |

这些未来包没有已实现的对应完整runtime，wall、D点数、E留出数及总资源均为null；原包与权限未改。

## 保存观察与论文义务

既有保存观测单列进入账本：三母线h0/h1、三方法v2→v3固定顺序，共198/548；测量外部156.945949s、guard130.984s、后处理23.037932s，完整测量树579文件1660401B，采样worker树RSS298913792B。最终group ledger取worker_timing（包含saved_report），不能用报告生成中尚未收尾的snapshot替代。计时范围、单次顺序偏差与公共网络/更长前缀差异保持；不将该值相加到P1预算或推断提速优势。

论文继续并列实际轨迹、完整F/X网络、一小时业务必要条件、完整F/X时序四层。预先固定路径的条件实际比较不要求aggregate_contract_release先变为true；其自身公共数值、完整观察、预算与运行权仍要满足。正面69态静态DC合同结论需要139节点覆盖；完整跨时合同结论还需反事实任务/事件、恢复/期限和预算，139本身不够。旧失败与false保持，不因条件实际轨迹通过而被覆盖。

D/E仍保留业务快慢达产×电网按期/延期×三方法及必要敏感性；当前一个业务形状或103点代表单元不能改名为完整D。E在计划、容量、策略冻结后才揭示独立输入。现阶段只完成义务与成本账本，不登记或启动D/E。

启动前24个不同普通检查均通过：首轮21，后续新增wall、公共包caps、最终worker timing组合各1；重跑8项和2项不重复计数。五轮终态日志、命令、source pins和PRE_SEAL findings见[开发记录](development_checks_01/development_checks.json)。没有失败测试或新scientific candidate，没有official verdict、seal或receipt。

B1–B3、batch、saved-cost及P1绑定保持；preservation_before与完成后的preservation_after均exit0，118个B1–B3文件、731个历史文件、batch/P1与cost源未漂移。P1注册SHA仍为`23577e5d79d3284a260decbfe2258a3103252617953452565a9feeffafbd94e2`，p1_01不存在，专项授权仍待答复。C整体性能、完整F/X时序与D/E资源门均OPEN。
