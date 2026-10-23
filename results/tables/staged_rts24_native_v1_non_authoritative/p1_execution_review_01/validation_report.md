# P1：一次RTS-24原生代表校准

2026-10-23，DRAFT_NONAUTHORITATIVE。用户在本轮明确回复“授权给你继续做吧”，对应前文给出的唯一一次P1范围、原登记及停止帽。[授权上下文与启动前核对](authorization_and_prelaunch.json)记录该外部指令；原registration_v1.json保持native_authorized=false和SHA `23577e5d79d3284a260decbfe2258a3103252617953452565a9feeffafbd94e2`，未因运行改写历史注册。root唯一writer；只读领域及独立复核不签发official verdict、seal或receipt。

## 实际执行与终态

原[launcher](../../../../experiments/staged_rts24_native_launcher_v1.py)核完整schedule、源码/config/选定环境及旧工件后，独占创建[p1_01](../p1_01)。on_time/early/full_temporal，从真实前史h=-2到h=2，共五个模拟小时；随后h=1/2的normal-C及branch_0、generator_0代表合同子集。全部串行，零重试，没有扩大范围或顺延停止帽。

[report](../p1_01/report.json)记录31/31 reserved、run-invoked、run-returned、parent-imported；16 QP/15 LP。31个原生点均kOptimal，接口返回kOk、primal/dual valid，必要父点、child及actual独立审计通过。worker与一个fresh进程得到完全相同state/head/summary/audit，fresh为零solver、零新构模，重放范围内零新证据发布。

package_complete=true表示固定P1包完成；科学终态仍为missing_input、publication=committed、state_certainty=known。已接受至h=2、5行，无原始违规；coverage_complete=false，method_conditions_satisfied与full_replay_conditions_satisfied均为null。观察末端仍为8，h=3..7没有执行；未将缺输入补成零需求、完成或不可行。resume_permitted=false，本次目录不重用。

## 已观察业务与代表合同

下表来自保存journal的prepared/proposal及连续账本，由领域审阅逐项复读。q/r以MW_c、债务以本例一小时步长下的MWh_c计；P/g以MW、Y以MWh计。reported数值点仍按原声明容差审核，不声称严格数学界。

| h | 实际网络/工程 | P0 | 原始网侧g | CFE延期q | 恢复r | 实际P | Y | 小时末债务 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| -2 | normal/投运前 | 150 | 0 | 0 | 0 | 150 | 120 | 0 |
| -1 | normal/投运前 | 150 | 0 | 0 | 0 | 150 | 120 | 0 |
| 0 | normal/投运前 | 150 | 0 | 0 | 0 | 150 | 120 | 0 |
| 1 | branch_0/投运前 | 150 | 0 | 20 | 0 | 125 | 100 | 20 |
| 2 | normal/投运后 | 160 | 0 | 0 | 20 | 185 | 168 | 0 |

h=1的原始CFE请求为25 MW，按a=1.25变为20 MW_c延期；该小时q_grid=0，延期完全由CFE触发，不能解释为非零网侧调用或用于抵扣独立F/X承诺。该任务due=3，在h=2已恢复，保存status=recovered_by_deadline；due=3尚未实际观察，所以deadline_miss仍为null。当前尾债0、observed_primary_deadline_miss=0、primary_right_censored=false，来源是已观察任务结局，而非时域已覆盖完毕。

四个代表outage-hour（h1/h2各branch_0、generator_0）均有独立firm点满足声明静态DC约束，raw点保存削减值0，point_legal_under_X=true；每个raw另有child-LP证据。legal_X自身仍minimum_established=false、independent_firm_point_still_required=true、temporal_backing=not_established；本包确实另核了firm点，但四行并非全部69态或完整139节点。actual子集与完整C父点族分别保存，不互相替代。

## 成本、计数与覆盖

| 观察 | 实测 |
|---|---:|
| 整个launcher命令外层wall，含只读准备及启动/返回开销 | 213.51433710000128 s |
| 受控worker Job外层wall | 206.28100000000268 s |
| 单点进程最大外层wall | 3.625 s |
| fresh进程外层wall | 12.781 s |
| 31点原生内部run时间之和 | 0.08562920000986196 s |
| 采样Job全树峰值RSS | 300,490,752 B |
| Job peak commit | 241,938,432 B |
| 外层保留成员HANDLE / TotalProcesses | 66 / 66 |

