# 跨小时2h合成前缀的只读复核记录

状态：DRAFT_NONAUTHORITATIVE。本文件由唯一writer整理只读`/root/source_factory_preseal_audit`的PRE_SEAL findings及修补证据；不是official verdict、review receipt或运行授权。

该独立复核在本2h synthetic scope内未发现阻断性未闭合finding。绑定代码、测试、fixture、预算和终态均可从[connected_06/request.json](connected_06/request.json)及其`tested_bytes`读取。

| 复核问题 | 直接证据及处置 |
|---|---|
| 活锁文件导致快照失败 | 初次owner/holder/normal全部close，核原stream.closed及lease.stream=None/locked=false后才取全文件快照；重开核验后再次close才比较。成功result及独立重算覆盖212个文件，其中12个execution.lock均为byte `0` |
| 省略第二次inspect是否减弱重开 | 父constructor动态调用self.inspect，确实执行successor完整_restore并填last_candidate_state；直接比较其产物。read-only推进拒绝另有负例，head与next source不变 |
| 三个新增静态memo的边界 | followup implementation/contract与ticket-holder implementation分别调用185/76/491次；全部15个target的original均恢复、bookend一致、errors0。协议config/spec被request/快照/结束SHA绑定；dynamic assess、ticket读取、source/history/carry不缓存 |
| 完整两小时终态 | pytest1passed600.372s、outer604.266s，exit0/reason null；6观察PID退出、monitor/cleanup/remaining均0；raw Job PID10640/33732不同且exit0/quiescent |
| 业务数学和carry | CFE/Joint q0=1/50，r1=5882352941/250000000000，debt=3/5000000000000；network q=r=0；每条q+r≤1/20。各分支hour1 before_actual/business等于hour0 after_actual/business；2个outcome覆盖6 lane-hour |
| 规模推导 | owner触发的fresh为T²+5T+2；一层prefix-hour权重公式独立沿代码核对。另计historical postcheck、parent snapshot及episode终结；不是实际文件访问或完整实验预算 |

复核指出一项不阻断06自身结论的metadata缺口：原补验记录了04/05的科学projection SHA，但没有绑定对照SQLite的文件SHA。已新增[baseline_projection_bindings.json](baseline_projection_bindings.json)，保存04/05/06数据库绝对路径、文件SHA、对应request/terminal SHA、原退出状态和仅已完成hour的projection；每份数据库读前/读后SHA相等。04只比较已完成hour0，05/06比较两hour；原失败终态未改。该比较为supplemental regression，独立来源鉴真仍为false。

只读reviewer随后独立重算伴随记录、三份数据库及request/terminal SHA，并重新查询完成outcome列表，确认此metadata缺口已闭合、无新增finding。没有重跑Job或修改原result/postcheck。

必须保留的边界：2小时、3lane、零Rref请求、synthetic source/catalog/normal binding和fake solver；raw Job numerical_evidence_verified及whole_task_resources_verified均false，完整未观察进程树证明false。192h、正网络调用、事故延续/修复、phase边界/右删失/episode终结、真实RTS/native、writer rehydration、持久atomic-live认证、生产预算与formal均未由本包证明。旧Common/source-factory未闭合findings不在本次已验证调用路径内。
