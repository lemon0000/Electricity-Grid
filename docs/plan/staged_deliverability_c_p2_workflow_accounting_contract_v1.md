# C：P2整链会计与核验复用决策

2026-10-23，DRAFT_NONAUTHORITATIVE。接续[输入诊断](continuation_handoff_20261023_p2_input_cost.md)和[内部执行图](staged_deliverability_c_p2_runner_cost_review_v1.md)。本次只补纯元数据、源码结构与条件成功路径计数，不启动solver、公共P2、journal或重放，不更改旧输入/源/结果和任何运行权限。

## 复用决策

实测指纹的主要热点为原Distribution.files/存在性访问，preserve为历史stamp；packet单次profile仅0.0027545s。1281次完整指纹分别跨native、父端重构模/审计、finish或reopen，没有可直接删除的相邻纯比较重复。删除parent导入前或导入后的任一检查，将检测窗口移到另一侧；跳过未选RECORD路径可能遗漏原PermissionError。当前不具备全闭包freshness与失败窗口等价证明，因此保持原检查，不为减少调用而改合同。

仅缓存packet可使每进程解析一次，960→321，减少639次/163038294B逻辑读取；context解析1281→321可减少960次/239574720B。原工件hash、55/7源和legacy核验仍须逐位置执行。这两项只说明候选结构，不是已实现收益。Cursor目前浅tuple保留可变row；共享缓存将使请求方与核验方别名。私有模板/递归独立视图、首尾原始读取、解析异常和漂移窗口均须另证。即使稳定普通文件域内成功输出相同，也不能宣称重复open/parse失败行为相同。Windows文件handle不自动证明目录新增、ACL、既有映射等窗口；本轮不引入该机制。preserve仅三次，保留原样。

暂缓上述缓存，优先闭合journal、prefix、CAS增长和昂贵失败预算；该决定基于实际热点和未闭合语义，不代表C优化或整体性能审查完成。

## 会计范围和依据

固定原packet的319槽、十实际小时h=-2..7、h1/2两合同帧、69事故。只展开所有祖先成功、十小时均接受且无stop、一个committed terminal、两个完整reopen的路径。保留注册构造、outer、昂贵失败为独立范围；不把成功公式套到attempt/pending或terminal缺失。

工具仅从已保存packet/context/observation、P2七输入、原55准备源、原输入诊断的start/report/launcher/command及stdlib后核验锚点核对结构。固定三准备工件SHA，沿原保存source pins读取全部66来源；读取28个journal来源和10个external入口的**数量**来自已绑定源码AST，工具不读取外部应用文件、不重新验证旧机器性能。CLI在导入Reader前拒绝预载src/experiments，固定仓库package入口；随后核冻结Reader的module/spec、require和全部Reader方法的source/code身份，再执行读取。

另只读原P1五小时journal：由原683文件postcheck锚点绑定genesis、六entry及130个CAS文件，按typed-wire的ref标签计算fixture、初态、逐hour payload/state和terminal闭包，核after_cas_keys与链，投影各epoch的对象数/字节及加权inventory逻辑读取。再核原33份进程observations，交叉验证五小时175 selective/551描述、4 full/570描述、129指纹及185 journal runtime等已观测计数。不实例化科学类型、不调用pack或reopen、不重新判定科学结果；只说明原五小时前缀的保存拓扑，不能外推十小时。闭包解析须拒绝缺失引用、cycle、未知tag及伪ref形状，普通list/dict中的ref字符串不能误作引用。

新增工具、测试和本合同组成三个本轮绑定输入。一次纯stdlib机械CLI，独占`results/tables/staged_rts24_p2_workflow_accounting_v1_non_authoritative/audit_01/audit.json`，零重试；复用已冻结Reader，单文件≤2MiB、Reader合作式读取20s，末端全量bookend，输出≤512KiB。bootstrap固定package/Reader身份读取另记，≤4次/64KiB且每文件≤32KiB；总数合并Reader及bootstrap须≤1800读取/12MiB。该逻辑字节账不包括解释器/标准库/模块导入的OS IO，metadata Reader计时不含导入与bootstrap。阻塞OS IO无硬实时承诺。不得导入科学模块、调用任何原指纹/packet/compiler/native/journal或创建P2注册/执行目录。普通测试使用算术、AST、保存元数据和tmp，不执行科学路径。CLI只产生机械会计，计时不作代表性能证据。

## 需核对的层次

1. 321次内部CLI、960 load、1281 fingerprints、3 preserve及319点/4构模/2import会计与packet角色一致。
2. writer `_check`、journal runtime、root/CAS inventory、root-file和chain-prefix访问分别计数；inventory次数不得当作CAS对象或字节数。
3. writer及两reopen的prepare/propose/accept、audit/context/summary、历史row和reference请求重建展开，编译器calls和请求描述数分开；动态replace、审计内部和codec递归未穷举时明确列缺口。
4. CAS扫描用各阶段库存大小表示，标明payload/state更新中间态；没有公共十小时保存对象就不填字节预算。source/code/输入首尾保持、独立AST/显式调用轨迹oracle、原保存字节复现和只读PRE_SEAL审查均须完成。

输出create-only，核完整write、flush/fstat大小与身份、close后ordinary/非reparse/单链接及原字节读回，再打印绑定output pin；输出读回单列一次≤512KiB，不混入输入读取账。写入/关闭/读回异常保留partial目录并非零退出，不覆盖重试，也不报告采用成功。

不据输入诊断单次profile时间乘总次数；单点10s/solver5s、全包3600s、fresh60s/outer65s仅原提案停止帽。真实坏盘/阻塞IO、native失败、parent收尾余量、十小时CAS/摘要增长及整个成功/昂贵失败成本仍需证据。C整体、139数值/F-X时序、D/E现实输入/选择/留出和资源准入继续OPEN；原P1一次native授权已用，新native仍需专项授权。无official verdict/receipt/seal。