[launcher](../p1_01/launcher.json)及每个point/fresh均exit0、stop_reason=null、quiet=true；全部保留HANDLE signaled、active=0、PID list为空且历史成员数闭合。RSS是采样值，不保证捕捉间隔尖峰；commit与RSS分别报告。原单点求解5s/进程10s、Job300s/无进展30s、采样RSS1GiB及64MiB/5000文件帽均保持。所有权/准备范围见原[P1合同](../../../../docs/plan/staged_deliverability_c_native_p1_contract_v1.md)。

观察器记录父端与点端合计124次Pyomo build、62次numeric import、31次native call；worker selective120/378描述，fresh55/173描述，共175/551。launcher未安装同一观察器；其完整核验另有源码定义的一次schedule，即5/16 selective及2/285 full，属于结构会计，不能冒充新的仪器观测。计入该准备后，与原未来执行180/567 selective、6/855 full对账；历史注册准备仍单列。worker35与fresh17次audit_execution分别来自保存/重放路径，不是52个独立实验；full compiler中的276个fault描述也不是276次native执行。

worker fingerprints 65次、inclusive约38.519s，点子进程共62次、fresh2次。原生内部run合计远小于命令wall，提示该样本的装载、身份/文件核对、进程和保存链是后续性能定位重点；inclusive时间有嵌套，不相加成总wall。源码/身份核验的优化仍须保持依赖freshness、失败窗口与旧CAS/root删除检测，不能据本次观测直接省略检查。

保存量分三种时点：completion.json绑定677个worker范围文件/2,836,931 B；launcher终态扫描682文件/2,946,738 B，尚不含launcher.json自身；独立后核验的完整终态为683文件/2,950,863 B。将来新附加的审阅目录位于p1_01外，不混入这三种计数。

## 保存后核验与审阅

[只读postcheck](postcheck.py)第三次执行exit0，完整输出在[postcheck_03.stdout.json](postcheck_03.stdout.json)。核全部683文件SHA、273个point CAS与130个journal CAS的内容寻址/引用、六entry链和trusted head/state集合、request/native/result/log绑定、原选项/退出/quiet、fresh同一metrics及重放禁止新证据、124/62/31计数。另以stdlib对保存transport矩阵/向量独立计算row activity、目标和reduced-cost echo及primal界；最大objective echo约2.91e-11，row/primal界约2.39e-12，reduced-cost echo约5.12e-13，均在原1e-6门内。它不重新构建或证明原科学模型代数，也不调用solver或执行journal replay。

前两次失败仅属新后核验器：初版将point CAS根误作objects目录；第二版将历史checkpoint的可选input_pins当必有。已保留两版源码、stderr、非零退出和空stdout原件；最终按实际目录及原HEAD checkpoint字节解释，未修改P1、旧checkpoint或验收阈值，未新增native尝试。B1–B3的118保存文件及685个旧checkpoint路径匹配；原注册/运行源码/config字节保持。

领域模型与独立审阅均只读检查原保存记录，未发现High/Medium科学不一致；强调h1为CFE延期、C/P0双父点、missing_input与null、三种存储时点及数值证书资格边界。独立复核还核31点的绑定、完整数组/退出与fresh计数。后核验源与最终包装的具体复读记录随检查点保存，不产生official verdict。

## C与后续范围

本次关闭“固定P1原生后端和代表保存路径缺实测”这一具体缺口。它不覆盖昂贵真实失败、更多cohort/更长前缀、完整静态139、完整反事实F/X时序、三方法/快慢业务主比较或独立留出；本例g均为0，也没有验证非零网侧实际调用。overall_performance_review_complete、resource_admission、formal_result继续false。

后续须据本观察重审优化、完整路径及有限主比较规模，并确定业务/设备/工程/任务/清洁来源、D与选择/敏感性/留出规则。P2或其他新的native校准需另登记具体包并取得相应授权；本轮P1一次权限已经使用，原目录保持。尚无D/E资源准入或正式论文结果。
