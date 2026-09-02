# RQ2 增强基线鲁棒性预注册 v1

> 状态：`design_only_not_executable`。本文件解释
> `configs/rq2_public_baseline_robustness_preregistration_v1.yaml`；机器可执行的
> 冻结边界以 YAML 及其 SHA256 manifest 为准。当前
> `implementation_bound=false`、`independent_R4_review_passed=false`、
> `user_formal_run_authorized=false`、`formal_execution_ready=false`、
> `formal_result=false`。
>
> 冻结 SHA256：config =
> `017708b25c3e1702c938a108af070a7047517bd128552500d3ffcac6a3ee3554`；manifest =
> `da6d13055ccfcd03c00939ab7fa61f43e05052556211f725b4550a09d33f64c9`。
>
> 当前状态导航：本文件正文保留预注册时点的设计与证据状态。后续已实现四臂
> core、checkpoint/external-preflight及identification/report的validate-only合同，
> 但正式grid输入、独立复审、用户执行授权、execution readiness和正式结果仍为
> false。实时状态见`RQ2_开发机任务与执行边界.md`和
> `docs/model_spec/blocker_register.md`。

## 1. Problem–Method–Insight

**Problem。** 已观察的 70-cell 三区域相图为 `R1=0, R2=0, R3=69,
mixed=1, unresolved=0`。这份派生 benchmark 不支持原始正向 H2，也不能区分
共同不足来自单一服务本身、两类服务的联合交互，还是 B6 规划口径造成的特异性
欠配置。v6 pilot 与 formal result 均尚未观察。

**Method。** 在 v6 完全相同的数据、15 个 OAT cells、block splits、训练代表点、
完整训练支持审计、fixed-policy holdout 规则、时序物理包络和 solver contract 下，
预注册四个且仅四个 arm。变化仅是服务调用组合或 B6 规划口径；任何 arm 均不得
改变 CFE target、POI、阈值、recovery、windows、support、代表点或 solver。

**Insight boundary。** 未来四臂结果最多支持对冻结公开边缘样本和冻结时序模型的
机制归因。它不把已有 70-cell 阴性证据改写为正证据，也不识别现实 joint law、
合同发生率或因果效应，更不构成 X、absolute Alibaba MW、outage probability、
full-N-1、AC 或 security certification。

## 2. 不变量、变更半径与四个 arms

本 v1 不改 `formulation.md`、v6 preregistration/manifest、v4 configs/runners、
生产实现或结果。70-cell summary 与 manifest 以现有 SHA256 作为 immutable
predecessor evidence。T1 的 instantaneous MW-only 界仅作解析诊断，不替代包含
duration/event/rest/energy/debt 的完整时序 arm。

| arm ID | grid call | green call | planning | execution |
|---|---|---|---|---|
| `network_only_shared` | inherited active | 0 | shared | shared |
| `cfe_only_shared` | 0 | inherited active | shared | shared |
| `joint_correct_shared` | inherited active | inherited active | shared | shared |
| `joint_b6_separate_planning_shared_execution` | inherited active | inherited active | separate by service, then combined | shared |

所有 arms 保留 E0 的无条件质量并单独报告；E0 不进入 conditional service metric，
也不进入 R3。training proven infeasible 使相应 fixed-policy estimand 未定义；timeout、
缺证书或未解析状态不得解释为 infeasible。

## 3. 冻结 estimands

每个 arm、每个 cell 报告 minimum normalized flexibility `D_min_by_arm`。派生量为

\[
I_{joint}=D_{joint,correct}-\max(D_{network},D_{cfe}),
\]

\[
U_{B6}=D_{joint,correct}-D_{joint,B6}.
\]

同时报告各单服务与联合 arm 的 fixed-policy failure probability、expected
shortfall、peak recovery debt 和 terminal recovery debt。前两项属于
`service_risk_metrics`，正的结构化 contrast 表示左侧 arm 更差；后两项仅属于
`descriptive_state_metrics`，其正负不决定机制类别，也不抵消 service-risk 结论。
right-censored terminal debt 不得当作失败。未来只有在非右删失窗口中注册并实现
明确 machine field 的 `debt_limit_violation` 或 `terminal_condition_violation`，才可
另行作为 failure channel；本 v1 两个字段均 planned/unbound，不能参与归类。
`D_joint_B6 = max(D_network, D_cfe)` 仅是待验证 identity；设计不预设其成立。

## 4. transport 与共同见证

Primary analysis 是完整有限 Cartesian support 上的 full transport sharp bounds。
`independent_product`、comonotone 和 countermonotone 仅是诊断 coupling，不是现实
joint law。每项 multimetric attribution 或 region statement 必须由同一个
`pi` witness 同时满足；不得拼接不同 metric 的 endpoint witnesses。

