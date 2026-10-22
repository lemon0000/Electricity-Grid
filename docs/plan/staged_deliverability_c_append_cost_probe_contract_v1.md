# C同append后继的保存成本诊断合同

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。接续[batch交接](continuation_handoff_20261023_batch.md)。仅新增诊断、普通测试与保存记录，不改旧B1–B3、codec/journal_v1/v2/v3、batch五源、P1十三源及注册。根唯一writer，sol_reviewer只读PRE_SEAL。按agent.md第9节在已有有界开发范围内测量，无native/solver、下载、seal或formal动作。

## 问题与固定来源

测量同append合并pack/inventory后，在原科学校验完整保留时的实际保存成本。输入为旧`staged_rts24_journal_v1_non_authoritative/attempt_01/{method}/journal`：三方法各genesis、前两条hour及其typed CAS闭包；读取保存Fixture、row.prepared.evidence、row.actual、初始/各小时完整state。只用`EvidenceReadView`，读完bookend；旧writer/reopen及analytic生成器不执行。完整观察末端保持5，只有h0…1已观察，期限/未观察后续不截短。

每个case重新从已核旧字节解码，独立ReadView且不共享fixture/row/cache；读完关闭该ReadView，case末端另逐字节重读其全部used闭包、完整inventory、三个root SHA与原目录身份，并核全部输入typed根。末核不重新打开已关闭cache，也不重复解码；捕获的不可变bytes只作比较预期，不供下一case生成输入。v2与v3分别与冻结state逐字段、科学digest、typed根及CAS闭包字节核对。普通运行态hook不可改变输入。新schema/runtime/entry/root哈希差异单列。

## 两段DAG、次数与冻结期望

1. **一次准备**：controller在spawn前独占cost_preparation_01，保存create-only准备request（实际runner/observer/合同/test/runtime/旧树与输入根/exe/env/固定case/预算）；external SHA传入child并首尾核→外部owned Job→受控compute/import/禁止数值入口→旧源/整树/manifest核对→三方法保存输入解码→每方法对保存的第二步state执行summary与独立audit各一次→保存baseline.json、观测与来源→进程退出/完整Job静默→controller复核原request与执行pin，读回→create-only `cost_registration_v1.json`绑定request SHA、准备launch和baseline。准备及测量均位于独立`staged_rts24_append_cost_v1_non_authoritative`命名空间，不创建旧attempt或修改旧树。准备Job固定30s总wall（包括启动/Job收尾及终态扫描），child自身工作最多20s/20s无进展，输出4MiB/200文件、RSS1GiB；静默未知不注册。baseline结果及来源根/状态SHA先绑定注册，后续测量不能现算期望或选择case。
2. **一次测量**：controller先按external registration SHA核源/旧树/环境/baseline→独占cost_probe_01→owned worker→首尾旧绑定核对→逐method、v2再v3各create/两hour/finish→保存外部trusted binding→一个独立fresh进程仅reopen→quiet后读回并核完整state、闭包、summary/audit/outcome/certainty/terminal→三类失败各版本一次及各一个fresh→首尾核源/旧树→报告/观测/completion→worker退出/outer Job静默→launcher终态及保存核验。

每个fresh在spawn前另存create-only intent，绑定case/reg SHA、exe/env、argv前缀、确定性的`--intent-sha sha256(intent)`尾参规则、整个输出树/进度路径及限制；child首核external intent SHA和实际`sys.orig_argv`。静默后另存monitor，不覆盖intent。controller在outer quiet后首次读取completion/report/worker和12份fresh观测，重算core索引、晚写stdout/launcher/completion全树pins、科学/计数与旧绑定；最后独占controller_verification并复核终态树。任何失败保存controller_failure，不把worker exit0当全包成功。

正常六case与失败六case均串行，12个fresh；零重试、零恢复、零追加观测。失败case固定full_temporal且从初始state开始：

- unknown：只在本case `entry_000001.json` 的首次`after_rename`抛登记OSError；核publish对象路径、raw SHA、ordinal及final可见性。writer保留head/ordinal0、未采用；failure may=true/unknown，fresh核完整闭包后确认恰一条hour、committed、无terminal。
- deletion：同一具体时点，把本case genesis所指fixture CAS的原字节/SHA独占保存为removed_object.json，再删除原对象；resolve必须在本case新journal内、只一次、不恢复。writer未采用/ordinal0/unknown，fresh必须拒绝缺失可信闭包，不能生成新证据或伪造终结。
- reference_unresolved：begin(None)，保存未接受观测和reference未决attempt；writer状态不前进，ordinal1、committed、closed，fresh同样未决、0接受row、无terminal。这不是publish unknown。

记单次h0/h1请求描述数为(d0,d1)，instantaneous=(1,2)，fixed/full=(3,4)。selective compiler是Python请求列表编译，不是模型构建/solver调用。各节点的固定会计如下：

| 节点 | 每次calls/descriptions | 次数与合计 |
|---|---|---|
| 准备baseline，summary+audit | 4 / 2(d0+d1) | 三方法12/34 |
| success writer：h0、h1、finish | 3、6、4 calls；合计13 / (8d0+5d1) | 每版本三方法39/106 |
| success fresh | 同writer 13 / (8d0+5d1) | 每版本三方法39/106 |
| unknown writer/fresh | 3/9 + 5/15 | 两版本16/48 |
| deletion writer/fresh | 3/9 + 0/0 | 两版本6/18 |
| reference未决writer/fresh | 2/6 + 2/6 | 两版本8/24 |
| 测量worker+12 fresh | 186/514 | 六success156/424，六failure30/90 |
| 准备加测量 | **198/548** | P0=198、raw=66、恢复min/max各142 |

