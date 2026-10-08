# H1 审计性能 successor v3

## 范围与不变量

2026-10-02 用户要求解决 v2 单次校准超时。风险为 R3：改变实现及计算身份，保留 v2 科学规则、阈值、原模型、求解器、232-stage 顺序、5s/stage、3600s task、2GiB Job 和一次性执行边界。旧 v2 封存包、消费记录和超时结果不修改。开发、保存数据诊断、pre-seal、封存及独立审查属于本次修复；新 native 运行另需明确授权。

v2 原始 native Runtime 合计7.084s，232-stage完整独立重放309.415s；task在3598.047s截止后保留232 stage_accepted，但只有预登记的terminal checkpoint。完整raw不替代terminal、fresh reopen、worker_result或job_checks。v3不恢复旧attempt。

## 实现

generation_projection_v3公开project_and_audit入口每次重建一个canonical H1模型。保存canonical fixed值；raw与candidate分别加载完整赋值、独立计算变量界、fixed偏差、所有约束、整数性、strict locks和chronology。legacy normal residual只在计算期间暂时deactivate新增H1 locks，并在finally恢复，等价于原normal模型约束集；其独立chronology与原错误顺序保留。调用结束重新计算stage input/lock/dependency identity；阈值在审计边界复核。模型不跨调用缓存。

每次_audit_stage构建一个canonical模型，在native numeric赋值前生成独立clone交给私有candidate审计入口。运行时检查模型类型、变量对象独立性、完整变量名、fixed标志及基准hex、locks激活状态、scale和structure一致。native numeric与raw/candidate审计使用独立模型；模型构建为一次H1/底层构建加一次clone，替代v2的四次H1、六次底层构建。

完整归档在同一owner内可复用已经审计的同一snapshot数值结果。每次读取仍开启新的SQLite事务并完整扫描全部raw、metadata、chunk/predecessor/hash链，再复核packet、spec、limits、来源、实现身份和冻结阈值。缓存key绑定完整physical inspection与语义身份，receipt按精确类型和canonical digest复核；仅缓存awaiting_terminal或accepted，partial/rejected不缓存。完整prefix在同一事务完成metadata与数值审计，可同时保存awaiting inspection和候选projection；awaiting inspection不发布projection。新增terminal head必须重新完整数值审计；fresh owner缓存为空，必须独立完整数值审计。任一snapshot读取或缓存异常清空缓存并毒化owner，后续操作拒绝。checkpoint、fsync和anchor顺序不变。

raw、candidate、receipt字段与v2一致，科学rule_identity仍为原v2规则身份。优化实现的identity额外绑定v3 helper及直接normal依赖，stage replay、archive、collector、resource、Job和gate使用独立v3计算/包身份。底层native capture及Windows Job controller保持原实现。

## 冻结验收矩阵（封存前完成）

1. retained v2的232份raw逐stage重算：native SHA、model stage identity、numeric SHA、lock hex、完整mapping receipt全部一致；完整projection物理units与locks一致，v3的计算/归档identity可不同。
2. 独立旧audit oracle比较正常、负generation、strict-lock-only、变量界、fixed、整数性、功率平衡和chronology反例；raw不可变、candidate失败仍拒绝、阈值边界和目标hex规则不变。
3. canonical fixed基准不可被先前raw赋值污染；NaN/inf/bool/missing/extra拒绝；输入或阈值在raw/candidate边界漂移拒绝；临时lock activation在异常后恢复。
4. tiny完整collector/worker replay、独立fresh reopen、checkpoint/anchor先后、持久化不确定失败窗口、禁止retry与gate缺失/篡改/身份反例回归通过。
   clone隔离与fixed基准污染反例、同head仍完整scan、raw/metadata损坏、数据库替换、receipt/type篡改、阈值/来源/spec/limits/实现漂移、scan及cache写入异常均须拒绝；新head和fresh owner须重新数值审计。
5. 在独立non-authoritative目录以真实232份保存raw替换唯一capture seam、已安装solver_calls_forbidden下完成整条worker，包括terminal/outcome/fresh reopen；每次stage审计均与v2保存oracle比较。实测offline完整worker目标小于声明non_solver_seconds=2440；它不测native capture耗时、不执行Windows Job监督，不是资源充分性或native成功证据。
6. 新旧sealed成员及原run inventory保持，source闭包包含全部v3源码、worker/prepare/diagnostic、tests与本规格；diff及process检查通过。PRE_SEAL findings闭合后封存，再由全新只读reviewer给official verdict。

## 证据边界

保存raw benchmark属于开发验证。其worker_result所在根明确为saved_worker_non_authoritative，mocked capture调用数不是新的native solver次数。完整研究资源、共同Rref/A与完整支持LB/UB继续待完成；正式结果与资源/执行ready标志保持false。
