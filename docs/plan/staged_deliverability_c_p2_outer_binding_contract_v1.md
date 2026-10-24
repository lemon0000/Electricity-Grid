# C：outer启动绑定与quiet后保存开发合同

2026-10-24，DRAFT_NONAUTHORITATIVE。接续[双记录交接](continuation_handoff_20261024_terminal_budget.md)。root唯一writer，按agent第7节进行只读独立PRE_SEAL审查。本轮只开发版本化父端组件及checker v2，不创建公共P2注册、production manifest/lease，不执行原P2/native或长实验。原七输入、guard v1–v3、parent v1/v2、packet、B1–B3/P1及已发布字节保持。

## 输入与DAG

沿用原kernel注册和55＋7＋6来源的原字节，在独立outer context中另绑定9项successor代码/测试/合同；不得向原注册加键。context持有原package context、两份128KiB/文件槽、受控environment摘要及新来源pins，均为development/authority false。读取核完整原输入和新来源的首尾；loaded module路径/字节与登记源码一致。选定源码闭包不冒称完整runtime/native/OS证明。

正常路径为：读取/持有context→在专用worker目录create-only保存`outer_context.json`→原launcher_start和两日志槽→以固定argv/cwd/environment/commit限构造原OwnedChild后继→在release前直接捕获parent PID、child PID/FILETIME、传入CreateProcess的argv/Windows命令行/cwd/环境摘要及context SHA→create-only保存`outer_startup.json`→重新核输入及目录→原release→guard v3监督/quiet→仅quiet已知时保存有硬帽的launcher.json→checker v2完整元数据/来源书挡→parent observation v2保存及最终组合会计。

新增两文件在worker开始前存在，进入原worker completion core且计入guard的实际worker库存；不增加terminal后两文件reserve。parent不嵌入context或startup全文，既有记录长度合同不变。新checker按完整原字节检查两文件及其completion/SHA引用，不删字段、不改旧manifest后投影。319/138/10与内部guard v2语义保持；仅外层process按guard v3/parent v2核验。原checker保留原拒绝行为。

## 启动事实的边界

启动捕获来源为父端实际成功构造的suspended、已在owned Job中的HANDLE与PID/creation，不从worker日志推断。Binding在创建进程/线程内使用，捕获、release和finish逐次核同一creator及child owner身份；未尝试构造不能finish。捕获固定发生在release前；context/startup写入或输入漂移失败时尝试关闭原owner并如实保留cleanup未知，禁止release和自动重试。保存的事实证明父端调用了绑定的CreateProcess参数；checker独立返回的`startup_record_schema_verified`只表示持有字节/schema及owner关联一致，不单凭JSON证明真实捕获。独立OS command-line查询、完整进程亲缘、整个runtime闭包仍为false；不能由一份可传入的JSON授权运行。

组件没有P2 execute/注册CLI。普通短Python子进程只用于验证真实owner捕获和收尾；P2元数据采用独立合成保存包，二者不拼接为实际P2执行。prepared context不启动worker。任何将来真实P2运行仍须具体新包、资源/时间审查、相应seal/review及专项native授权。

## 失败与保存

context、startup、launcher沿原codec pending/fsync/no-overwrite rename/readback，已有target/pending不复用。构造/捕获/发布失败尝试关闭创建中的owner；若关闭也失败，专用未决异常及Binding同时保留原owner能力、capture/publication phase/SHA/may-have-published与两个有界错误，cleanup/quiet显式unknown，禁止release或重建，不把构造异常当作资源已关闭。release后失败由原guard清理，不接管或猜测未知quiet。quiet未知不读取worker或保存worker launcher，仅在独立父目录保存process诊断。quiet已知的非零退出可只读捕获failure库存/数值诊断，parent v2仍按原成功回调门禁保存失败process观察，不把诊断当成功采用。

成功回调直接消费本次checker结果；不重复同一完整科学或元数据重放。首次写入前也核已持有目录与输入，unknown quiet分支仍核独立父目录identity。发布后再次核输入、worker祖先identity、outer context/startup/launcher原字节及parent最终记录；外层书挡失败也携带已发布parent SHA、may_have_published与未决状态。父记录saved不等于package完整或科学采用。所有139/F-X、resource/formal及科学重放字段保持false。

## 验收与成本边界

窄普通测试覆盖：真实短Python owner→release前fact→quiet→launcher/parent；wrong argv/cwd/environment/limit、context/SHA/注册或新来源漂移；startup写前/写后/rename后失败和owner关闭；重复release/finalize/已有pending；unknown quiet零worker访问；保存包中两新文件/owner/context/启动事实篡改、完整319协议及failure库存；旧checker拒绝新root文件、旧七输入/绑定及旧父记录长度证明不变。

每次outer输入书挡=一次原read_inputs的76次内容读取＋9项新来源及4个已加载新模块校验；context构造还含原context准备85读、9次新来源捕获和两次完整书挡。owner捕获/释放/最终采用的边界不能跨调用缓存。checker复用原完整两库存/319引用路径，并加两文件原字节比较。每一文件处理仍遵守原8MiB、总64MiB/8192及有界metadata规则；record cap与1024历史成员帽不放宽。

普通测试限pytest tmp，单命令90s硬停止/零自动重试，不构成P2性能测量。capture、来源复读、双库存、fsync、失败收尾及总wall/RAM/storage仍需代表性成本。fresh60s＋最多5s收束相对65s无进展帽仍OPEN；本轮不放宽或绕过该门槛。完成本单元只形成开发证据，C整体及D/E现实输入/方案/选择/敏感性/冻结后留出仍OPEN。
