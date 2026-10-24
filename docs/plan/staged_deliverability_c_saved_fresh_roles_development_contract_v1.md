# C：F parent／fresh 编排与发布开发合同

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[阶段监督交接](continuation_handoff_20261025_saved_fresh_stage_owner.md)及[原F范围/预算](staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)。root唯一writer，按agent.md §7做独立只读PRE_SEAL。继续实现完整F，原source集合SF49、P1/原B/C/E/guard/outer及全局门禁保持。原三个draft未seal，可迭代并保留每次已测snapshot。

## 本轮实现路径

在原ENTRY和测试中连接角色driver、create-only输出及固定RAM relay。parent从外部context独立重建并保存自身payload；预扣一次fresh后创建suspended nested owner，直接保存真实启动事实，release/监督；进入inner_quiesce前向上层parent channel发布该真实阶段，完成owner/channel close后进入inner_terminal。内层process记录和独立fresh_parent观察完成后，才读fresh payload，做完整比较/G1及保存候选，再退出。controller持有外层Job，完整quiet后才读取child候选，核两个启动/完整记录/候选，再保存外层观察及末次书挡。进度与阶段必须对应真实操作，不用定时心跳。

fresh阶段表示已经扣除一次性reservation并开始40s含capture的窗口，不表示已启动成功：先锁存reservation→写fresh phase→在同一预算内构造/capture→保存startup→release。构造失败不退款/重试。不能把capture移到fresh phase之前从而漏计原F1费用。ordinary小caps也按同一reservation时刻计算total。

role relay只允许fresh→parent、parent→controller两个固定pair及相同context SHA/源绑定；固定phase顺序。relay失败先安全停止并保留primary/cleanup层，不允许失败的通知跳过quiet。原ordinary stage API继续只接受闭集probe ID；新连接探针也用源码固定fixture/程序和严格pytest输出目录，不接受任意argv、callback或脚本路径。

这些箭头表示观察转入本进程自己的上游writer，绝不代写child channel。fresh的channel仅fresh写，parent主线程在watch fresh时写自己的parent→controller channel；controller直接读取parent帧。本轮controller无external绑定channel时relay=None，outer_quiesce/outer_terminal只保存本地时刻。若以后存在external持有的独立controller channel，才可用parent→controller pair把parent已接受阶段写入controller自己的上游channel。

停止次序固定：已有primary/timeout时先direct kill→best-effort inner_quiesce通知→完整quiesce/最后channel书挡→owner close→channel close；上述quiet/书挡/close均成功才发inner_terminal。该通知表示进入记录发布阶段，不是采用；child失败而cleanup成功可通知后发error。relay自身失败首次锁存并立即kill，再继续收束，不覆盖primary。100ms mutex等待计入原deadline，没有通知重试。

使用同一driver的普通解析fixture固定为小整数运算，parent/fresh分别在各自新进程重新计算；输入/比较对象与保存P1科学schema明确区分。普通fixture不读P1、不构造model/Highs、不产生saved_P1 verified。生产adapter连接仅在原F context/actual entry验证后可达，实际F CLI仍关闭；完整五小时fresh不在本批次执行。最外trusted invocation、constructor/kernel阻塞、controller自身资源和root端同步文件I/O停止能力继续按原F合同验收，未闭合前不开放F准入。

当前actual saved重建/书挡/比较分支复用原adapter，但实际owner/entry仍只允许ordinary闭集；生产路径尚未接通，不能把普通连接通过称为saved F通过。G书挡在普通fixture中只证明调用次序/拒绝窗口。

| 输入书挡 | 进程与精确调用点 | 原P1路径义务 |
|---|---|---|
| G0 | 外部已发布context、固定目录建立后，controller创建/release parent之前 | 完整P1/caller/source锚；两侧自身库存另计 |
| G1 | parent确认fresh完整quiet、内层记录发布后、比较与candidate前 | parent持有原预期，完整重读库存/source |
| G2 | controller outer quiet、两层记录/候选及输出核心库存核对后、final observation之前 | controller原caller独立完整重读库存/source |
| G3 | final observation create-only/readback之后、最终库存/返回之前 | 完整P1/source/caller书挡；发布存在仍可返回未决 |

任一quiet未知禁止该Job工件内容和全内容SHA库存；controller只能存自己的process/失败诊断，不补造缺失inner文件。G失败不自动重放，不推断数值不可行。

## 输出、发布与失败

固定原17 targets和四份128KiB记录；不新增production target。普通解析连接只使用相同路径布局，context的schema/scope及所有门禁明确为ordinary。每个角色的写入路径固定，所有目录/祖先/根identity持有书挡；input/output不相交，fresh与fresh_parent各自独立。JSON经规范编码与长度核验后才独占创建pending，write/flush/fsync/readback/no-overwrite rename/final readback；阶段、expected SHA、may-have-published和原始错误链保留。已存在target或pending拒绝，不重试、不覆盖、不删除失败工件。

