# 共同参考数值调度选择与状态递推

日期：2026-09-19。状态：DRAFT_NONAUTHORITATIVE，独立pre-seal限定范围无开放实质finding。
实现`reference_selector.py`；扩展`reference_grid.py`接受受控ReferenceGridState，原origin API与物理约束保留。
正式科学协议未注册，不输出数学精确lex、因果、安全、完整服务或容量证书。

## 顺序与数值合同

selector显式声明规则、absolute gap MW、relative gap及lock_tolerance_mw门。每小时依次最小化：
`(B-P_ref, sum(abs(generation-normal)), generation按唯一排序UID)`，包含fixed/disabled UID。
L1用非负辅助变量与双侧线性约束表示；每级fresh构模，前级canonical incumbent目标以原float等式固定。
固定值和本级目标显式记录float.hex，身份编码也按float.hex；不round，不把Fraction投影值替换数值等式RHS。
本级目标与全部前级等式另用Q(str)重算；从L1级开始同时检查辅助变量总量与实际绝对偏差总量一致。
物理辅助不等式仍使用继承的1e-6 MW；目标值与前级锁定、L1辅助总量与实际绝对偏差的一致性
使用显式lock_tolerance_mw，要求0 <= lock_tolerance_mw <= absolute_gap_mw。
L1优先级重算使用实际绝对偏差，避免辅助量掩盖已锁定目标的漂移。
零lock门表示Q(str)严格相等；十进制重算与浮点canonical值有差异时保留unresolved，不round或放宽。
maximum_objective_lock_violation单独记录锁定/目标残差；maximum_exact_selector_violation记录全部selector残差最大值。
各级solver gap与目标锁定误差分开验收；absolute gap不是最终全部优先级累计误差的证书。

每级要求已有owned native pipeline的optimal验收、唯一完整赋值、无来源错误、fresh物理投影、
finite非负且有序的LB/UB/objective，以及显式absolute/relative gap门。relative分母为max(abs(UB),1e-12)。
这是预先声明的数值算法，不是精确实数lex最优证明；任何stage不合格立即停止，不降级采用前级可行解。
原始solver bounds、状态、options、版本、完整赋值和每级固定目标均保留在stage中。

## 总预算

在第一次native调用前，按机组数n预检完整n+2次调用、每次solver time_limit、线程和共享总solver秒数。
最后一级具有最多约束，提前构建只用于规模检查的placeholder-lock模型，确认完整规模在预算内。
不通过每级重置预算绕过限额。预算的秒数是声明的native solver limit之和，不是Python构模/审计全过程的wall-clock watchdog。
该接口限开发短预算；GridDevelopmentBudget硬上限20次调用，因此当前最多支持18个generator UID，
fixed/disabled机组也计入，不能仅通过提高传入budget覆盖正式网络。
正式规模、运行监控及资源许可仍需正式runtime验收。

## 后继状态

只有全部级通过，最终reference赋值产生所选G（baseline与P分别Q(str)后相减）和ReferenceGridState。
state绑定origin、previous state、固定selector policy、全部选择证据摘要及最终实际carry；generation必须与最后完整赋值逐UID相同。
后续小时沿用同一normal/network/事件揭示链及selector policy。换solver、阈值、预算或实现将改变policy identity，不能接旧state。
ReferenceGridState受控构造，不接受arm ActualStepCarry冒充参考状态，不从普通可行assignment产生后继。
失败时next_reference_state和selected_request均为空，之前状态不变；保留失败级及此前各级证据，不把无解/超时标成数学不可行。

当前normal计划/初态/repair cap及reference规则仍是机制声明。接口没有读取arm/CFE target/业务容量；
完整共同来源适配、持久化重放及四臂双提交尚未连接，因此不据此声称完整因果或正式共同请求包已完成。

## 验证记录

初批35项测试通过（27.58s）；后续修订最终52项针对性通过（56.94s），
四文件174项相关回归通过（105.29s）。覆盖真实多级与跨小时选择、非单调功率域、空域、各级故障、
两机UID平局、输入次序不变性、exact/float分工、来源与gap异常、完整预算提前拒绝、policy/identity漂移和依赖闭包。
独立pre-seal发现原1e-6锁定门可放过超过声明gap的5e-7目标漂移；修复采用显式更严格lock门，
新增5e-7前级漂移、L1辅助slack、非法lock和零容差decimal反例。独立复核当前52项通过（58.80s），
确认finding闭合，限定范围无开放实质finding；该结论不是official verdict或receipt。

验证命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`，
targeted为`tests/test_rq2_reference_selector_v1.py`；相关回归另含`test_rq2_reference_grid_v1.py`、
`test_rq2_current_grid_step_v1.py`、`test_rq2_current_grid_short_solve_v1.py`（均在tests目录）。
真实微型求解每次1秒/1线程；无formal run、production seal、receipt或正式门变化。

当前开发字节SHA256（非production seal）：

- selector：`2554da17477580396ae698e91f9d8c6f755968c218b1801e521dd11e478eae48`
- reference_grid：`c0979459844985fb87f4666fdbd19041864d186d570d1a1a7bdb8ab0e0d31269`
- selector test：`fbc6e4f295d1022fb7ee26c154ec131633f90980223d4cb7594b63922257fcad`

各臂固定实际功率的dispatch selector后续已开发并完成限定pre-seal，见`rq2_actual_dispatch_selector_v1.md`。
下一项共同请求exact单位适配、reference轨迹/四臂事务连接及正式训练容量绑定。
