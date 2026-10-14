

### 2026-10-08 — H1 operational business 接线前 exact/clock 边界取证

后继 paired transaction 仍处设计取证阶段，尚未实现或验证 persistent lane owner。
旧 `BoundaryAnchor` 要求非负 source hour，不能为真实 raw0 虚构 raw-1；拟以内部业务相对时钟
保留连续 cohort/deadline 语义，并把真实来源对应保留在独立 audit。该映射尚待等价性验证。

`rq2_cfe_preallocation_v1.md` 的 operational 边界要求显式绑定 pair/hour/allocation 与转换记录；
旧部分 scalar 通道仅登记 float，本阶段没有新增舍入科学规则。
零 solver 探针 `results/tables/rq2_h1_operational_business_v1_non_authoritative/exact_boundary_probe.json`
证实：Fraction(1,21) 经 float 再按 decimal 重建会改变 exact 值；旧 `_effective_call` 对 exact
1/1000000 与 preallocation 的 exact threshold 判定也存在边界差异。
该阈值探针本身不证明合法 operational 输入会触发错误：common request mapping、CFE effective
过滤及 `_continuous_response` 已有前置域约束，需要在新适配中证明边界是否可达。
保持旧源字节、v2 阈值、12位 recovery 量化、q+r<=D、功率平衡与所有既有结果。
先完成保留 exact 值的明确适配和等价性/阈值邻域验证；无法证明的输入保持 unresolved，
不得删减完整支持或静默 float 化。真实 native/Job=0，正式门禁仍 false。
