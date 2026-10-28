# F：跨项目对象闭包的连续性校验组件

2026-10-28，DRAFT_NONAUTHORITATIVE。实现[完整retained producer合同](staged_deliverability_c_saved_fresh_retained_producer_lifecycle_scope_v1.md)的一项必要依赖；完整目标仍为同LIVE owner expectation/context/hold、G2/G3、cleanup与父端采用。root唯一writer，bridge_pre_seal独立只读PRE_SEAL。该组件不提供producer、closure初始来源或任何运行权限。

## 校验范围

旧namespace graph将foreign-global函数和ModuleType记为external identity，不能闭合跨项目producer依赖。新graph对完整声明的project module/source set递归链接project module、跨module function/global namespace、CodeType及嵌套code/defaults/kwdefaults/annotations/function dict/closure cells、class bases/MRO/vars、staticmethod/classmethod/property/slots/descriptors、dataclass fields/params/default/default_factory/metadata，以及明确支持的containers/Path/GenericAlias/UnionType。cycles和aliases保相同对象身份。project globals对应的实际function.__builtins__字典与LOAD_GLOBAL/LOAD_NAME fallback一并观察；unsupported实例/partial/自定义metaclass/foreign project globals直接拒绝。

两次独立registry枚举核完整set、module身份及alias；module name/file/package/version及完整ModuleSpec/已支持loader实例字典（含loader_state、_cached、_initializing及额外data字段）递归观察并保身份。SourceFileLoader/SourcelessFileLoader/ExtensionFileLoader及builtin/frozen loader可观察；NamespaceLoader及其他未显式支持state拒绝。Source49以外但落在project root的module/foreign function不能当成stdlib external。project class的声明归属从给定源AST核对；静态LOAD_GLOBAL→LOAD_ATTR的module/class链也观察直接指向对象，不能只固定外部module id。外部stdlib/native直接引用仅列conditional TCB，其内部行为及初始正确性不获认证。

此snapshot只证明观测之间结构和identity连续：**initial_project_state_authenticated=false**，其余producer/full-runtime/P1/role/permit/resource/science/formal/F flags全false。source map是调用方提供的字节，不凭snapshot将其升格为权威；真正Source49精确装配、bootstrap issuer、独立初始module/class/default oracle和runtime许可仍须后续接线。snapshot不exec/import project code、不读源文件或P1；可供未来同owner full producer在已经认证的初始状态上bookend，不能独立授予该初始认证。

默认上限37 modules/50000 nodes/depth256/8MiB编码图及2MiB source bytes，构造时累计编码预算并在返回前复核，超限拒绝。mappingproxy只允许GC referent为exact dict的情况，不调用未知mapping方法。Path验证raw parts与派生str/parts/equality/hash一致，允许正常派生缓存。snapshot强持compound objects、source bytes、registry与metadata引用；检查creator PID/thread及seal，随后重建结构/身份/conditional metadata精确比较；不可复制或序列化。进程内id不写入对外graph/report，不供父端认证。实际接线必须固定registry is sys.modules，注入registry只是unit seam。旧NF9冻结profile中确有37个Source49 project module且无额外project file，但这只是已有profile元数据清点，不证明本图在真实module set上成功或资源达标。128MiB retention及全链wall/RAM/storage尚未实测；不调用旧40图帽或绕过它，新native接线需独立helper/预算后继。

## 本轮验证DAG及预算

普通unit仅12个synthetic module测试，共26帧，覆盖cross-module/cycle/alias、code/default/annotation/dict漂移、foreign globals、registry缺失/别名/换对象、project/conditional module的spec/loader可变state、直接外部函数替换、dataclass/slots/property/classmethod、unselected project class、closure cells、builtin fallback/字典置换、不支持值与有副作用mappingproxy、各cap、不可传递和false gates。synthetic模块在system tmp命名空间执行，自带有限builtins；不exec/import任何Source49目标模块、不读实际P1，也不调用原ENTRY context函数（后者会读P1 anchor）。独立fixture AST oracle不使用实现的dis/traversal/canonicalizer：从四个fixture源声明推导精确project module/function/class、global/builtin load及default-name edges，与观察图节点/边及held object身份精确比较。它只覆盖fixture；实际Source49初始化及完整运行时call-graph oracle仍OPEN。

普通短验证独立预算static25s/unit15s/总40s：register5、唯一unit10、PRE_SEAL5、saved5、checkpoint5，其余static5/unit5仅本包失败封存。root≤10文件/4MiB，每record≤1MiB，写入预留checkpoint1MiB；child≤8s、stdout128KiB/stderr32KiB、256MiB/process/512MiB pair sampled停止帽。旧预算/未用余量不转用。当前累计1125.7064325000204s、不接受41条；本包登记前费用0，新增模拟跨度0h。

完整正常路径：register（固定v3 checkpoint/完整继承及archive重建、own syntax、graph.current metadata）→唯一unit（parent前后check各1，child前后check各1，12项纯图测试）→PRE_SEAL前后check各1→saved前后check各1及26帧/内存/原流重开→checkpoint check内previous一次、saved canonical比较、独立费用和known pins。共previous10、graph.current10；每current只compile本组件一次并读49-source freshness，显式490次source读，旧链I/O另计；不重跑v3 derive/unit或NFC12。

精确继承：v3 previous1195 + frozen own7-overlap2 =1200；加入v3 root6中5个新文件为1205；本轮own7（program/test/scope/driver及已继承builder/capture/memory）overlap3，最终1209。archive旧162+v3 root6=168文件15673460B。registration/check与PRE_SEAL均需重建完整map/count/set，不接受动态删减。历史不接受按record续计，失败仍独立fallback保存charge/raw/known pins，无法证明累计时incomplete/null。