只有 pair 完整、结果已解析、额外结构限制已编码且 endpoint witness 通过边缘残差
校验时才可称 sharp。现有 pairwise v4 不包含 T1 所需的原始 `g_t/c_t` 轨迹，因此
该诊断仅登记为 future implementation requirement；路径为 `null`，门为 false。

## 5. 互斥且 fail-closed 的 attribution

归类前必须同时满足：四 arm training 状态已解析；所有 required pairwise rows 与
E0 rows 齐全且已解析；transport endpoints attained 且边缘残差合格；multimetric
结论存在同一 `pi` witness；config 与 upstream hashes 均验证通过。

归类按以下优先级互斥执行：

1. `unresolved`：任一全局前置条件失败或任一必要结果不可解析；禁止正式主张。
2. `training_infeasible_estimand_undefined`：在冻结 solver contract 下有经证明的
   training infeasibility；不生成 fixed-policy attribution。
3. `single_service_insufficiency_supported`：至少一个 single-service arm 在
   failure probability 或 expected shortfall 上满足 all-coupling robust positive，
   并满足共同见证要求。
4. `joint_only_interaction_supported`：两个 single-service arms 对注册风险 metric
   均 robust nonpositive，而 `joint_correct_shared` 的 `I_joint` 为正或存在 robust
   positive service metric，并满足共同见证要求。
5. `b6_specific_underprovisioning_supported`：两个 single-service arms 与
   `joint_correct_shared` 对注册风险 metric 均 robust nonpositive，而 `U_B6` 超过
   tolerance 或 B6-minus-correct 风险为 robust positive，并满足共同见证要求。
6. `partially_identified`：所有前置条件满足，但 category-determining sign 跨越
   tolerance，或候选归因只能由不兼容 couplings 分别见证；禁止经验机制主张。
7. `no_registered_mechanism_supported`：所有 category-determining capacity 与
   service-risk contrasts 均 robust nonpositive，且不满足更早类别；这只排除冻结
   指标内的注册机制，不构成经验因果结论。

其中 robust positive 使用 `LB > tolerance`；robust nonpositive 使用
`UB <= tolerance`。`LB <= tolerance < UB` 是 partial identification，不能把
independent coupling 的单点结果提升成 robustness 结论。
Recovery debt 只作状态描述；原始正 debt、right-censored terminal debt 或尚未实现的
violation 字段均不能触发上述 single/joint/B6 标签。

## 6. 尚未执行的结果链

冻结阶段顺序为：

`verified v6 grid package`
→ `future four-arm planning/pairwise package`
→ `future four-arm identification package`
→ `future baseline robustness report/package`。

每一阶段都必须包含 config hash、upstream manifest/provenance、checkpoint
inventory、声明的 machine-readable schemas、全部注册 cells（含 negative 与
unresolved）和 SHA256 manifest。identification package 还必须保存 scalar endpoint
witnesses 与 common-`pi` multimetric witnesses。所有 future implementation、config、
runner 和 output path 当前均为 `null`，且不得列入冻结 manifest。

首阶段不是 future implementation：它精确绑定 v6 已冻结的
`configs/rts_gmlc_public_grid_need_dispatch_v4.yaml`、
`experiments/run_rts_gmlc_public_grid_need_dispatch_v4.py`、直接实现 authority
`src/grid/rts_gmlc_grid_need_successor.py`、输出目录
`data/processed/model_inputs/rts_gmlc_public_grid_need_dispatch_v4_gurobi`与 schema
`rts_gmlc_public_grid_need_dispatch_v4`。这些代码/配置已经存在，但 runtime receipt、
provenance manifest 与完整 grid package 尚未验证，所以该 stage 仍为`ready=false`。

## 7. 可证伪条件与放行条件

- 若四臂不能在同一设计与 solver contract 下实现，本设计不可用于归因。
- 若任一 arm、cell、E0、endpoint 或共同见证未解析，则相应 formal attribution
  失败并保持 `unresolved`。
- 若 single-service 风险已经 all-coupling positive，则推翻该 cell 的 joint-only
  或 B6-specific 解释。
- 若 `I_joint` 不为正且 joint arm 的注册风险不 robust positive，则不支持
  `joint_only_interaction_supported`。
- 若 `U_B6` 不超过 tolerance 且 B6-minus-correct 风险不 robust positive，则不支持
  `b6_specific_underprovisioning_supported`。
- 若正负号依赖 coupling，则报告 `partially_identified`，不发布单一机制标签。

只有 future four-arm implementation/config/runner 完整冻结、独立 R4 复审通过、用户明确
授权正式运行且所有上游包与 schema 验证通过后，才可另行提升 execution gate；本
v1 自身不接入现有 executor，也不授权 solver、pilot 或 formal run。
