# 双向物理功率容量开发与验收

2026-09-28，开发候选；生命周期状态由独立 manifest/审查记录给出。
科学授权为用户本轮批准的双向容量定义，实施风险R3，根代理唯一写入者。

`D` 是按声明 `D_DC` 归一化的物理功率容量，主目标仍为四臂最低 `D`。
每条规划track满足 `q+r<=D`，`eta*r` 仅表示有效工作恢复率。
单位沿用输入归一化契约；本组件不识别或批准某个具体 `D_DC` 数值。
B6的grid/cfe两账各自受同一D上限约束，其规划witness仅证明分离账前缀。
固定策略所有臂（含B6）都使用一份shared execution容量，恢复上限取D、固定恢复功率、
当小时恢复功率、业务headroom、适用CFE surplus及债务/量化限制共同允许值。

## 版本边界

新增六个模块：`continuous_planner_bidirectional`、`planner_bidirectional_witness`、
`planner_bidirectional_assignment`、`planner_bidirectional_short_solve`、
`capacity_policy_bidirectional`、`scale_hourly_bidirectional_transaction`。
输入、witness candidate、assignment/native结果、policy/observation/record/cursor及transaction
publication/proposal/cursor均有独立类型或身份。基础scenario、精确动作、数值快照、开发预算、
债务账、网侧selector/replay原语复用；不把新类型继承成旧业务policy/cursor。
旧冻结及open-activity draft原字节保留，已封存episode入口仍只接受原类型。
新transaction显式创建新业务observation并调用新policy，验证同一外部网侧归档后成对提交；
业务拒绝或网侧unresolved保持前状态，不推进publication，不提供resume。
当前接入范围到小时事务；持续episode的transport/worker/controller若消费新类型，须另行显式版本化。

严格witness在任何hour replay前以Fraction检查每track `q+r<=D`；拒绝时无candidate step，
状态停留在此前已接受前缀。旧活动阈值、恢复效率、服务平衡、headroom、事件/能量、期限账继续验收。
assignment从可信输入重建新canonical模型，失活提交模型约束不能隐藏违反容量限制。
原生adapter保留旧开放活动adapter的数值门，包括严格lower<=canonical、原始LB/UB顺序、
目标一致性1e-9与spec声明的残差/整数/gap；normal专用数值修复未传播。
不强行把解析最优数值的浮点赋值转成精确物理witness。

## 冻结验收矩阵

1. 独立解析下界与可行见证：0.4/eta0.8，一小时恢复D=0.5；两小时恢复D=0.4，四臂覆盖。
2. 每track物理功率约束、B6两账、共享实际执行容量；不误用eta*r或两份执行容量。
3. 严格超容量（含小于数值容差的超限）拒绝且状态不推进；保留截止期与开放活动边界拒绝。
4. 恢复功率/业务headroom/CFE surplus、因果前缀、事件/预算及债务守恒回归。
5. 新旧输入、witness、policy/observation/cursor、transaction类型互拒；身份漂移与归档pin拒绝。
6. 原生界原样保存，timeout、无incumbent、异常、未知/不可行status不生成数学不可行证书；单次调用无重试。
7. 新transaction四臂、两小时恢复链、业务拒绝、网侧unresolved、成对提交/零solver replay回归。
8. 已封存518成员、科学候选YAML及旧open-activity开发产物hash保持；无formal run。

测试入口为 `tests/test_rq2_bidirectional_{capacity,native,policy,transaction}_v1.py`。
合成数据仅为机制验收。原生短求解适用上限沿用旧budget，未授权192h或正式实验。
E168/F24/stride24、birth+24、nonrolling192h和事件/能量预算仍未注册。
完整有限登记S/F/U合同、因果training容量到holdout绑定、真实来源全支持与计算资源门仍开放。
本组件的prefix/complete容量证书、causal证书、formal/security均继续为空或false。
