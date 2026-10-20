# 事故持续、修复与缺输入整链：启动前性能审查

2026-10-20，R3 DRAFT_NONAUTHORITATIVE。root为唯一writer；独立只读PRE_SEAL复核。既有v2 owner/source/history及旧测试源码、旧结果保持原字节；新增两份toy fixture/test及本结果包。全部native/formal/resource门保持false。

本包固定3个模拟小时，不更改168h enrollment及至多24h follow-up合同。N有两台committable机组：G1 min10/max30、ramp24MW/h=.4MW/min、成本斜率1；G2 min10/max40、ramp60MW/h、成本斜率2，启停成本0。负荷20MW、DC基线25MW。N初态两机off/0，h0两startup=1，N恒为G1=30/G2=15；正常阶段5个锁为60/1/1/30/15。5是该toy的完整阶段inventory，既有数值验收限不变。

h0左边界G1已在事故中、onset unknown，h1继续同一已披露事故，h2空overlay表示观测修复。事故只进入selector overlay，不改变N base availability。修复首小时cap=min(Pmax,60*ramp)=24，只在h2出现。Rref h0/h1供20MW、request5MW；h2供25MW、request0。修复时Rref为24+21，网络Actual为24+32.76470588225，Joint为24+36，G1 cap binding。

三个业务lane共用w=.1，alpha=.5/f=.5/headroom=.1；CFE源为.6/.6/.2。h0三个lane配对；h1仅CFE Actual stage0注入带feasible incumbent的fake timeout，其business/actual carry均不提交而停止该lane，其余两lane继续；h2跳过CFE，Joint r=.06/debt=.029，Network r=.047058823529/debt=7/20000000000000，CFE仅保留h0 debt=.02。timeout始终记actual_unresolved，不解释为数学不可行。

成功前缀后尝试h3：输入实际只含0..2，owner先持久化attempt，normal在load_pinned_current缺源拒绝。要求无Job/clock/obligation/parent hour003新项，原三个normal terminal/head保持，0额外selector；旧3outcomes/7paired lane-hours保留。关闭全部handles/leases后取文件SHA，重开constructor完整重放，再显式public inspect取得pending_attempt=true、hour3与continuation=false。这里的缺输入发生于enrollment，不冒充正式follow-up右删失指标。

完整DAG：toy source/registry → 0Job kernel oracle → fresh N0 fake Windows Job → owner genesis batch → 每小时ready batch →（h>0先durable attempt/原normal Job）→ 独立current/共同Rref/各active Actual → intent/ticket/原transition → paired前第二独立current → outcome/ticket → 完整replay → h3 missing ready batch/attempt/source rejection → 全close/快照 → owner constructor batch/原FSM → 显式public inspect → 独立historical与parent snapshot → close/保存SHA/报告。

复用与优化：不重跑旧chain07、旧06或batch connected_01；保留已验批量重放。三个Actual串行，同小时current共享但各carry独立。原test-only15个静态身份memo复用，逐键原函数bookend；current/source/历史/业务/数值不缓存。旧guard按同代码证据复用。新增验证聚焦新输入、5阶段normal候选、共同Rref、cap超限拒绝、CFE timeout/其余lane继续、缺源停止和read-only pending重放。

计数：3 normal Jobs/15 normal stages；selector 13+11+10=34，timeout恰为总capture index17。owner源层原3h成功前缀+一次reopen为API28/weight52；缺源ready额外API2/weight6，重开后显式public inspect再加API2/weight6。因此本包API32/prefix-hour64、parent inspect64/weight128。额外public inspect是为读取构造器未对外保存的pending报告并验证只读行为；独立historical/snapshot/anchor及normal内部重放另计。

先units_01：120s/0新Job/native，3个normal小时各5模型的残差/边界/整数及锁校验；3h原业务+selector oracle含34假capture、repair cap+1MW拒绝；缺h3源拒绝。unit仅为科学一致性和成本证据，不代表完整owner链。之后根据实际kernel和独立PRE_SEAL findings再决定fresh connected_01。

有界完整诊断预预算：1500s总wall；每Job240s固定上限（相对旧1机3stage的180s，新增2机5stage，独立新fixture规模预算）；正常option TimeLimit5s固定、selector原TimeLimit不变；树RSS1GiB、logical128MiB、5s监测、120s无进展。旧2h/1机outer509.516s；当前历史API权重64相对28且模型增加为两机，另有第三Job、失败及postcheck，估计总约900–1400s，尚未经本新路径实测。此估计只授权本诊断的停止设置，不能作为生产预算。若关键kernel证据不通过或仍有阻断finding，不启动完整诊断。超限停止owned进程保留全部原件，绝不运行中顺延。

每次request保存actual code/config/inputs/spec/本计划和依赖SHA与tested_bytes，记录Python环境、PID及source末端SHA；所有失败保留。整个3h观察、toy完整链、full168+24、正式结果与native authority分别报告。正式真实RTS、生产整体预算、writer重建、持久atomic-live认证、seal/official review仍OPEN。

units_01终态exit1：3项normal候选检查通过，oracle读取timeout时测试误用不存在的raw termination键，实际schema为solver_records；没有Job/native，外层16.203s、source unchanged、观察PID退出、句柄关闭。仅按原schema修正断言，并补逐阶段物理dispatch oracle，保存失败原件。units_02仍固定120s，同范围0Job验证。

units_02终态exit1：3项normal候选通过，实际h2 Rref被原物理审计拒绝。原因是fake误把G1变量ub30当作repair cap；原24MW限额在actual_ramp约束中，拒绝正确。仅修toy fake选择的有效上限min(ub,CAP)，不更改任何物理约束/数值限；追加0/40、0/35及repair24/21、24/33.5、24/32.76470588225逐stage断言、onset unknown与base availability不变断言。units_03仍120s/0Job固定范围。

units_03终态exit1：normal三候选通过，h2原business产生Joint恢复.06，测试误加q+r<=f*w=.05断言而失败。冻结spec lines55-59明确q受f*w；恢复在有效调用为零时取D/power/headroom/适用surplus/debtη之min；总q+r<=D。因此修正测试预期为q<=.05、q+r<=.5、r<=.09 headroom及适用CFE surplus，Joint r=.06/debt29/1000/Actual40MW（G1=24,G2=36）。这纠正未登记的测试假设，原科学代码、冻结配置和验收阈值全部不改。Network恢复与7/20000000000000残债保持原推导。失败原件保留；units_04仍固定120s/0Job。
