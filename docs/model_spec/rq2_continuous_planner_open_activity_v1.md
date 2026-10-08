# 连续 planner 开放活动边界适配

2026-09-28，`DRAFT_NONAUTHORITATIVE`。范围为 build-only 下界松弛及精确动作见证；
源码为 `continuous_planner_open_activity.py`、`planner_open_activity_witness.py`。
本组件不运行 solver，不产生 solver bound、正式容量证书或运行授权。

## 适配与不变量

科学候选的 `minimum_event_power=1e-6` 等于 `SERVICE_TOLERANCE`，旧输入类型要求严格大于。
新 `OpenActivityPlanningInputs` 是独立类型，接受 `minimum_event_power >= SERVICE_TOLERANCE`，
使用独立 scope/identity，绑定 `open_activity_boundary_outer_relaxation`。
旧输入、planner、赋值审计、short-solve 与 witness 字节保持；旧接口拒绝新输入类型。

物理活动仍要求 `q=0` 或 `q>tol`，且正调用满足 `q>=minimum_event_power`。
闭模型采用 `q>=minimum_event_power*on` 和 `q<=maximum_capacity*on`。
任意符合严格活动规则的轨迹可取 `on=1[q>0]`：非活动时 q=0，活动时 q>=minimum_event_power，
因此满足这两个闭约束。其余容量、请求、响应、事件、预算、逐 cohort 恢复和期限约束沿用旧式。
这是**相同已声明前缀与合同**的集合包含关系，不证明前缀到尚未注册完整目标的关系。

当最小事件功率等于 tol 时，闭模型还容纳 `q=tol,on=1`；它只是松弛动作。
新 witness 复用原 `planner_witness._audit_hour` 的 Fraction 精确检查，正调用 `q<=TOL` 被拒绝，
不提交物理后继。连续非负恢复仍是原有的另一项松弛，小于或等于物理阈值的正恢复仍被拒绝。
GRID_EXCESS 模式允许构造零请求上的边界假调用；CFE-only 的精确请求等式继续生效。

B6 保留两套规划账，其见证只属于 separate planning；其他臂仍为 shared physical prefix。
已知 due 在窗内时，due 小时恢复后必须偿清。开放末端继续保留债务和右删失。
所有输入及例子标注机制假设，没有新增真实业务观测。

## 验证与当前边界

针对性测试覆盖：四臂略高于边界的合法投影及债务；恰在边界的假活动；零活动；
到期恢复与欠债拒绝；微小恢复拒绝；类型/identity 隔离；未支持合同拒绝。
两种 service mode × 四臂在共同适用域内逐变量 domain/bound、逐约束标准线性表示和目标一致。
新测试33项；连同旧 planner、witness、assignment 回归共179项通过（2.13秒），无 solver 调用。
准确命令及开发字节哈希见
`results/tables/rq2_continuous_planner_open_activity_v1_non_authoritative/development_checks.json`。

新 builder 没有接入旧 short-solve：不能用新类型绕过旧身份检查，也不能将 relaxed incumbent
写成物理、因果或完整容量上界。后续需版本化接入原生赋值/界审计，并完成完整目标合同、
training→holdout 证书绑定及完整支持资源验收。本轮不封存本 draft、不签发 official receipt。
