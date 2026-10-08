# H1共同基准：目标、边界与选择规则提案

2026-09-29，DRAFT_NONAUTHORITATIVE。为有限登记机制协议v2补充可审阅的科学规则；未实现、未批准、未封存。

## 现有实现核对

`continuous_grid_normal.build_continuous_normal_model`建立正常状态SCUC，复用
`src/grid/rts_gmlc_scuc.py::_build_model`，并按ceil(minimum up/down)-elapsed补初始残余dwell。
现有normal输入验证要求一小时步长、零业务削减/恢复、无incident，完整area reserve，以及初始状态与carry一致。
代码能够表达短horizon，不等于已有H1滚动来源适配和共同状态发布协议。

现有normal目标`operating_cost`为thermal分段生产成本加cold startup与shutdown成本。
reserve、thermal limits、功率平衡、DC网络约束及机组chronology是约束，不是可牺牲的目标项。
共同reference现有选择器依次最小化请求MW、相对normal的L1出力偏差、按UID排序的各机组出力。
其数值规则独立于normal；normal修复不适用于reference或容量planner。

## H1 normal的具体建议

每小时取唯一当期base power row和baseline 250*w，事故不进入normal；维持已有机组、网络、成本、reserve源值。
不额外加未来负载预测、末端债务清偿、terminal generation target或末端机组价值。
正常网络只含normal状态，事故/selected-state约束由共同reference及各臂actual单独验收。
H1终端是开放的：当前启动机组尚未完成的minimum-up义务必须在下一小时的N carry中延续，不能因小时结束消失。

首次committable机组状态建议off、generation=0、elapsed_down=ceil(minimum_down_hours)，表示已满足启动前停机时间的机制初态；
以后由真实提交的normal前状态和chronology更新。不可将每小时重新初始化当作滚动。
其余normal初值使用第一小时已揭示base source上下限：fixed的commitment=true、generation=upper（按原门验证lower=upper）；
curtailable的commitment=true、generation=lower；disabled的commitment=false、generation=0；三者elapsed均为0。
这是假设性的入窗初态，不声称观察了前一小时实际出力；不合静态边界或dispatch_mode即拒绝，不能换另一个可行初值。
“all-off”仅适用于可启停机组。base_availability逐UID等于静态enabled，并按现有固定episode base规则保持。
origin disclosure必须绑定来源明确的入窗前边界事件状态及其已揭示历史，不能默认清空正在持续的事故；
缺少该边界记录则input unresolved，不读取未来事件结局来补初态。
N、Rref、A_a使用独立身份；Rref/A_a初始出力在有效可用机组上取上述normal初值，入窗边界已不可用机组取0，
同时保存同一origin disclosure和base_availability，再按现有actual-origin静态上下限验收；不通过则unresolved，后续不回写N。

### 并列解规则

建议normal采用显式词典序阶段：

1. 最小化上述operating_cost；
2. 按committable generator UID的固定字符串排序逐个最小化commitment；
3. 按全部generator UID的相同排序逐个最小化normal generation。

每个后续阶段将已接受assignment经独立canonical evaluator重算的前阶段目标值作为等式锁定，不能直接重命名raw ObjVal；
RHS按binary64 hex或已有无损canonical serialization保存。保留原始native上下界、canonical assignment、
锁定值及完整约束审计。二元commitment锁定为经整数审计确认的0/1；连续量不得因锁定失败自行舍入或移动。
全部新增锁定等式属于normal约束残差审计，绝对上限仍为1e-9；native上下界仍须有序，gap门仍为1e-8，
跨通道目标一致性仍按normal专属1e-9，双零gap=0，其余零目标情况unresolved。
这是对新增normal阶段的待批准适用声明，不声称旧normal封存包已覆盖这些阶段。
每阶段未通过则该小时normal unresolved，不使用此前阶段assignment作为完整normal选择结果。