external harness顺序是O不存在时生成ordinary context→独占create O/context→controller核O仅含该context及root/祖先identity→建立固定子目录。external唯一写context；以下表是唯一writer和每target cap，合计17项5,537,792B（5.28125MiB）＜8MiB。每次会计核已用＋所有尚余target cap恒等于该预留总额；failure独立128KiB，不计入四记录512KiB。四个log是应用日志，当前固定为空；不捕获解释器/bootstrap的OS stdout/stderr，启动失败由直接owner记录保留。

| 唯一writer | targets | 每项cap |
|---|---|---:|
| external | context.json | 2MiB |
| controller | worker/parent_startup.json | 16KiB |
| controller | worker/launcher.json；parent/parent_observation.json | 各128KiB |
| controller | diagnostics/failure.json | 128KiB |
| parent | worker/parent_metrics.json | 1MiB |
| parent | worker/comparison_candidate.json | 256KiB |
| parent | worker/fresh/startup.json | 16KiB |
| parent | worker/fresh/launcher.json；worker/fresh_parent/parent_observation.json | 各128KiB |
| parent | worker/events.jsonl；worker/parent.stdout.log；worker/parent.stderr.log | 各64KiB |
| fresh | worker/fresh/metrics.json | 1MiB |
| fresh | worker/fresh/events.jsonl；worker/fresh/stdout.log；worker/fresh/stderr.log | 各64KiB |

RoleStore冻结writer、完整目录和context文件identity；每个JSON target仅一次attempt，publication receipt持有实际pending→final identity。读取许可来自创建线程的真实OwnedStage：不可变terminal commit、actual witness完整并与冻结record相同、全部实际HANDLE关闭；成功payload读取前再核完整success-record，JSON自报bool不能授予许可。应用诊断只需实际quiet且限固定日志。

最终顺序为outer quiet→保存且精确比对outer launcher→两层记录/候选核对→15文件核心库存/G2→final observation/readback→G3/source/16文件最终库存→核核心原bytes/identity及最终publication receipt→返回。最终record不预写G3完成bool；返回后的稳定性及controller自身退出仍属于external boundary。

quiet未知只能进行有界metadata安全会计与独立process诊断，禁止读取其payload/日志或全内容库存。成功读取前后核metadata、目录和exact bytes；比较完整payload及caller-held预期，不从双方互相推导预期。candidate、文件发布及最终采用保持不同事实；生产最终局部返回仍依赖外部trusted invocation和G3。普通连接记录所有F/science/resource/formal字段false。

## 普通检查预算

先固定collection、互斥组和源码snapshot；普通pytest单组最多90s，所有pytest实际执行累计≤240s，静态/collection/保存核验≤60s，合计≤300s。必要PRE_SEAL修正只在剩余预算内预登记affected-only组（每组≤30s）；所有失败和原源码保存，不自动重试、不提高单组帽。解析连接每个parent Job总额≤8s、fresh≤3s、quiesce≤1s，256MiB进程commit/512MiB Job/256MiB采样tree RSS；全连接root输出仍受8MiB/64文件及四记录预留约束。普通root文件操作的硬停止不在本批次宣称范围，pytest总帽不是F的180s准入。

首组33项31通过/2失败，54.938s，失败源码/两份原输出已保留；两失败均为旧纯RAM nested preset的0.8s fresh phase触帽，完整quiet仍通过。连接路径加入JSON/fsync/目录会计，故单列固定ordinary `role_graph` preset：parent各phase1.2s、合计7.5s；fresh phase1.4s、合计2.9s；仍在事前≤8/≤3的Job envelope内。原steady/deadline/nested及生产40/50/180不变。优化三应用日志初始化为一次首尾完整会计，空log/start事件不作无承诺的独立fsync；JSON持久发布仍完整fsync，应用错误事件保留fsync。ordinary固定fixture重建/比较复用已经冻结的context，源/runtime书挡仍在角色进入与G0–G3执行；actual saved分支保留原entry/adapter检查。

第二个real10组合于30s触帽，wrapper终止/等待pytest后原日志保存，不计终态通过。进一步把同一次最终库存操作的逐文件重复全局会计合并：首读前核实际quiet能力/完整success-record，首尾全局会计、每文件双遍原字节/identity、publication receipt及末次能力书挡保持；不跨operation/process复用，不减少G0–G3。重审剩余预算后，当前源码real10/unit26/stage87/metadata-bootstrap17分别以30/30/30/60s帽预登记，均终态通过；全六次pytest实际累计180.093s＜240s。完整科学adapter字节与原冻结snapshot相同，旧科学重放只复用该未变域；不将其当作actual saved角色或新fresh执行。

覆盖真实parent/fresh连接、relay时序与双层quiet、缺失/损坏payload、比较不相等、fresh失败、不完整quiet、启动后失败、发布各窗口与发布后漂移、目录替换/别名、target/pending冲突、四记录容量及原stage/bootstrap回归。复用不受影响的科学adapter保存证据；若其字节或行为受影响则运行相应窄回归。预期出口为可恢复开发检查点及完整F下一段实施条件，没有production lease/manifest、official verdict/receipt/seal或新增运行权限。
