# 多小时事故态赋值审计与同轨迹交接

日期：2026-09-16。状态：`DRAFT_NONAUTHORITATIVE`。
实现：`src/rq2_joint_deliverability_boundary_v1/outage_assignment.py`。

## 输入及赋值审核

消费`OutageTrajectoryInputs`、调用者预存的完整problem identity及canonical变量名到原值的完整dict。
先重建当前完整事故态模型；变量不允许缺少或增加，值只接受有限built-in int/float，拒绝bool及隐式转换。
分别检查canonical fixed值、变量上下界、全部active约束，阈值固定`1e-6`，不允许调用方放宽。
原值保存在不可变有序tuple中，identity沿用float.hex表示；不舍入、截断、补值或修复。
目标只重新计算。有限输入发生算术overflow时保留失败，无法表示的残差记None并伴随错误。

`OutageAssignmentWitness`只能由审计入口构建，绑定problem、完整assignment、审核结果及本组件源码摘要。
contract及固定容差捕获到见证字段，result_id只读取捕获内容；入口拒绝运行时contract或容差漂移。
此检查由独立pre-seal的1.1e-6残差改容差反例推动，不能靠保持源文件hash不变就接受内存中的阈值变化。
上游problem身份覆盖normal候选、数据、原事件、目标、repair与原点参数、依赖及runtime版本。
结果只是当前模型与容差下的完整赋值可行性；不证明solver来源、最优性、唯一向量或因果响应。

## 同一完整轨迹的分块提取

`replay_outage_chunk`接受非空连续source-hour tuple。首块必须从原完整问题首小时开始；后继必须紧接前块。
每次都重新审计完整原assignment并比较见证，拒绝失败、源码漂移、问题或赋值改变。
末态由原完整赋值在cut处精确提取；入口没有独立suffix assignment或重新优化选项。

`OutageReplayCarry`绑定full problem、full assignment、normal candidate及绝对source hour，分列：

- 全机组actual generation、availability及当时完整原事件；
- 同一normal赋值前缀经`replay_grid_chunk`核验的normal carry，包含原GridIdentity与计划dwell；
- `derived_offline_assignment_witness`角色，信息模式仍为原problem的offline full-event-path。

前块carry在后继入口与同一完整赋值重新推导的前缀末态比较，不能只保留相同normal candidate而换actual路径。
完整canonical复核已覆盖cut两侧和全部内部边；此接口是同轨迹机械重放与状态提取，未另建一个可独立求解的slice模型。
持续故障保留原active event；修复和相邻新事故按完整模型的绝对事件时钟验收，不重编号、不重触发trip。
actual出力不覆盖normal出力，forced outage不更改normal dwell。

本接口不接受任意裸snapshot，不把carry转成新`OutageTrajectoryInputs`，也不允许重新优化suffix后继承原轨迹身份。
新窗口滚动调度、不同normal计划、末态历史网络可达性及因果控制器需要各自的合同和验证。
assignment不合法时不能生成任何carry；完整可行见证仍不属于工程安全、AC或完整N-1认证。

## 验证与剩余工作

测试入口：`tests/test_rq2_outage_assignment_v1.py`。覆盖完整与分块末态一致、持续事故、修复与相邻新事故、
actual和normal末态分离、同normal不同assignment混接拒绝、fixed值/变量界/约束篡改、数据类型和inventory、
源码漂移及导入依赖闭包。修复运行时contract/容差finding后，五文件211项相关回归通过（52.98s），包含本组件33项；
修复前209项不作为当前snapshot的最终证据。独立pre-seal复跑33项通过（25.11s），运行时合同finding已复核闭合，限定范围无开放实质finding；未生成official receipt。
测试借用已验证的微型normal候选，每次normal求解限1秒/1线程；事故态仍是手工解析赋值，未调用其solver。

解释器为`D:/Miniconda3/envs/compute/python.exe -B`，实际命令为：

```text
python -B -m pytest -q -p no:cacheprovider tests/test_rq2_outage_assignment_v1.py tests/test_rq2_outage_trajectory_v1.py tests/test_rq2_continuous_grid_candidate_v1.py tests/test_rq2_continuous_grid_normal_v1.py tests/test_rq2_continuous_grid_carry_v1.py
```

源码SHA256：`928d9547354047eb04fb06a42612fba9d8ca5a5c2c24f094086f2581a7d1ea6b`；
测试SHA256：`f4c2e1d9063b3212ca91c7aebcdb5223a3f805960cf716cc3b88a589c968205c`。
`git diff --check`通过，旧`src/grid`、`src/solvers`及已跟踪configs无diff。

下一项是由组件独占build→solve→native snapshot→load→canonical audit的事故态短求解入口。
必须按indexed curtailment及显式objective重新定义验收，不能复用旧标量curtailment最优性条件。
正式连续输入发布、机制参数注册、因果/完整服务证书、新规模runtime与执行门保持开放。

后续开发更新：上述短求解已实现为`outage_short_solve.py`，见`rq2_outage_short_solve_v1.md`。
其40项targeted及六文件251项相关回归通过，独立pre-seal限定范围无开放实质finding；本赋值组件源码保持。