此规则定义的是accepted-incumbent-anchored numerical lex selector，不能声明精确数学最优或唯一解；phase0成本及后续锁定残差须一起报告。
UID顺序是任意但事先声明的benchmark选择，不具有物理优越性。即使锁定了carry所需变量，仍不能宣称不同native运行间精确相同，
因为首级接受的canonical成本及各阶段解均可能在容差内变化。同一request identity独立重跑若得到不同carry，确定性门失败并unresolved，不能择优。
最终完整assignment重新验全部normal约束与所有目标锁定，核验输出的commitment/generation对应最终stage。
未进入后续状态和请求计算的辅助变量可保留完整witness原值；若实现读取新的辅助变量作为后续决策输入，必须补其选择规则。
startup/shutdown的状态转移须用incoming与selected commitment重算并审计，不能把非唯一辅助变量当作独立carry。
不能仅固定solver seed便声称实现了该词典序规则。solver参数及资源由独立计算pilot绑定，不在此规定未经验证的线程数。

## 输入、发布与确定性

normal计算键只由当前允许输入、N前状态、模型/规则/solver身份构造；reference计算键再包含当期normal选择结果、Rref前状态及已揭示事故信息。
键不含alpha、theta业务坐标、D、arm、source/pair/split标签或未来后缀；审计层可另存这些标签到键的映射。
每个键只发布一个已验收的决策projection：normal为选定commitment/generation、完整N carry及canonical目标锁链，
reference为g、选定generation、完整Rref carry及canonical目标锁链。同键projection不同是协议冲突，拒绝发布，不能last-writer-wins。
完整assignment及reserve/segment/flow等辅助值作为每次执行witness单独保存，可有不同run-evidence identity；
下游只读公开projection，不读取这些可变辅助值。projection相同且各自witness均通过时，不因辅助值差异判共同决策冲突。
每stage存储目标标签/次序、raw bounds/value、canonical value、所有锁RHS与残差、完整assignment和实际solver/options/threads/seed身份。
缓存命中也必须验证输入、状态及规则身份。公开的当前时间若进入算法，必须是合同允许的时间信息，不能暗用其查未来源行。
相同可见前缀、不同隐藏ID或未来后缀的测试须得到同一公开normal/reference结果和g；测试通过只覆盖具名实现与输入，不替代形式因果证明。

normal结果发布后，reference在固定normal commitment下使用Rref前状态及已揭示事故/修复信息，按原reference词典序获得g及新Rref。
reference与actual继续各自原gap、残差和witness门；本提案不借normal数值修复放宽它们。
后续A、业务策略、actual及成对提交顺序见有限协议v2。事故修复不能使reference或actual的历史ramp/dwell凭空重置。
不得按某臂是否已停止或某theta的期限变化重新计算同一个已发布的共同前缀。

## 实施验收与成本门

需要新类型/身份的H1 source adapter、normal多阶段选择、三链状态存储与回放、按需共同前缀发布；不原地修改旧normal封存字节。
验收先用合成小例：成本并列但commitment不同、commitment相同但出力不同、残余dwell跨小时、跨时ramp、
后续缺源但登记债务已清、仍有债务时缺源、未来扰动及隐藏ID替换、同键冲突、任一词典序阶段失败和发布中断。
若机组数为n、可启停数为m，normal每小时最多1+m+n个阶段；reference及actual还各有自己的多阶段成本。
这一代价必须在正式资源登记前用冻结的合成输入测量，不能按单次H1 solve成本估算整个流程。
若成本不可承受，应如实提交算法替代提案；不能临时省略词典序阶段、改用首个incumbent或放宽数值门。

本页补足拟议科学规则，不证明实现或运行可用。与v2参数合同一起审阅通过后，才进入新版本开发验证；正式实验另需完整执行包与具体运行授权。


## 2026-09-30 授权与开发状态

用户已明确“批准 v2 合同并开发验证”。本页与配套H1/v2参数合同的科学开发授权已取得；此前“待批准”措辞保留为提案形成记录，不再作为重复询问依据。具体运行权限、资源门和执行验证仍独立。