构模/full compiler/证据生成/native/solver允许次数均0。入口在加载所有可达科学模块后统一禁止，并核所有冻结别名；不能只patch SolverFactory源入口。fresh还禁止CAS put/publish、新runner递归或构造新输入。实际失败少执行的调用保存真实值，不能填齐预算；必要计数、数值、源或子进程失败即不再启动下一case。

## 观测与等价

观测器源码、alias集合、配置和时钟均绑定注册。在所有模块已导入后，对同一源函数及冻结别名装同一wrapper；每阶段核wrapper/禁止入口身份，异常也记录started/returned/raised，退出恢复原绑定。持续漂移则计数unknown并停止，不声称覆盖任意内存ABA。覆盖selective/prepare/accept/summary/audit、runtime、pack/inventory/read/publish、v3 deepcopy/typed比较/batch；逻辑读取成功bytes、inclusive时间与外层阶段wall分别保存，嵌套时间不相加。观测/事件/manifest及报告自身写入单列，不是全OS I/O。

成功逐小时核完整state及typed wire，finish后v2/v3完整CAS清单与逐文件字节一致；fresh读取相同外部绑定，返回规范化完整state和保存根、summary、独立audit与准备baseline相等。failure同时核prefix/head/ordinal、实际failure witness、final/pending/孤立CAS、terminal及fresh结论，不只比较异常字符串。保存schema差异、依赖身份、阶段绝对wall、CPU/采样RAM及文件/字节数。

顺序固定v2→v3，单次观察存在缓存和顺序偏差：只报告该顺序下阶段绝对值，不报告提速比、节省百分比或优劣推断。复制/比较/runtime、观测包装和输入解码均计入相应阶段；首尾preservation成本与journal阶段分开。

## 总预算、停止和绑定

外部supervise总wall帽300s，包括owner创建、全部worker/fresh、最终quiescence及终态扫描；无真实阶段进展30s。worker组预算为准备/读取25s、parent科学/输入绑定与保存累计110s、全部fresh监控及收尾累计110s、末核20s、报告5s，合计270s，保留30s用于启动、调度、outer最多5s收尾和末扫描；child自到达后的总工作也不得超过270s。这是会停止的组预算，不保证所有局部最大耗时可同时完成。每fresh的supervise总帽10s已含其quiescence和末扫描；异常时最多5s清理可能超出成功总帽，该案必须失败。每次启动前须从累计110s组预算与worker剩余预算预留15s，否则停止，不顺延。阻塞终态IO不承诺硬实时落盘，失败保留unknown。心跳仅在输入核验、完成小时、finish、child静默裁决和最终核验等真实进展点写入，不能为续命空写。

outer采样整树RSS1GiB、每进程commit1GiB/Job commit2GiB；整棵cost_probe_01输出16MiB/3000文件，fresh用同一总树扫描，不能另获配额。0.2s采样，输出预留终态16KiB。串行最多worker+一个fresh逻辑角色同时活跃，共13个逻辑角色launch；本机Python启动可能产生stub，不能将13当作Job历史成员预期。guard硬上限1024，按实际TotalProcesses==保留unique HANDLE数且全部signaled、active0/final_pids空核对，缺短命成员为unknown。所有PID/creation与实际成员数落盘；exit和whole-Job quiet前不读child报告。

注册绑定精确compute exe、受控env策略、两个runtime、direct runner/test/合同、observer/codec/ReadView/guard/ownership及实际使用的历史preserve helper、旧v1/v2整树和核心manifest、batch开发记录/5源、P1 registration/13源、baseline字节与DAG/规模/预算。旧树仅显式旧目录，不含新cost输出。worker/fresh按各自角色核同一registration SHA、code/input/runtime和固定argv；控制器完整核验，fresh另由journal自身首尾runtime及读盘闭包核验。所有新输出create-only；启动后code/config/input/registration冻结，后续修复用独立successor。

外部controller的无数值准备/启动核验另记录其绝对耗时；measurement的quiet后完整只读readback为45s合作式上限，逐case及落终态前复核，输出仍计同一16MiB/3000文件。它不包含在worker的300s观察值内，不能把worker wall称为全流程耗时。成功和失败均在本次新建目录保存controller_timings，包含preflight、owned monitor、quiet后处理/读回与从launch入口到末记录前的总wall；明确末记录自身、最终console和退出不在该值内。另由外部PowerShell Stopwatch按process启动至返回保存exit/wall捕获，覆盖解释器启动与末记录出版。PREP的late controller记录在registration创建后生成，独立保存并在measurement报告中绑定其内容，不冒充baseline或production输入；measurement late记录由后核验与Git绑定。阻塞系统调用只能使该段超限/未知，不能保证合作式上限为OS硬实时帽。

外部PowerShell wrapper也属于direct source pin。每角色启动前以create-new owner排他占有，再create-new日志与intent（脚本原字节SHA、argv/cwd与输出）；准备request绑定同一wrapper，measurement先核准备绑定，结束后重核脚本。exit0还须存在普通controller timing且accepted_success=true、request内wrapper SHA相同；否则外部capture保存非零/unknown。末端capture绑定intent/log/timing字节，不覆盖失败记录。普通测试用临时假Python进程检查脚本漂移、缺timing、未绑定、失败timing及并发双启动只有一个owner。

普通测试至少覆盖观察别名与恢复/漂移、isolated source加载、组预算/非quiet禁止读、注册和输入篡改、路径/故障对象界限、零数值入口和fresh只读；启动前PRE_SEAL完成。该三母线两小时诊断不测公共RTS-24数值点、真实dual/log、139/F-X时序、长cohort/192h、真实坏盘/掉电/阻塞IO，不关闭C/D/E资源或授权P1。
