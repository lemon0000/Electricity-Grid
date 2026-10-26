# C：单点保存raw科学重建开发合同

2026-10-24，DRAFT_NONAUTHORITATIVE。按[科学采用DAG](staged_deliverability_c_scientific_adoption_dag_v1.md)只实现节点C。root唯一writer，agent第7节只读独立PRE_SEAL审阅。原数值接口、backend、audit、codec、journal、outer、七输入及已发布字节不改。

## 入口与边界

新增纯读取函数接收point root、调用方持有的完整预期BoundQuery/请求frame、完整point库存pins、外部所有权process记录和当前选定source pins。预期query不从该point CAS生成；后续与完整B图的独立来源绑定单列。支持原P1请求形状和原P2多出的execution_binding；按各自闭合字段比对，不为适配修改原记录。legacy outer可含原DRAFT authority字段，仅显式核该固定tag后用原process schema验quiet；保留原record SHA，不改其字节。guard v3走原parent v2。quiet未知在任何point/source读取前拒绝。

双库存沿用已验证机械reader的ordinary/path/fstat/祖先/长度/8MiB单文件/64MiB总量/8192文件/depth边界，完整库存必须等于调用方pins。point固定八个root文件及普通CAS；process按原10s自报帽、完整成员/HANDLE/owner及outer集合闭合，numeric子退出2单列。原P1/P2 monitor扫描整个package，故terminal计数须不小于本point去除process.json的库存，而不能要求局部与历史整包计数相等；全历史package计数未独立重建，不能用此下界作资源准入。log读取以SHA/长度绑定，记录的历史log_file须为规范绝对字符串，但允许保存包迁移后实际路径不同，不重写历史raw。

源书挡固定选定源码组，并核实际加载的compiler/backend/audit/codec等module文件。不是完整runtime/native闭包。typed query必须精确等于预期query，CAS identity也相同；query父链至多一层，网络不超过原RTS-24的24 buses/33 generators/38 branches，禁止超范围构模；32个QP二次项不等于发电机条目总数。imported族固定由query决定：root经济QP、anchored非经济child LP、anchored经济primal-only，不接受调用方选择较弱证据族。

## 数值与保存状态

逐一核request/result/raw/log/observations/process引用、registration和runtime pins、ordinal/hour/role及P2 execution_binding；P2必须有非null注册SHA。raw字段按原writer成功形状闭合，numeric可另含原error/artifact_error/extraction_errors；observer固定原五字段与scope、非负有限counter/time域，不接受额外authority或adoption声明。独立compile→原snapshot_from_raw→原import_snapshot（含其第二次compile及独立审计）；再调用原代数audit返回残差、gap和原容差。重建PointEvidence的typed-CAS根SHA必须精确等于保存evidence_ref，包含float.hex的signed zero，不用float宽松相等替代规范字节相等。CAS库存恰为query/evidence完整闭包。

numeric_unresolved仅在原UnresolvedNumeric重现、保存status/error同类同消息、evidence_ref为null、CAS仅query闭包时返回；不返回可用point，不推数学不可行。malformed原始payload、options/getter/cleanup或记录矛盾直接失败，不能吞为numeric未决。错误、partial或numeric不能升级为imported。

结束前完成CAS reader书挡、第二完整库存、源和调用方预期query/frame书挡。任何漂移不返回成功；全函数无solver、spawn、CAS put、publish、journal/reopen或持久写入接口。返回仅是局部数值一致性及精确hash报告，scientific_evidence_adopted、journal_replayed、full_139、F/X temporal、rigorous certification、resource/formal全false。

## 有界验证

普通测试采用独立给定primal/dual的两母线解析QP、child LP和primal-only，手造raw记录，禁止Highs/solver factory/backend call。核2次构模的实际调用数、root/child残差、full evidence SHA、signed zero、警告/无dual/时间未决、raw/log/CAS/预期query/frame/来源漂移、未知quiet零读取及无输出写入。旧数值/代数/codec窄回归复用原语义。

只读P1回归至多原31点中的三代表点各一次，使用已保存raw和独立当前原compiler构造的同请求；调用方先验证原P1全库存，不启动native。普通测试命令90s上限、无自动重试，失败保留；不另立性能experiment或运行完整P2/journal。若成本超界，先保留终态并定位，不扩大帽。此验证不关闭B/D/E/F、整体65s余量或资源门禁。