首个独立实现normal_h1_model.py已有逐mode初态、单小时词典序阶段构模、等式锁及严格赋值审计；110项新旧相关测试通过14.04秒，正在闭合只读pre-seal复核。它尚未包含native逐阶段求解、已验收前级锁值来源、当前小时source adapter、causal shared-prefix key、三链持久发布或完整履约证书。旧normal代码与协议保持。


## 2026-09-30 H1当前小时适配与normal开发状态传递

新增 normal_h1_source.py、normal_h1_current_solve.py 及独立测试/规格。静态网络提取不读未来行；当前base row与workload按250MW/12位half-even映射，中性relative clock与真实source timestamp/time basis审计分离。旧normal内核仅使用局部(0→1)索引，全部UID出力/启停与committable持续时间跨小时保留；逐mode值域、可达age及boundary/input/static/clock绑定均有检查。

完整owned native lex chain通过且carry域合法才产生nonpublished numerical candidate。容差内assignment若不满足精确carry域，返回明确unresolved、无decision；连续出力和锁值不舍入。native后输入复核或carry拒绝保留完整native证据与调用计数。原始projection改为不可变bytes，独立audit identity绑定raw、timestamp、time basis及输入，不进入共同计算键。

/root/cfe_preallocation_official只读pre-seal findings已闭合；独立运行一个零solver 5e-10边界反例，未重跑pytest/native。最终47项定向测试通过12.87秒；相关四文件回归112项通过22.53秒发生于最后postsolve证据保留补丁之前，该补丁已由最终定向测试和定点预审覆盖。此前含旧normal的171项回归通过33.70秒。两次早期测试配置错误与修复、各次范围和hash保存在 results/tables/rq2_normal_h1_source_v1_non_authoritative/development_checks.json，旧A包587成员无漂移。

本轮未seal、无official verdict、无正式实验；模块只支持同进程开发组合。后续需来源认证、精确predecessor存档回放、same-key projection冲突拒绝、原子共同发布及三链/按需后续；不能把candidate用作已发布N或完整履约证书。下一步先接共同projection存储与零solver回放。


## 2026-09-30 H1完整锁链零求解回放与共同投影日志

新增 normal_h1_replay.py 与 normal_h1_projection_store.py、两组测试及独立规格。每个stage重建模型/前级canonical锁，重跑原normal predicate和严格assignment/carry域门；owned结果权限及全部数值派生证据逐项核对，原始native报告逐字保存。回放不创建可执行boundary，也不认证历史native执行。

共同投影开发日志复用本地NTFS owner，SQLite DELETE/FULL，只追加archive与head链。每次读取一个key会重放全部witness；不同projection使该key持续unresolved_conflict，不覆盖旧投影。commit后freshconnection逐字读回已提交历史才返回成功；commit/读回异常停止本owner，按独立保留head检查恢复。原始report aggregate32MiB、全库archive aggregate64MiB在解码/取blob前检查。

/root/cfe_preallocation_official只读pre-seal findings已闭合，未独立运行pytest/solver；最终相关四文件107项通过74.95秒，含已有source/native回归。测试覆盖权限/派生值篡改、阶段缺失和顺序、auxiliary witness差异、冲突、commit前后及readback失败。冲突测试采用validator-output故障注入，不冒充第二份真实native证书。

results/tables/rq2_normal_h1_projection_store_v1_non_authoritative/ 保存一份实际3-call合成完整archive、sample_checks及NTFS日志；禁用solver后回放/幂等追加/重开一致，replay0calls。development_checks.json记录源代码、测试、示例及数据库hash；旧A包587成员零漂移。未seal、无official verdict、无正式实验。

日志当前只持久保存开发证据，不登记native invocation、不推进episode N/Rref/A head；来源认证与审计lineage、精确episode predecessor/可执行状态恢复、三链发布、按需后续及完整支持容量/资源门仍待闭合。下一步接显式episode状态与持久前驱绑定，保持已有normal数值门和reference/planner独立门。
