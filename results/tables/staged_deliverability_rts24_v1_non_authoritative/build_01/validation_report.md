# RTS-24公共网络构建诊断与保存读回

2026-10-22，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。依据[登记合同](../../../../docs/plan/staged_deliverability_c_rts24_build_contract_v1.md)执行唯一一次build_01，exit 0；没有重试。公共网络来源固定为PYPOWER 5.1.19 case24，业务、工程、F/X及事件仍为声明的机制假设。没有native求解、连续业务执行或公共网络数值结果。

## 已观察结果

| 项目 | 保存观测 |
|---|---|
| 输入 | 24母线、33机组、38支路；工程前/后完整frame；37支路+32机组事故集 |
| 请求 | 12个离散hour template、1699个唯一request描述；24无父root、1675父边，父request均在同template |
| 角色 | normal C 12、fault F 828、fault raw 828、P0 base 12、reference raw 3、recovery两端各8 |
| actual | 12个策略后预留槽；加描述得1711逻辑节点上界，未生成公共actual点 |
| 构模 | 2个公共normal C模型各97变量/64约束；6个三母线解析模型各11变量/8约束 |
| 解析点 | 6个完整点审计通过；变比/移相及故障包含在内；全部minimum_established=false |
| 拒绝路径 | 缺公共经济父点拒绝；故障支路非零流的损坏点拒绝 |
| factory | 0次SolverFactory请求；源码不调用solver，运行期拒绝器覆盖登记路径 |
| 旧字节 | 118个B1–B3保存文件、42仓库pin（157个唯一文件）、7选定外部文件、5旧版本一致；旧C audit根SHA固定 |
| 资源 | 脚本5.6228543s；解释器启动至退出6.1211474s；采样RSS峰值136,228,864B |
| 核心保存 | 8份机器工件共1,040,196B，7个completion清单项逐SHA匹配；没有failure |

四个离散输入窗为on_time/early的h=0、1、2与delayed/late的h=3。它们没有连续执行四小时。query_dag的1699项bound_query_identity均为空；其中1675项明确标记缺公共经济父点。model_shapes另保存两个实际绑定的无父normal C查询身份。不能把描述量当成已绑定、已构模或已求解量。延期h=3保留50MW参考接入权缺口。

`economic_kkt_audited=2`是两个解析normal-base的**显式顶层KKT审计记录数**。两个actual还分别嵌入其reference_base_P0的完整父点和经济证据；连同raw的两个父证据，保存工件包含4份不同父query身份的EconomicEvidence。bind、构模和子点审计会递归重核父KKT；2不代表所有KKT函数调用数或仅有两份父证据。正则化目标固定为报价成本+1e-8×ΣPg²，不宣称原报价最优面上的严格字典序解。

report的RSS字段仅覆盖写report前（135,847,936B），completion另记录完成前采样；launcher保存stdout末次采样峰值和解释器外层时间。stage_seconds的已计阶段合计不是完整脚本wall，导入、身份序列化、写入和收尾均仍在总wall中；阶段值不作为全部阶段覆盖或纯solver成本。

## 保存读回与检查

[postcheck.py](postcheck.py)为运行后追加的只读检查器，不属于原核心清单。它从实际保存JSON重建完整query、点与证据，重算6个点和2个顶层KKT结果，逐值一致；子点审计也核对其经济父证据。重新生成1699个描述及完整网络frame，核对身份唯一性、所有父边、角色和输入；重新核对8源文件、环境、旧字节及核心清单。读回8.018336s，0次factory请求，见[verification](verification.json)。四份父证据的另一次显式读回复算和独立审查范围见[preseal findings](preseal_findings.json)。核心8文件未倒写；launcher、本说明、postcheck、verification与findings均为追加材料。

实现检查包括193项组合回归通过（34项当时针对检查+159相关回归，15.38s）；随后增加旧audit根漂移拒绝，最新针对检查35 passed/4.91s，独立审查员复跑35 passed/4.95s。所选RTS-24旧测试仅装载/缩放，不执行其native测试。测试覆盖清洁路径、F/X、父完整点/KKT与恢复域的身份及拒绝行为；测试量不作为实验样本量或主实验验收。

## 结论与下一步

本包完成公共输入、请求与父依赖结构、两个公共正常模型构建和解析点审计的有界开发检查。公共网络normal C/P0经济基准及KKT、公共corrective完整点、raw最小性与恢复端点最优性、三方法连续策略、actual闭环、journal/关闭/fresh重开、长cohort及失败收尾仍未完成。公共网络完整F/X时序背书、C整链性能审查与D/E规模/资源仍OPEN。

已保存8源字节继续保留；实现变化进入新后继。下一步先设计连续策略和journal接线以及公共点证据获取路径，再登记需要的代表性native包、调用上限、保存/失败路径与资源；具体native仍须专项授权。本诊断没有production seal、official review、资源准入或主实验运行权限。
