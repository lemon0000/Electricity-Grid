# 当前小时固定业务功率网络验收

日期：2026-09-19。状态：DRAFT_NONAUTHORITATIVE；独立pre-seal限定范围无开放实质finding。

## 对象与信息边界

实现为`src/rq2_joint_deliverability_boundary_v1/current_grid_step.py`。
输入为经过隔离的CurrentGridInformation、当前DisclosureStep、上小时ActualStepCarry和精确有理数MW业务功率。
当前接口验收给定赋值；不选择请求、业务动作或dispatch，不调用solver。完整normal计划的提前发布仍为机制声明。
输入没有未来事故表；这不证明外部提供赋值的选择过程具有因果性。

origin必须显式声明mechanism_assumption，核对前一小时clock、normal计划commitment、静态出力界、完整机组inventory和事故组件。
后续actual carry只由完整赋值审计产生，绑定静态network、allowed plan、当前时钟、实际出力、基础及有效availability、
planned commitment、已揭示事件状态和前驱输入/赋值摘要。它不是经验实测状态，也不是持久化来源认证。

## 固定机制与物理约束

- normal commitment固定；故障通过availability处理，不改写计划开停。
- 基础availability在episode内固定；变化需另立trip/repair合同，目前入口拒绝。有效availability还受当前generator outage影响。
- 机组当前上下界、固定机组出力，以及非fixed机组相对normal出力的一小时response限制均保留。
- 有效available的fixed机组必须报告完全相等的当前上下界；不相等属于输入歧义，入口拒绝。
  故障不可用时保留其profile bounds，但实际出力固定为0；curtailable机组使用当前区间，disabled机组不能被当前报告启用。
- committable机组actual ramp连接前一小时实际出力；计划startup/shutdown按nameplate提供原有allowance。
- 仅有效availability因当前故障下降时豁免下降ramp；修复返回必须有当前揭示的cap，且不超过nameplate。
- AC故障支路flow为0且移除该支路角度方程；其他支路按continuous rating和DC方程，DC支路保持静态界，参考角为0。
- 每节点使用当前外部负荷与给定DC实际功率平衡；业务恢复功率可以高于baseline，但不得超过physical/connected上限。
- 目标为0，仅检查可行性。实时备用未注册、不在本模型内；本组件不认证AC/N-1工程安全。

## 审计与拒绝语义

fresh重建模型，要求全部变量原始赋值，检查fixed值、变量界及全部约束；另以Fraction独立计算节点平衡、
机组可用性/界、response、实际ramp及repair残差。统一阈值为1e-6 MW，原exact业务功率不被float投影替代。
输入错误抛出ValueError；给定赋值违反约束时返回errors且next_carry=None。
拒绝不会修改旧carry，也不代表不存在其他可行dispatch。无因果、数学不可行、容量或完整服务证书。

## 验收矩阵与开发记录

解析例包括：origin/normal=20、ramp=10、外部负荷10，DC=20时总出力30有效、DC=21时31违反ramp；
修复origin=0、当前总负荷10，cap=10有效、cap=9无合法给定赋值；支路故障后只能由仍可用的DC支路供给远端负荷。
另验证actual prior不同于normal、三小时状态衔接、固定参考角、支路容量、未知组件、缺修复报告、基础availability变化、
exact MW浮点投影、数值溢出、合同漂移，以及调用者不能直接构造或replace受控carry。

最终41项测试通过（8.86s），含同小时一机返回/另一机跳闸、计划startup/shutdown、完整赋值与identity错误及审计期间合同漂移。
独立pre-seal发现fixed机组不等current bounds被静默解释为固定upper，已改为入口拒绝并补五项非committable测试。
修复后五文件173项相关回归通过（50.01s）；独立复跑41项通过（8.49s），另复核五项noncommittable例（2.54s），finding闭合。
执行命令为`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`，相关文件为
`test_rq2_current_grid_step_v1.py`、`test_rq2_grid_information_v1.py`、`test_rq2_event_disclosure_v1.py`、
`test_rq2_outage_trajectory_v1.py`、`test_rq2_outage_assignment_v1.py`（均在tests目录）。
新测试全部为构模与解析赋值，未启动新solver或正式实验；旧grid/solver/scenario源码及冻结config无tracked diff，`git diff --check`通过。

当前开发字节SHA256：

- source：`355f18c7d65b030758e0d5d16b5e4d3427332ca9251c958284e43f8daabc6513`
- test：`96bdcf8c3a7264226f6249cac8e6fe6ecb26c49658e5dc56bb7bebd3b184af1e`

以上为开发可复核记录，不是production seal、official review receipt或启动授权。
下一必要工作为owned单小时短求解、请求及调度选择合同和业务策略逐小时连接。
原离线模型、冻结配置和现有诊断包保持。当前开发不关闭完整continuous输入、完整恢复或formal门。
