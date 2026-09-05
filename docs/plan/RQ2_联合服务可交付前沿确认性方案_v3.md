# RQ2 联合服务可交付前沿确认性方案 v3

> 状态：`SEALED_READY_FOR_INDEPENDENT_REVIEW`。本方案是首次official R4
> `REWORK`后的聚焦scientific successor，不授权implementation、solver或formal run。

## 1. 权威组合

1. 机器协议：
   `configs/rq2_joint_deliverability_preregistration_successor_v3.yaml`；
2. 指标规格：
   `docs/model_spec/rq2_joint_deliverability_estimands_v2.md`；
3. 当前执行方案：本文件；
4. R4记录：
   `configs/rq2_joint_deliverability_preregistration_review_rework_v2.yaml`；
5. 历史v1/v2仅作为不可变predecessor，不再单独指导实现。

## 2. R4修复闭环

| Major | v3处理 |
|---|---|
| `network-only`受CFE恢复约束污染 | 网络单服务仅使用业务恢复余量；B6两条规划track分别使用对应恢复资格 |
| `alpha=1`结构性不可恢复 | 增加解析precheck、专用undefined状态和witness；禁止数值填补及四臂符号归因 |
| 点值忽略solver误差 | 从四臂`[LB,UB]`传播contrast区间，只允许interval-supported符号 |
| 操作性estimand未唯一冻结 | 固定全部包络常数、代表点算法、逐时policy、failure/shortfall、E0及bootstrap |
| v2声称零科学变化 | v3明确承认科学修正，逐项列出superseded paths并绑定REWORK receipt |

## 3. Pre-seal验收

validator和合成测试必须在零solver、零result write下证明：

1. v1/v2 exact outer及review receipt hash未漂移；
2. 46个cell恰好由36个factorial和10个OAT cell组成且无重复；
3. 四臂恢复矩阵严格匹配v3，尤其`network-only`不读取alpha；
4. B6规划具有grid/CFE两套恢复余量和独立时序状态，执行回到共享状态；
5. `alpha=1`解析witness阻止solver和numeric capacity；
6. 四臂capacity interval正确传播至三个contrast interval；
7. 点分解残差和区间符号状态分别验收；
8. 代表点score、排序、quantile、去重、补位和质量重分配均唯一；
9. holdout policy只读当前状态并输出grid/CFE分渠道shortfall；
10. E0质量、有限条件分母、transport和bootstrap算法均具备精确字段。

## 4. 后续阶段

1. 对v3 exact outer执行同一reviewer线程的聚焦独立复审；
2. 仅在official verdict为`PASS`后建立implementation successor；
3. 实现46-cell builder、arm-specific/track-specific recovery、结构性precheck、
   interval propagation、holdout状态机和v2输出schemas；
4. 使用合成小例和HiGHS测试实现，不启动正式数据求解；
5. 对implementation successor执行独立R3/R4 review；
6. 验签1071-block grid package；
7. 另获用户formal-run authority；
8. 运行planning、完整training support、eligible holdout、transport与bootstrap；
9. 对结果执行独立post-result R4后，才允许形成论文claim。

任何上游阶段未通过时，下游保持关闭。

## 5. 当前门禁

- v2 official R4：`REWORK`；
- v3 pre-seal：待本地validator与测试；
- v3 independent R4：未开始；
- implementation、grid、formal-run、formal-result、paper-claim：全部关闭。
