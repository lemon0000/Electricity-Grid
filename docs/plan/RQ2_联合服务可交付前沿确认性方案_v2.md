# RQ2 联合服务可交付前沿确认性方案 v2

> 状态：`SEALED_READY_FOR_INDEPENDENT_REVIEW`。本文件与sealed v1科学配置及指标规格共同构成
> 当前候选，不授权solver、formal run或结果发布。

## 1. 权威组合

1. 科学配置：
   `configs/rq2_joint_deliverability_preregistration_v1.yaml`；
2. 指标规格：
   `docs/model_spec/rq2_joint_deliverability_estimands_v1.md`；
3. 当前执行方案：本文件；
4. v2机器修正：
   `configs/rq2_joint_deliverability_preregistration_amendment_v2.yaml`。

v1配置中的研究问题、四臂、46-cell矩阵、CFE目标、容量指标、holdout指标、
transport规则、阈值、solver contract与全部关闭门保持不变。

## 2. 修正后的验收项

实现阶段的合成小例必须验证：

1. `I_joint = I_sep + A_B6`的有符号四臂分解；
2. 四个注册CFE目标的完整缺口重建；
3. `min(business headroom, CFE-compatible surplus)`恢复上界；
4. training infeasible、cap infeasible与solver unresolved的fail-closed状态；
5. 正负容量差值均保留，并由逐时轨迹和binding-constraint witness解释。

完整时序包络包含duration、event count、minimum-event-power、rest、energy和
recovery约束，因此不对`D_N,D_C,D_B,D_J`施加跨arm顺序门。

## 3. 完整阶段顺序

1. 取得本v2 exact sealed outer的独立R4 PASS；
2. 建立target-specific完整CFE缺口、CFE-compatible recovery、46-cell inventory
   和非互斥归因的versioned implementation successor；
3. 运行第2节的合成小例和相关回归；
4. 完成implementation successor的独立R3/R4 review；
5. 验签1071-block grid package；
6. 另获用户formal-run authority；
7. 运行46-cell四臂planning与完整training-support audit；
8. 仅对eligible cells运行holdout Cartesian replay；
9. 计算transport bounds、共同coupling witness和bootstrap；
10. 发布完整cell inventory、离散前沿、有符号归因、负结果与未决状态。

任何上游stage未完整发布并验签时，不启动下游stage。

## 4. 当前门禁

- v2已seal，独立R4 review尚未开始；
- 46-cell implementation、runner和output path尚未绑定；
- grid package、formal-run authority、formal result、paper claim和security
  certification均为false；
- v1 sealed outer保持不可变，不作为当前独立review入口。
