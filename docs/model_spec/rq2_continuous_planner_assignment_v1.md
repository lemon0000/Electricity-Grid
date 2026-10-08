# Continuous planner赋值与原始求解报告审计

状态：`DRAFT_NONAUTHORITATIVE`。实现`planner_assignment.py`，测试`test_rq2_continuous_planner_assignment_v1.py`。
本组件不调用solver，不产生正式容量证书；复用`Rq2SolverSpec`及其验证器，保持既有solver和科学协议。

## 可信输入和完整快照

调用方显式提供ContinuousPlanningInputs与arm；提交模型上的元数据不作为信任来源。
遍历active=None的全部Var，包括inactive block，按组件完整名称保存原类型、repr、float.hex、有限数值或具体错误。
None、bool、不支持的数值类型、NaN/Inf、溢出或有损大整数转换分别记录，不改成可用零值。
独立构建canonical模型，变量名集合必须完整相等才检查赋值和提取动作。

结构摘要包含所有变量域/界/fixed状态、所有线性约束及其effective active状态、目标表达式与方向；系数、常数和界用float.hex。
submitted非线性结构标记错误，仍可独立检查其合法变量值。摘要只比较当前提交结构与canonical结构，不能证明先前solver究竟求解了什么。
赋值身份绑定planner、完整快照、两份结构摘要及残差阈值；原始求解报告绑定此赋值身份。

公开AssignmentAudit在构造时从绑定的可信inputs/arm及快照重建canonical模型，复核全部派生残差、目标、错误和精确见证。
快照的类型/repr/hex/数值一致性亦检查；不能清空残差、替换目标或拼接其他赋值/其他planner的见证来重标通过。

## 数值赋值审计

将原数值原样装入新的canonical模型，分别记录每个变量的lower/upper violation及integrality violation、每条canonical约束的lower/upper violation和目标值。
变量界与约束按显式solver feasibility tolerance判断，整数性按integer feasibility tolerance判断；不使用业务SERVICE_TOLERANCE。
整数审计容差额外要求小于0.5，否则任意实数均落入某整数的接受邻域，验收失去意义。此为接口适用性门，
不替代正式注册数值容差或目标solver选项范围核验，不修改旧solver adapter。
canonical域限NonNegativeReals和Binary，因此界加整数性覆盖当前域；未来新增其他域须扩展审计。
缺值或表达式非有限时数值审计未通过。提交模型约束被deactivate、修改、替换或目标改变均不能消除canonical残差。

未完整评价的最大残差为None，不能以空列表的0充当通过证据；已得到的逐项记录仍保留。

## 精确动作提取

只从capacity、grid_service、cfe_service、recovery、allocation提取动作；每个有限float使用Fraction(repr(x))并核对round trip。
track_call/debt/remaining/on/start/stop只参与原模型数值残差，不覆盖独立物理账。
actual_service_power由精确baseline-q+r派生；allocation的birth转为绝对power source hour，仅精确零项省略。
负值不clip，微量非零不抹去，执行量不调整为请求量；负零保留原hex，在Fraction层自然成为零。
由`planner_witness`核验完整候选，提取失败或精确见证拒绝与数值残差失败分别记录。

数值赋值通过而精确见证失败是合法结果，例如`.09999999999999998`不能修复成请求`.1`；连续松弛中的微小恢复不能当物理恢复。
反之，完整原赋值中的冗余变量可能违规，而由主要动作提取的独立见证通过；两项结果分别报告。
B6提取仅形成separate-planning候选，不切换到shared execution。

## 原始求解报告

`audit_raw_solver_outcome`只接受显式原始status/termination/LB/UB并保留其数值表示。
timeout、非optimal、缺值、非有限值、倒置界、LB超过赋值目标、UB与目标不符分别列出issues。
当L<=U且差值有限时才计算raw absolute gap=U-L，不取绝对值修复倒置界；relative gap=gap/max(abs(canonical objective),1e-12)，只是诊断指标。
全部报告保持unresolved及`raw_solver_report_unaudited`，包括数值一致的optimal报告：当前没有build→solve→snapshot运行链证明，也没有solver bound来源认证。
raw LB/UB只标注offline relaxed open prefix，不传成effective prefix、complete或causal界。不依据infeasible字符串签发数学不可行结论。

## 验收与后续

手工赋值和故障注入覆盖四臂、完整inventory、inactive block、约束停用、同规模表达式/目标/域修改、非有限及缺失赋值、整数和连续阈值分离、微量动作保留、raw outcome失败分类。未执行solver。
下一步需独占canonical build→solve→snapshot的短求解适配，绑定前后结构、真实solver版本/options与原始结果，再按对象证明解释界。
正式窗口规模/资源门、完整服务projection/continuation、因果策略训练和科学协议仍待验收。

本轮47项针对性、8文件281项相关回归通过。两项独立pre-seal finding（派生审计对象重标、integer tolerance>=.5）已闭合，限定范围无开放finding。
审查方另复跑47项targeted与planner/witness/assignment合计146项通过，原两项独立攻击反例均被拒绝。
源码SHA256：`4e1a7fdc991accb61e613d79d8a3f958362bd1cf022e590dc66642f9388296b6`；测试SHA256：`59992c8d93483893fc7f5464dac542336df61ef48cc9eb5db0b9f78138cac396`。

## 下一短求解适配的设计入口

采用内部fresh build→预算检查→version-checked create_solver→load_solutions=False→原生result→显式load→立即snapshot流程。
入口不接受人工status/bounds。budget显式限制time limit、threads、变量/约束规模、scenario数及H；在创建solver前拒绝越界，不自动重试或fallback。
限时选项仅是solver预算，不承诺强制wall-clock终止。0个solution不加载，多个solution的选择语义首版保持未决；加载失败不沿用残值。
timeout若恰有1个solution，仍加载并审计候选，但整体未决；optimal且来源、结构、赋值、finite有序bounds及gap检查通过才考虑单列relaxed-prefix证据。
pre/post结构及load前变量初值必须保持；真实包版本、返回options、原始结果与assignment身份一并记录。
精确物理见证是否通过与relaxed-prefix区间分别评价，complete/causal仍为null。此段不注册formal runner或新科学阈值。
