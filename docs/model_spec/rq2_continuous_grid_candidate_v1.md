# 连续normal短执行与逐小时事故候选

日期：2026-09-16。状态：`DRAFT_NONAUTHORITATIVE`。

## 开发对象与科学范围

`continuous_grid_candidate.py`拥有normal构模、一次短求解、原生结果加载及canonical赋值审计的完整流程，
然后将全小时baseline连接到原始`N1OutageEvent`及已有corrective LP核心。
它复用`continuous_grid_normal.py`、`src/solvers/rq2_solver_adapter.py`和
`src/grid/rts_gmlc_grid_need_successor.py::_build_corrective_model`，不修改旧冻结入口。

事件是显式`mechanism_assumption`；candidate保留两种时钟：normal来源小时为1-based，
事故时钟为zero-based half-open，`outage_source_index=source_hour-1`。
原始seed/id/type/uid/start/end完整保存，窗口从事故中途开始不改写原起点。
normal仅接收已验证输入，不读取事件表；事件信息只在normal求解后用于逐小时响应。
不同seed是否共享同一normal最优解尚未注册，不将event-blind模型等同于跨seed共同baseline证明。

每小时产物包含normal发电/commitment、原事件、corrective完整变量与状态、grid need及必要的zero-DC确认。
无事故小时保留完整baseline，只有normal最优性及物理见证通过时给`grid_need_mw=0`。
normal失败或超时，不启动corrective；有合法incumbent仍保留normal赋值见证，全部小时grid need未决。

## Owned solve证据

每次求解fresh build，仅调用一次version-checked solver，显式`load_solutions=False`，不做重试或求解器替换。
保留所有solver/problem/solution记录、原数值表示、完整变量/目标映射、初值与加载前后快照、
结构摘要、配置options及前后版本；要求一个solver和problem记录、一个minimize目标。
native无解、多解、异常、未知标签或有效决策变量缺失均不形成最优解。
加载后重新构造canonical模型，检查fixed值、变量界、整数性、全约束残差及目标值。
normal还通过独立机组carry审计，保留初态残余义务和末态。

HiGHS legacy结果可能不报告solution objective map，空map原样保存；问题UB仍须与canonical目标
在`min(feasibility_tolerance,1e-9)`内一致，目标map存在则额外逐项核对。
最优性要求typed ok/optimal状态、typed optimal solution、合法完整赋值、有限有序LB/UB、
LB不超过incumbent及注册相对gap。corrective UB须在`[0,dc_demand]`中。
输出仅是声明数值容差下的开发证据，不是正式最优性或工程安全认证。

## 被原生接口省略的变量

`native_values`与`canonical_completed_values`分列，后者仅允许：

1. canonical fixed变量：采用构模时已固定的有限值；
2. 未出现在任何active constraint body/lower/upper或objective中、无上下界的连续变量：取显式0代表值。

判断基于表达式引用，不按变量名猜测。native已报告的变量不覆盖；used/free、bounded或integer变量缺失拒绝。
completion值与原因进入结果身份，合并完整赋值再次通过fresh canonical审计；不将补值标为solver观测。
这处理事故后完全不参与方程的相角，不改变网络方程或新增岛屿参考约束。

## 不可行报告与未决

corrective和zero-DC均为既有逐小时连续LP。typed native infeasible、零solution且结构/options/version
一致时，可保留solver报告并触发fresh zero-DC确认。通常接受native ok/warning；另对已实测
`Pyomo 6.10.1 + highspy 1.15.1 + HiGHS + corrective纯LP`精确组合，接受
`SolverStatus.error + TerminationCondition.infeasible`作为版本限定solver报告。
该特例不用于normal/MILP，也不把一般error视为不可行。

两个fresh LP均报告不可行时，小时状态为`solver_reported_exogenous_infeasibility`，grid need为null。
它是同一solver的另一次zero-DC确认，不是独立数学证明；`infeasibility_certificate=null`。
zero-DC可行、超时、异常或报告不完整时保持`unresolved_grid_need`。
任一小时未决或外生不可行报告都使`finite_grid_need_trace_available=false`，不把未知填0。

## 预算、身份与限制

调用方显式声明单次秒数、线程数、H、变量/约束、最大调用次数及总配置solver秒数预算。
开发硬上限为单次30秒、4线程、H168、20,000变量、100,000约束、20次调用及总60秒；
实际测试为单线程、每次1秒。按`1+2×active_hours`保守预留潜在zero-DC确认，预算不够时在创建solver前拒绝。
时间限制是solver配置值，不保证进程级wall-clock超时；构模/审计耗时不冒充solver耗时。

输入identity复用normal合同；执行identity覆盖本模块与normal的源依赖、版本、solver spec及budget；
事件identity单独绑定原始表及grid身份。fresh进程测试检查完整src导入闭包。
结果及solve证据只能由owned入口内部创建，普通构造/`dataclasses.replace`不能重标；普通数据记录不是签名。
`dataclasses.asdict`可序列化为开发记录，本模块不写production目录、manifest、lease或review receipt。

corrective仍是相对同小时normal基线的独立响应，不包含事故态跨小时ramp、minimum dwell、
事故修复到normal的状态转移、full-N-1或AC。因此`corrective_cross_hour_feasibility=null`，
`formal_result=false`、`security_certified=false`，尚不提供完整连续grid输入包。

## 验证记录

主线程当前44项针对性测试通过（8.76s），五文件相关回归270项通过（23.09s），覆盖原生结果/预算故障、跨入事件、输入身份、
no-outage全小时基线及zero-DC确认。四个真实小型运行覆盖H2无事故、H3线路事故、H1机组事故
及线路约束产生20 MW正grid need；这四个case合计9次solver调用，每次上限1秒/1线程，无真实RTS多日求解。
独立pre-seal最终复核44项通过（8.70s），限定范围未发现开放finding；不生成official verdict或receipt。

源码SHA256：`4f091095c621b6eb2bd403562e28f586447057767033ee1a3b1720780b2a752a`。
测试SHA256：`3c7eb3aaf94354352e51f7e1e43128523f4a0181b1820c04ff7da2ac130fe272`。
相关回归使用`python -B -m pytest -q -p no:cacheprovider`，文件为
`test_rq2_continuous_grid_candidate_v1.py`、`test_rq2_continuous_grid_normal_v1.py`、
`test_rq2_continuous_grid_carry_v1.py`、`test_rq2_continuous_planner_short_solve_v1.py`与
`test_rq2_continuous_planner_assignment_v1.py`。`git diff --check`无输出，旧SCUC/corrective/solver adapter无diff。
