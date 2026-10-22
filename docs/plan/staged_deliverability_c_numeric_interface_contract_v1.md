# C公共数值接口开发合同

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。接续[保存交接](continuation_handoff_20261023_journal.md)。本轮开发一个可由原生LP/QP后端消费的确定性接口；不启动后端、实验、native校准或新的保存轨迹。根代理唯一writer，R3由只读sol_reviewer作PRE_SEAL审查。

## 验收范围

- 使用原公共Pyomo构模函数及目标，不修改已绑定源码、配置、科学容差、业务策略或journal。消去固定变量、等界变量和停运支路零flow；常数行仅在其原界满足时消去。保留行/列名字、上下界、目标常数、线性项及二次项、全部消元值和query SHA，形成确定性问题摘要。
- 消元映射记录每个变量原界/固定原因，以及每个常数行的原界和常数activity；不将被消去的行伪装成从未存在。所有free列（含自由angle）均以原始row/column dual核对`gradient - A.T @ row_dual`，不能只检查有box证据的列。
- 所有导出问题统一为min；max-meter只将原目标乘-1。普通测试以独立点、原Pyomo表达式及手给值核对目标、shift/tap、行界、等界和完整索引；不能把构模或解析snapshot称为公共最优解。
- 仅完整、有限、维度相符、精确绑定导出问题的snapshot可消费。原生状态须为optimal；timeout、未知、缺primal或必要dual、非有限或审计失败均不产生可用PointEvidence，不推断数学不可行。经济父/child LP必须有完整dual；actual/F可声明`dual_valid=false`并仅携带规范空tuple双数组。任何声明dual有效的snapshot（包括actual/F）均核完整有限数组及全部free列rc；不得让空/NaN数组与valid声明并存。
- 采用min形式后端的`gradient - A.T @ row_dual = col_dual`约定。平衡/支路等式乘子取负；upper行乘子取负；非固定box multiplier由reduced cost正负拆分。独立数值audit核对这些约定，不根据目标结果自动翻转符号。
- Pyomo可能把无机组母线的`constant == expression`反向表示。导出统一为独立audit的`G-Pd-Pnet-out+in=0`，逐行核对其与原Pyomo residual仅差±1并保存`original_scale`；这由原始代数决定，不依赖解或dual。后端返回的是该规范化矩阵的dual。
- 问题schema为`staged_diagonal_convex_qp_min_transport_v1`；snapshot固定`highs_min_row_bound_snapshot_v1`，不是任意后端通用的dual约定。当前只接受原模型的等式/upper行和非负对角二次项。纯Hessian导出使用`0.5*x.T@H@x`，对角值为多项式系数两倍；不做数值PSD猜测或自动修正目标。
- 经济根输出EconomicEvidence并通过原经济KKT；child LP输出完整ChildLpEvidence并通过原reduction/primal/KKT/gap；actual/F经济子点仅输出原点见证，不将其宣称为独立最优性证书。固定child变量/停运支路的对偶按原reduction置零；经济根固定机组的box乘子由固定值处stationarity重建并独立核验。
- 每次消费重新编译并精确比较问题形状、系数、消元值及identity；不接受仅由调用方声明相同query SHA的不同矩阵。模型数组与返回row activity/目标另核对原固定容差。
- 目标echo另固定绝对差`1e-6`作为传输一致性门；它不替代既有KKT/gap，也不是已测的native精度。真实后端若不满足则未决，不事后放宽。

普通测试只运行无solver的解析与公共构建例，阻断SolverFactory和Highs构造；不允许用数值优化生成expected。按差异选择相关旧回归。源字节与旧保存证据用现有只读postcheck验证。完整公共数值、公共g、139节点合同枚举、完整F/X时序及C/D/E资源仍OPEN。

## 后续真实校准

本接口不包含运行授权或自动执行入口。真实后端适配、具体公共输入/请求数/call cap、串行与线程数、wall/RAM/存储、外部watchdog、日志/心跳/终态保存和关闭重开路径须在具体native包登记并另获专项授权。不能以本轮纯接口测试关闭这些条件，也不能由解析两小时或局部构模时间估计公共全链wall。
