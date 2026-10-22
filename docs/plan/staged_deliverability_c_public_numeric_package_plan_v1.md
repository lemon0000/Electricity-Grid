# C公共数值证据包与调用预算

2026-10-23，`DRAFT_NONAUTHORITATIVE`设计。用户已选RTS-24公共方向；[纯数值接口](staged_deliverability_c_numeric_interface_contract_v1.md)和[保存成本审查](staged_deliverability_c_retained_cost_review_v1.md)是已开发前置。以下为后续实现/预算顺序，尚无highspy执行适配器、受控runner或可启动合同，不能启动native、seal或主比较。

## 数值后端与完整DAG

保留现有Pyomo连续DC模型、1e-8经济正则项、F/X、RATE_A、同小时0.5Pmax corrective和独立审计。新的纯接口导出规范化min式LP/凸对角QP；未来highspy适配器必须固定版本/入口与二进制SHA、问题schema/transport SHA、原行列顺序、选项和状态。None界机械映射±inf，全部列continuous，目标offset保持，Hessian采用0.5*x'H*x（对角=原多项式系数两倍）；返回消元后A*x、完整col/row value/dual、objective、enum.name状态、valid flags、迭代/时间和原生残差。不得默认Pyomo highs/appsi接口已提供QP完整dual。

完整路径按以下依赖登记，数值点失败停止其所有后继：

1. 源/环境/输入SHA及旧工件bookend→fixture/工程前后frame→机械请求角色/小时/父request identity与总call cap。
2. 合同层：该小时normal C经济根→完整primal/EconomicEvidence/KKT→每个选定事故F点与完整C raw最小削减/ChildLpEvidence→合法X条件审核。69事故是互斥枚举，不合成实际事件预算。
3. 实际轨迹层：从真实first_hour=-2的零债务/预算声明起，逐小时P0经济根→当期实际故障raw（如有）及两恢复端点→prepare/固定策略→已选actual P请求→原生完整点与独立审计→连续ledger/carry→CAS/journal发布读回后采用。
4. 缺数值/dual或失败：保留raw snapshot、状态、成功祖先、当前未接受输入、stdout/stderr及pending/orphan；不以占位父点续算，不将求解失败变成业务拒绝，也不推断数学不可行。
5. finish保持原观察末端8与未决/右删失→可信head/count/state/key集合→关闭→顺序fresh只读replay（0新solve）→完整科学状态/summary/audit对照→源/旧工件末核→资源/调用/文件报告和稳定终态。

child BoundQuery SHA依赖父完整点/KKT；actual SHA还依赖已经选出的P，运行前只能冻结角色、请求规则和上限，不能填造这些未来身份。主/留出、方法、clean、小时、工程和F/X不同的查询当前不跨身份借点。

## 逐包计数与停止

下表是假定所有必要祖先成功、实际策略未提前停止时的**请求上限**，不是实测solve或已经获准的规模。

| 包 | 实际轨迹 | 合同层 | 总请求上限 | QP / LP |
|---|---:|---:|---:|---:|
| P1代表校准：on_time/early/full，h=-2..2 | P0 5 + raw 1 + recovery 10 + actual 5 = 21 | h=1/2各normal C及最低索引branch、generator的F/raw，共10 | 31 | 16 / 15 |
| P2单路径公共整合：同路径h=-2..7 | 41 | h=1/2各完整139 = 278 | 319 | 160 / 159 |
| 单方法十小时每小时完整合同 | 41 | 10×139=1390 | 1431 | 720 / 711 |
| 三方法十小时每小时完整合同 | instantaneous 21 + fixed 41 + full 41 = 103 | 3×10×139=4170 | 4273 | 2160 / 2113 |

P1的合同层为两个normal、四个firm和四个raw；实际层QP为P0/actual各5，LP为raw1/两端10。P1仅作真实后端、支路/机组故障、工程投运及保存路径代表校准，终态仍是缺后续输入，不能代替P2、完整139或三方法。P2的证据上限为经济KKT 12、child LP KKT 159、firm/actual point-only 148；两帧合同也不是十小时完整合同。发生已知策略停止或任何必要数值未决时，实际计数更少并报告package incomplete，不改节点来凑齐计划。

## 资源证据与启动条件

真实后端的单点导入、QP/LP、dual、失败收尾与公共journal成本未测，不能用解析probe或普通测试wall估计P1/P2。P1后续runner拟固定串行、1线程、presolve=off、零重试，原生单点time limit 5秒、点子进程10秒、总wall 300秒、无进展30秒、进程树1GiB、输出64MiB/5000文件；这些是待核验的安全停止上限，**不是预计时长或资源准入**。须实现外部watchdog及所有权明确的child退出/终态保存，才能登记可运行的exact包；不通过就保留失败，不顺延。

P1自身全路径注册、native适配器/runner普通测试、独立PRE_SEAL审查及用户专项授权必须先满足。P2及D/E点数再依据代表实测、合法复用、保存增长和完整预算确定，不能自动继承P1权限或把319/4273线性乘单点时间。当前C整体性能、完整F/X反事实任务时序、D/E资源和formal仍OPEN。
