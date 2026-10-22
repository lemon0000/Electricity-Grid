# 连续证据保存与只读重放后继

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。接续[连续业务规格](staged_rts24_causal_development_v1.md)，保留其已绑定八源和B1–B3字节。公共网络方向保持RTS-24，机制回归继续使用小例。本后继只实现实际路径证据的保存、关闭及重放；公共normal C、69事故F/X和完整反事实业务时序分别按原C计划继续。

## 请求与科学语义

[reference_requests](../../src/staged_rts24_reference_queries_v1.py)仅构造P0、实际事故raw和方法需要的恢复两端，数量为`1+I_fault+2I_noninstantaneous`。完整合同编译器保持原样；公共S=69时，每次省去139个未消费合同描述。selected索引仍逐项轻量校验，不省略输入拒绝边界。有效fixture域内请求字段、顺序、身份及消费元数据与原full compiler过滤子集相同；多个非法输入同时出现时不承诺异常先后完全相同。

[causal_v2](../../src/staged_rts24_causal_v2.py)复用v1类型、初始化、固定策略及父/child数值审计；驱动只改用上述子集。[audit_v2](../../src/staged_rts24_causal_audit_v2.py)继续独立重算策略、功率、cohort、永久期限缺口和carry。数值容差、Fraction业务编码、actual完整点/零额外curtailment、approx假想账本与full实际接受前缀均按v1。没有通过少审历史换取速度。

## 无损CAS

[保存层](../../src/staged_rts24_evidence_store_v1.py)使用固定20类型白名单和精确字段类型；原注解中的object在codec中明确收窄。Fraction使用约分整数对，有限float使用hex保留负零及subnormal，tuple/list/dict分别编码。禁止pickle或动态类导入。完整frame、query、父点/经济证据、child LP、状态和业务证据作为SHA对象引用；小型bus/gen/branch及参数等内联。CAS身份包含schema、kind和typed payload，与原科学`c.digest`分开。

先在内存形成规范编码及完整闭包，核深度/节点、单对象8MiB、闭包64MiB/10000对象，再检查已有目录与新增出版预算；超限不先写入。JSON在递归解析前扫描深度/节点。get重建白名单dataclass后纯编码回算CAS SHA，拒绝替代wire、错误字段类型、错误hash、缺引用和循环。

同一次同步put可按对象身份复用编码；一次reopen使用单个ReadView复用已解码对象。操作结束逐一重读所用对象，并核完整目录inventory、目录dev/inode及runtime pins。缓存不跨小时写入或新的观察操作。已有final与pending冲突拒绝；pending不会参与普通dedup。没有消除完整state中的历史引用列表或科学hash的O(T²)成本。

## Journal、检查点与终态

[journal](../../src/staged_rts24_journal_v1.py)限定Windows本地单writer。独占目录、不可覆盖genesis和连续ordinal条目；CAS先写，条目后写。每次文件发布为独占pending → write/flush/fsync/close → pending读回 → 同目录不覆盖rename → final读回。文件及父目录链均拒绝reparse，CAS文件拒绝hardlink，目录身份首尾检查。选定源码/解释器文件可保留Conda合法hardlink，但核其文件字节。

genesis绑定完整Fixture的科学SHA及typed根、初始状态、plan/clean/method、codec和选定源码/环境。旧fixture.source_identity不足以覆盖新模块，因此额外绑定新五源、直接复用的v1/point/child/debt模块、实际import入口、三份输入配置、Python以及六包版本/十个外部入口源。它是显式选定闭包，不是完整生产环境seal；导入highspy不等于执行native。

每小时begin先prepare/propose，actual由调用方显式提供；commit重审实际点和完整候选state，再额外独立audit。只有条目final读回和末端绑定通过后，writer才采用candidate。hour已journal保存与`actual_accepted`分别表示；approx只采用其hypothetical账本。finish保存完整state、summary和独立audit检查点，区分complete、known_rejection、missing_input和right_censored；覆盖完成不保证方法或完整约束通过。

缺reference/child或数值身份、最优性未决：保存reference attempt；已形成proposal而actual缺失或绑定未决：保存actual attempt。attempt保存当前observation、完整已有证据、请求身份、已形成动作及可重演异常，固定adopted=false、无after-state，不改变ledger。已被投影/连接排除或actual完整点已知失败仍由内核保存known rejection。缺下一输入时不生成未来任务；永久逾期和右删失沿最后已确认前缀结算。

rename开始前异常保留旧状态并关闭；rename开始后至完整读回/bookend结束异常为publication unknown，本进程不采用或续写。failure为尽力保存的本地诊断；真实阻塞I/O、坏盘、掉电、kill、失败诊断无法写入均没有获得耐久性保证。不提供并发lease、自动重试、GC或可写resume。

## 可信只读重开

调用者须在journal之外保存`trusted_binding(session)`：genesis、已知head/ordinal/state SHA、关闭/科学/发布状态以及failure SHA及存在性。fresh reader同时接收外部构造的完整Fixture和plan/clean/method。仅给genesis不能证明尾部完整，因此API不接受这种弱绑定。

逐条重建完整父/子证据，重算请求、KKT/LP、固定策略、实际P、所有状态和独立审计，逐字段/科学SHA/typed SHA比较。正常尾部精确匹配可信count/head；unknown只允许可信failure指向的额外一条final。有效final可确认采用；仅有效pending可证明观察但不采用；缺失final/pending且may-publish为真则未决。删hour、terminal或failure、改may/outcome、错误前后链、未知文件和terminal后suffix均拒绝。

pending terminal单列检查点，不称未接受arrival。CAS pending和未引用final单列，后者仅字节/hash/envelope核验且不具科学权威；不得由orphan推导观察或采用。ReadView仅缓存同一次重开，所有已用对象和依赖有末端核验。返回只读结果，恒有resume_permitted=false。

## 检查与成本边界

普通测试覆盖public请求子集、多步跨版本状态、独立审计、codec保真/反例、可信尾部、缺输入、未决、已知拒绝、CAS及journal发布阶段和同操作缓存freshness。另按[探针合同](../plan/staged_deliverability_c_journal_probe_contract_v1.md)登记一次三方法五小时、三fresh child和五失败/缺输入路径的解析集成测量。普通测试wall不充作整链准入；该探针也不能给出公共g或公共网络性能。

公共真实normal C/P0、child和actual数值证据、native提取/终止、长cohort、完整F/X时序、昂贵真实失败收尾以及D/E点数/资源仍OPEN。下一native包先具体登记，再取得专项授权。
