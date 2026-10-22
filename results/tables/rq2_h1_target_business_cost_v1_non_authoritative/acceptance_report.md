# 目标历史长度的业务组件成本

本轮补测原业务validator与编码成本，范围为v2 business-anchor参数覆盖下的一条synthetic JOINT history。实际BoundaryAnchor、capacity identity和provenance仍来自training fixture；没有source认证、grid witness、paired commit或episode terminal。前轮constructor修复与207/208绑定保留，16准备门不变。

cost_01为1 passed in 12.94s，外层14.515s。构建genesis→192的完整prepare/advance耗时9.773252s，包含嵌套cursor/record校验与progress写入。按固定代码，192次prepare入口_validate的history长度为0..191，总和18336；内部调用量未instrument。以下为构建后各目标的一次额外观测：

| business历史长度 | 原_validate，s | scientific编码，s / bytes | 完整carry编码，s / bytes |
|---|---:|---:|---:|
| 168 | 0.0799385 | 0.0595023 / 201670 | 0.0505224 / 1836367 |
| 192 | 0.0913091 | 0.0055492 / 230230 | 0.0603213 / 2118971 |

两点各一次、顺序固定，编码时间不提供分布、单调关系或全规模上界。完整carry编码包含原cursor/records，不能解释为owner event或持久档案大小；采样owned tree RSS173473792B，logical9202164B同时包括base/out、保留副本及runner artifacts，不能解释为组件持久化需求。原90s/30s进度/512MiB/32MiB额度内终态，无顺延。

实际保留carry逐字段核实f=.20、headroom=.10、eta=.85、duration4/event14/rest1/energy2.8/debt.20、response1及恢复12位；initial state的previous_call/duration/energy/debt/event_count全0、event flags为false、rest为None，ledger cohorts为空/last_hour0。D=.50、alpha=.50是benchmark输入，不是最优capacity结果。call_limit=1在192个实际encoded observations中核验；service_tolerance=1e-6由request绑定的boundary源码唯一literal及两个指定direct consumers（cfe_preallocation、capacity_policy_bidirectional）单独核实，并未另捕获历史runtime变量值或闭合全部runtime依赖。参数表复制本身不作为这些字段的证明。

只有一个cohort：business hour168借入17/1000，due192；h192输入source_cfe_at_alpha_one=0，对应renewable_share=1、compatible_surplus=1/2、effective CFE request=0。实际恢复1/50，eta×r=17/1000，剩余debt与due-hour snapshot均0。保留所有192个动作，逐项复算服务平衡、调用量q≤f×w及共享容量q+r≤D；恢复另受headroom/debt/CFE surplus约束。数量均为归一化机制输入/动作，不是电网调度或服务认证。

1306个live source pins在运行及after未变，显式tested-byte snapshots为14份；6份base JSON及副本逐字节SHA匹配。保存case465/owned444未变，观察PID/create-time对应进程均退出，0新normal Job/native。旧192h due fixture16.099025s及4/16/32h负结果按原hash复用；旧fixture与本参数覆盖不同，不作提速比较。

postcheck最初将encoded envelope tuple-pairs当dict，参数补核最初将encoded Fraction当字符串；两份失败源码/错误保留，仅修读取器并复核保存JSON，没有重跑科学诊断。独立只读pre-seal审查的限定见preseal_review_summary.json；它不签发official verdict或gate receipt。

初版DRAFT core/final及当时19份顶层文件保存在preseal_before_contract_fix。后验检查曾额外断言q+r≤f×w，该更强式碰巧在本点成立；现按既定合同分开核q≤f×w、q+r≤D，并显式补初始零态。此次修正不改变原worker/输入/保存科学payload，也未重跑cost_01；当前core/final另绑定修正后的检查与初版历史。

本次只把一个业务组件成本从unknown补为单次观测。整链仍包含源层二次prefix量、normal/Rref/Actual、业务ready/post重放、576 operational events/旧cap32、terminal/checkpoint/reopen、失败/档案/scratch/reserve等未闭合部分；一个cohort的参数点不能代表其他机制、更多cohort或lane。总wall/RSS/storage准入仍null，overall_performance_review_complete、long_connected_launch_admitted、formal/native/resource/full192/seal/official保持false。
