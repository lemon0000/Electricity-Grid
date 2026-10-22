# 当前阶段输入的逐字段来源登记合同

2026-10-23。DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT。接续[来源缺口](../literature/staged_parameter_source_gap_20261023.md)和[阅读版交接](continuation_handoff_20261023_methods_pdf.md)，root唯一writer。本包仅做静态来源登记与元数据核对，不构建电气模型、执行公共case函数、求解或启动实验；不修改三份原YAML、既有实现、B1—B3、P1权限或D/E范围。

## 覆盖与来源

[sidecar](../literature/staged_rts24_parameter_provenance_v1.json)逐标量覆盖public 40、business 60、rights 32，共132个叶字段。数组逐元素，JSON pointer采用RFC6901转义，保留叶键为str/int/index；旧actual_outages的整数键1不能与字符串键混淆。禁止重复、规范化碰撞、别名/锚点或未分类字段。三配置原始SHA及13项实现/定义/辅助审计参考SHA固定，包含Parameters/METHODS、有效causal_v2、所继承v1策略、reference_requests、独立audit_v2、债务和点/child审计；输入、引用或case源码变化须重审。

每行记录原值/类型、单位、原始来源类别、公共运行采用方式、直接来源pointer、语义角色、变换结果、经验资格及主张边界。来源类别与采用方式分开：公共case的包/版本/SHA只是来源绑定，不是经验观测；业务、设备、权益、清洁、期限仍是机制假设。精确缩放不提升来源资格。

37个字段按现有显式规则乘200：business参数7项、设备容量/待机4项、workload前后2项、前史与两条Y路径17项；rights四项和X包络功率/爬坡/能量3项。无量纲、时间、事件数、公共网络与工程增量不套200。public_value_record只表示输入级变换，不是逐小时实际值；前史f=0和Y规则另列。early/late只是开发清洁时序，不是业务快慢或holdout。

旧rights.network的17个字段和small.grid的四个标量/临时字段不被公共运行采用。small.grid时点只作与public.project的一致性核对；small.grid.before/after另在已存必要条件审计中核对缩放后F+X，旧rights.network四个工程时点字段也在该审计作三源一致性guard，但不提供公共运行能力。辅助用途清单明确限于选定来源一致性guards，不穷尽该审计的数值消费。旧response标签只存source_response_model，新标签是当前响应声明；actual_event.rule是固定标签guard，实际取selected[0]。rate_C增量进入网络对象身份，当前DC约束仍使用rate_A。

公共case仅以固定源码SHA和AST字面量读取baseMVA/bus/gen/branch/gencost五组，核对100 MVA、24×13/33×21/38×13/33×7及组内摘要；不导入PYPOWER/NumPy或执行case函数。这里不是逐公共数组单元/全部运行分支的分类。公共负荷按PD+GS乘4/5，tap零转1、移相角转弧度；原MVA-labelled rating数值按既有DC实现作为MW限额使用，不提供AC换算或工程认证。原引用与BSD式许可只按本机case源码声明记录，不新增网络/法律核验；无外部下载。

## 静态核对路径

[checker](../../src/staged_rts24_parameter_provenance_v1.py)以显式require/ValueError检查，关键门不依赖assert。先验固定源SHA，再解析3个小YAML；按独立审阅的采用映射构造期望内容，与sidecar进行包含类型的完整规范化比较，拒绝缺行、重复pointer、误分类、误缩放、错误单位、额外字段或擅改unknown/权限状态。该重构是元数据一致性检查，不称独立科学oracle；映射事实仍依赖领域审阅与原实现。

只读CLI读取sidecar、三个配置、case字节、13个引用及自身，共19个显式文件、38次文件读取，首尾字节一致。另对12个参考Python文件作AST词法核对：Parameters恰14字段、METHODS恰三种，策略/功耗/请求链合计覆盖14参数，独立audit覆盖同14参数，v2/audit各读6个X包络字段，五条选定导入关系存在。此项是词法见证和源SHA绑定，不是执行、完整数据流证明或环境依赖闭包。

registry≤512 KiB、每YAML≤16 KiB，固定132行和五组字面量，无循环重放、子进程、模型或结果树写入。解释器、导入、包metadata发现的IO不在19文件计数内，不称全环境seal或系统硬IO/RAM上限。CLI只向stdout输出非权威摘要；外层保存日志与结果时create-only，保持失败记录。

普通检查覆盖完整性与typed equality、37项缩放手工锚点、未采用/guard/标签/属性边界、Y与deadline限制、重复YAML/JSON及碰撞/别名拒绝、源漂移、公共AST未执行，以及优化Python下错误sidecar仍被拒绝。只读领域/独立审阅完成后才形成本轮保存观察；无official verdict、seal或receipt。

## 输出与未决

保存静态观察于results/tables/staged_rts24_parameter_provenance_v1_non_authoritative，日志另存results/logs。记录绑定本轮实际源/测试/合同/sidecar及证据字节；后续修复或扩大来源范围使用后继，保留本轮字节。原方法正文/PDF保持，来源页只新增登记入口及准确范围。

完成本包只闭合当前三YAML的逐字段来源可追溯性，不校准真实设备、任务、SLA、合同、清洁归属、工期或概率，也不穷尽非YAML策略选择。公共g/电气点、139静态节点、完整F/X反事实时序、C/D/E资源、主比较、选择和独立留出仍需原证据与授权；P1专项授权仍未答复。
