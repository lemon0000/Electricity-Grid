# C同append打包与库存核验后继合同

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。接续[保存成本审查](staged_deliverability_c_retained_cost_review_v1.md)及[受控P1交接](continuation_handoff_20261023_native.md)。本开发独立于待授权P1：旧B1–B3、codec、journal_v1/v2与native注册13源/23577…94e2保持，不接入或运行P1，不创建production候选、lease、seal、receipt或运行权限。

## 范围与可证目标

新journal_v3延续v2完整retained CAS/root/链/runtime/目录检查、全部独立科学audit、hour/attempt/terminal、trusted binding与只读fresh。新私有batch层仅服务同一同步append：使用该次_check刚核验的CAS清单，payload/candidate各调用旧pack一次，核合并SHA/根闭包/冲突与联合预算，按首次出现顺序发布去重对象。新key使用旧exclusive publish，旧key缺失或改变不得重写修复。返回的是期望集合；entry发布前及采用前仍各作全量CAS和root核验。不得跨begin→外部数值→commit、多个append或fresh复用快照、blobs或state digest。

为了避免hook修改可变records/row，先在同append整体深复制(session,payload,candidate)，保留共享引用；后续entry、检查、发布、采用及failure均使用隔离session与输入。entry前后重新提取原session全部字段、payload及candidate，以带memo的typed比较检查仍等于快照（root取路径字符串），同时检测字段重绑与嵌套修改。保留精确类型、float.hex和Fraction语义，不用Python宽松等号代替wire等价。任何不一致均不采用，entry可能已发布时留unknown，交独立fresh裁决；不清理pending/orphan，不恢复写入。

成功append的根pack预计4→2、完整CAS inventory7→3；包含begin与commit检查的成功hour为10→6，finish为8→4。attempt一根pack2→1，失败路径单列，不补成成功计数。genesis与fresh策略不优化，旧科学审核及最后CAS/root/runtime/目录检查保留。隔离复制、typed比较、重复runtime核验也必须计入成本；只有结构计数减少不能宣称wall提速或复杂度降阶，累计key/state物化与完整扫描增长仍存在。

## 普通检查与失败窗口

只在pytest临时目录生成解析三母线例和小型CAS；不调用solver/native，不运行新的性能attempt。检查至少覆盖：

1. 三方法逐小时/finish/reopen的完整state、digest、CAS根/字节、summary/audit/outcome等价；v3 schema及runtime元数据单列，不冒充v2 root哈希相等。
2. 实际pack/inventory/publication调用计数，共享闭包只写一次，Fraction/负零/次正规数保持原wire与身份；合并超对象数/字节预算及不合法root/类型在写盘前拒绝。
3. 旧CAS、genesis/旧entry在初始、prepare、外部等待、CAS发布与entry发布窗口删除/篡改/新增；目录/依赖漂移及伪造session库存拒绝。新key预创建不能冒充本writer，旧key缺失不能修复。
4. CAS/entry各publish阶段注入，reference/actual/audit未决、known rejection、missing_input/右删失、terminal pending/unknown、failure witness保存失败；writer不采用，fresh依旧独立读取并核完整可信闭包。
5. hook修改原payload/candidate、嵌套row的数值类型或signed zero时拒绝；隔离快照不污染旧接受前缀。fresh读后修改、可信keyset/head/failure篡改仍拒绝。
6. 相关旧回归、旧工件/source/registration SHA首尾核验、AST/diff/链接检查与只读sol_reviewer PRE_SEAL审查。

若需要代表整链wall/RSS/storage测量，另固定具体来源、DAG、次数、资源和停止条件，再按agent.md第9节执行；本合同的普通检查不代替该测量或D/E准入。公共点/g、真实dual/日志与公共保存成本、完整139/F-X时序和C/D/E整体预算仍OPEN。待授权P1继续沿原v2包；采用本后继必须独立重登记并另获对应权限，不能改旧注册字节。
