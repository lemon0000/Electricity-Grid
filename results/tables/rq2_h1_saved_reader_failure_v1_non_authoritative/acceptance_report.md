# 保存 Reader 故障组合与整链预算 v8

本包完成 source v3 的9个枚举保存M5单Reader故障的组合验证，取得真实部分构造实例、inner/outer清理和恢复证据。结果为 DRAFT_NONAUTHORITATIVE / PRE_SEAL 开发证据。既有 owner 尚未接入 source v3，全部16个正式准备门仍 OPEN，整体性能审查和资源准入尚未完成。

## 故障验证结果

原 `suite_01` 前8项 accepted，第9项在总240s watchdog的下一采样点停止；suite=241.344s、该case=34.782s，含清理外层241.812s，exit1。第9项当时没有 worker terminal；其 FileNotFoundError 是外层读取缺失终态的次生归档错误，不是目标故障拒绝证据。原attempt完整保留。

根据已完成H1后期故障47.093/44.891s实测，单独登记尚未验证的一项，固定总90s及原单例90s。`remaining_01` 用完全相同的worker字节，只运行该项，外层47.125s、case46.796s、worker42.670941s，exit0。未延长或改写原suite，未重跑前8项。

| 枚举故障 | accepted证据来源 | 完成numeric prefix-hours | 实际Job/stage inspections | 外层case秒 |
|---|---|---:|---:|---:|
| constructor primary | suite_01/01 | 0 | 0 / 0 | 8.187 |
| constructor parent close alias | suite_01/02 | 0 | 0 / 0 | 6.110 |
| constructor parent close code | suite_01/03 | 0 | 0 / 0 | 6.125 |
| constructor helper alias | suite_01/04 | 0 | 0 / 0 | 6.156 |
| constructor Path.read_bytes alias | suite_01/05 | 0 | 0 / 0 | 6.125 |
| post-constructor primary | suite_01/06 | 1 | 2 / 10 | 47.093 |
| final actual sharing read error | suite_01/07 | 1 | 2 / 10 | 44.891 |
| unselected hour0 packet drift, H2 selected=(1,) | suite_01/08 | 2 | 4 / 20 | 81.843 |
| third namespace round / seventh root | remaining_01/01 | 1 | 2 / 10 | 46.796 |

9个accepted cases合计观察到5个正常_after返回、10次保存Job检查、50次M5 stage检查；原被终止case的实际调用数未知，不补写为0。两attempt已花外层时间合计288.937s，不是生产预算上界。sampled tree RSS分别197,337,088B和203,472,896B，不相加；逻辑输出采样峰值分别1,471,840B和1,207,819B，不代表全部物理落盘或RSS瞬时上界。

每项均检查原真实Reader的3个inner及4个outer ReadViews，frozen parent实际调用，journal→anchor→root_lease及outer3→0顺序，closed flags、owner fields=None、capture sentinel，以及captured/all_packets/seen_hours三种显式容器。没有据此宣称其他所有局部容器清空、writer锁释放或任意内存资源释放；ReadViews是identity observations。

真实sharing项使用只读CreateFileW/share0/OPEN_EXISTING，原生冲突码32，原文件读取得到PermissionError(errno13)。CloseHandle成功后文件identity及SHA相同。packet项是内存反射，原normal_h1_source.validate_current拒绝未选中hour0的input drift。namespace项是第三轮_names返回值seam，原_inventory拒绝额外名称，磁盘未创建名称。三种机制分别记录，不能合称完整真实文件系统并发覆盖。

保留独立trace/profile：trace callback抛异常会停用trace，profile仍观察随后cleanup。未引入合并observer。每项要求injection_count=1、预期错误路径、空instrumentation/cleanup errors、hooks恢复、原guard恢复和465保存文件SHA相同。原suite2492启动pins、补验2584启动pins及上游2483绑定均fresh复核。只读reviewer逐项核对后没有新的具体finding；这不是official verdict或receipt。

支撑测试 `support_04` 为16 passed / 0.30s，外层0.789498s，6份前后源快照一致。该测试包括Windows临时只读共享行为、AST landmark唯一性、observer错误留存及实际接受函数的10种缺证拒绝。原source v3的294项unit/回归及H3双Reader成功证据按旧2483绑定复用，本轮没有重跑它们。全部本轮路径均为0新normal Job、0 selector、0 real native solver；sharing项确实调用非求解器Win32文件API。

## 预算与已有M232证据

`whole_workflow_budget_v8.json` 保留v7的完整已知调用量，没有复用折扣或owner切换。T192 clean terminal / W=0路径仍为773 batches、1546 Readers、149380 Reader-prefix-hour权重。现owner基线597520次保存Job重放；若每小时232 stage，相应138624640次stage检查。未采用的source v3结构条件数为298760次保存Job及69312320次M232 stage检查；新增all-H/digest/model/namespace/guard成本仍计入。它们都是静态工作单元，不是本次runtime counters或native solve数。

clean T192 paired路径575个事件，额外episode_terminal调用增加1，共576；此数要求assessment.needs_next_hour=false、无额外witness/failure路径。业务事件cap14与owner运行事件数量不同，旧toy cap32不能覆盖该路径。未知witness和失败分支不能由这个clean路径数量封顶。

`saved_M232_evidence_reuse_v1.json` fresh核对旧单小时校准251文件 / 20,938,085逻辑字节，并复核已有resource、shape报告引用。旧校准记录232 native reports、Job2744.984s、peak total commit269524992B，但没有独立非求解器耗时、完整资源准入、native execution authentication或optimality certification。这里不新增native调用，也不重新解释历史结论。

已有zero-solver shape只测stage0与231两个端点，其placeholder locks未验证科学provenance；不能把两次建模耗时当232 stages总成本。已有producer shape还保留future boundary反例：1272 constraints超过旧origin1211，且不是可达科学见证。它们不能证明当前source v3的M232 Reader、H192全packet retention、future carry或namespace范围。未读取SQLite replay，未运行模型或Reader。

## 仍需完成的工作

下一步先以这些已保存资料固定M232/source-v3适用性和全packet retention的有界诊断，核对source双Reader失败窗口及owner接线的净成本，再推进真实E168/F≤24边界和episode终结连接。原hour-0/两小时/三小时主体、target业务参数overlay及旧失败资料继续复用。缺少前驱或所需follow-up source时保留unresolved/right-censoring，不补造future carry。

当前总wall/RSS/storage准入值仍为null；完整native producers、Rref/Actual、owner业务历史与序列化、失败/terminal/reopen、物理SQLite/FS、task/reuse DAG、LB/UB与封存审查等未闭合。科学合同、冻结config、现owner及canonical plan/blocker原字节保持。本包不授权新长链、正式实验或native校准。

入口：[整链预算v8](whole_workflow_budget_v8.json)、[准备状态v8](formal_preparation_state_v8.json)、[组合核对](combination_postcheck.json)、[续接文件](continuation_handoff_20261021.md)。
