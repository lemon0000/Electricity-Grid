# Normal 数值最优验收修复候选

2026-09-28，R4 / DRAFT_NONAUTHORITATIVE。尚未替换旧验收或取得具体科学合同授权。

问题：已完成 H25 的 Pyomo/canonical 目标是 `1388837.913859345`，
Pyomo lower/upper 是 `1388837.9138593453/1388837.9138593455`。
旧谓词 `lower <= canonical` 因 1 ULP 交叉失败；最大残差 `2.788453912216937e-10`。
旧结果继续是 unresolved。精确重算目标也低于该 lower，因此重排浮点求和并不能消除问题。

范围限定为 pinned Gurobi direct、单目标线性最小化 MIP 的 normal。
Gurobi 的 optimal 是在指定容差下成立，而非精确有理数证明：
[官方目标说明](https://docs.gurobi.com/projects/optimizer/en/current/concepts/modeling/objectives.html)、
[容差说明](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html)、
[模型属性说明](https://docs.gurobi.com/projects/optimizer/en/current/reference/attributes/model.html)。

本候选把同一原生求解器内的界关系与跨通道目标一致性分开检查：

1. 原样保存 `ObjBound`、`ObjVal`、`ObjBoundC` 及其 hex；要求 `ObjBound <= ObjVal`。
2. Direct `ObjBound/ObjVal` 与 Pyomo lower/upper 的 hex 必须一致。
3. Native 与 canonical 的目标系数、常数精确代数相同，native X 与 loaded assignment 的 hex 一致。
4. `abs(canonical_objective - ObjVal) <= 1e-9`，沿用原目标一致性限。
5. Gap 仅由原生通道计算：`(ObjVal-ObjBound)/abs(ObjVal) <= 1e-8`。
   ObjVal 为零时，仅 ObjBound 也精确为零才定义 gap=0；否则 unresolved。
6. Native OPTIMAL、Pyomo ok/optimal、solution optimal 同时成立。
7. 独立 canonical 重算约束/变量界残差及整数违约均不超过原 `1e-9`；
   原有版本、options、结构、来源、normal witness 及资源验收仍须通过。

变更是删除 successor 中跨数值通道的严格 `lower <= canonical` 排序，
并把 gap 的分母统一为原生 ObjVal。它改变验收语义，必须明确授权后才可接入正式 runner。
它不修改 LB，不做 epsilon/nextafter/clamp，不改变已冻结精度数值。

允许的结论为 `numerical_solver_optimality_accepted`：指定容差下的数值最优性接受。
`rigorous_exact_optimality_certified` 保持 false；selected-N-1、公开机制映射、
工程安全、完整未来服务和正式实验的其它门不会因此自动通过。

`ObjBoundC` 是保留的诊断通道；不作为额外数值关系门。Gurobi 对 `ObjBound` 可利用目标整数性
收紧 bound，而 `ObjBoundC` 不作该 rounding；不能仅因模型为 MIP 就推断两者相等。
本次 H25 直接观测二者 hex 相等。零目标的双零 gap=0 是本候选明确提出的自定义约定；
官方 `MIPGap` 属性在 ObjVal=0 时返回 infinity，因此本候选不是逐字复现该属性。
原生与 canonical 的完整约束矩阵并未作 exact equivalence 证明：该路线信任已固定的
Pyomo→Gurobi translator，再独立重算 canonical 赋值可行性；该信任边界必须保留。

开发实现 `src/solvers/rq2_normal_numerical_candidate_v1.py` 只计算条件性候选数值谓词，
输出 `formal_acceptance_authorized=false`。调用前必须通过父端 exact report/schema 验证与
独立 canonical 数值重放；调用者还须验证拥有的执行、输入来源和全部 witness。
函数接收外部保留的 runner/collector/adapter pins，检查 canonical hex、数值类型（拒 bool），
重算归档目标代数/点值和 assignment 对应，不把自报 algebra 布尔当作证明。
它不负责验证任意外部 dict 的来源真实性，也不替代 canonical 模型残差重算，
`candidate_numeric_predicate_passed` 只表示这些外部前置成立时的条件谓词，不单独构成 admission API。
配套测试 15 项通过（1.36s）：H25 归档值的明确合成 counterfactual、正负零目标、
零目标非零界、1e-9/1e-8 超限、界倒置、状态/通道/代数/赋值/残差反例。
此 counterfactual 不补造旧归档缺失的 native 通道，不更改旧标记。

限定预审后补类型/hex、实际 collector 输入、代数/常数/赋值/pin篡改、ObjBoundC缺失/非有限值、
负目标非零gap与边界例，最终29项通过（1.80s）。原15项是早期候选测试，不作为最终充分证据。

真实 H25 直接诊断已完成：原生下/上界及canonical值与旧记录相同；目标代数和赋值一致，
独立零 solver 重放也通过。记录在 `results/tables/rq2_h25_native_provenance_attempt1_non_authoritative/`，
重放在 `results/tables/rq2_h25_native_provenance_replay_v1_non_authoritative/`。
原生 Runtime 为直接保存的字段，与父进程227.921秒的wall分开；完整资源认证仍false。
记录 SHA `87cefb0f180f49d0315de24b761e85f4fa8dd27c85310ca944652e184f49979d`，
重放 SHA `bcaef6a3d35c30e8e5f15f296689565c24f7b8472d6f28a5a1cfd86163f1aa0f`。

独立领域只读审计及候选限定复核已完成，未发现新的实质科学矛盾；reviewer独立重跑29项通过（1.74s）。
真实记录在当前条件谓词下通过，旧严格谓词仍为false。

2026-09-28 用户明确回复“同意该数值验收修复，继续推进（推荐）”，授权上述具体数值口径及
successor 推进。该科学决策授权已完成，无需重复询问。sealed successor 及 fresh official review
仍须按 agent.md 第7节完成；不能把候选限定预审当 official verdict 或正式实验 admission。
