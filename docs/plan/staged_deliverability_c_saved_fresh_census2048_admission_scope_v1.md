# NFC7：2048/自然返回与采样停止策略

2026-10-28，DRAFT_NONAUTHORITATIVE，起点0fe0ce0ab71f281d5e2a5dadcff27537736ee4e6。实现已形成draft，size/登记/unit/cold尚未执行；本文件固定首次执行前合同。依据[真实1024交接](continuation_handoff_20261028_saved_fresh_actual1024_v1.md)，目标为唯一2048或其前自然返回的有界import诊断，不把有限stop或return填作OBSERVED/LIVE、完整F或资源准入。

前驱NFC6 root16文件965896B、cp SHA 5c5a2e47010031bb6b0da99fc9cd928917a590c91e04db2f9db88ea00d7daad3冻结；累计static358.8353753000513、pytest366.48897970000326、unittest104.80309689999922，总830.1274519000538s、不接受37条。原57文件4020082B、失败与各自余量保留，不重跑旧包或转移余额。固定v3 leaf仍完整逐次执行，不递归调用NFC4/5/6 checker；继承输入933→1051→1061→1072无冲突union并增量绑定本包。

## 规模、DAG与费用

一次adapter import，最多2047次窗口内physical open；正常prefix为18帧census，schema进入独立v5、schedule为1及128至1920每128一次、terminal2048。最多20帧包括错误余量，单帧2048B、census24576B、总stderr32768B、stdout131072B、decoded131072B不改。size用finite float/有界int/封闭枚举的canonical长度过估计，核20帧census、最多256个graph帧及4个stage的总上界，并核saved固定body≤4096及packed≤65536；未知或超限仍拒绝并保留partial。

独立DAG及caps：size≤6 → register≤3 → 唯一完整14节点unit≤14 → PRE_SEAL≤4 → startup≤5 → profile≤4 → 唯一actual2048/return≤20 → saved≤4 → checkpoint≤3秒。static≤49、unit≤14、总≤63s，最坏累计893.1274519000538s。原59s只是未分配候选；本次执行前将unit从10预留14，以覆盖扩大窗口后的逻辑用例、采样/清理fault injections及四次full check，不修改任何已执行帽。

NFC6实测unit7.5794s中runner2.008s，四次full check与收尾占其余；本包逻辑窗口扩大且有一个0.5s阻塞reader注入，14s留不确定性。NFC6 actual audit8.7689s中parent5.7918s、窗口3.5519s只覆盖1024；cache增长可能非线性，20s是本次停止帽，不是翻倍外推的完成保证。最多1 unit child与2串行cold child，不另起memory/native校准子进程。

## 具体实现与完整保存

新root为results/tables/staged_rts24_saved_fresh_nfc_v7_non_authoritative，初始仅driver.py与原4745B import_policy.json，policy SHA仍4b731fc38ed2b52bff727acf0b02e4b8da7396cb17f2354225b34348155d9e9c。命令≤30000 UTF16、root≤16文件/4MiB，注册文件独立预留786432B以容纳新2048 helper及memory/fixture源码快照，candidate+1024B须先准入；旧NFC6的589824B及更早caps不改。

experiments/staged_rts24_saved_fresh_census2048_transform_v1.py精确构造core34/probe32/parent31、census2048_v1 helper、native fixture6与test none_census2048_v1。core/probe只迁移root路径；helper仅在CENSUS函数改limit/schedule/reason/schema及帧帽；parent只做同样解析器变化、路径与明确memory-drain接线。test01保留原oracle并包本层构造，其他原断言及14节点保留，新增2048/2047边界、完整schedule、natural-return边界和memory故障子例。Source49及全部科学模型/输入/阈值不变，epoch仍acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875。

本包14 helpers包括memory drain与独立fixture，所有当前注册事实由fresh input/graph/origins/source/构造/command/helpers/snapshots/control字段重建并精确canonical比较。size/register/check/checkpoint继续核11段timing结构与charge关系；计时是producer记录，不是独立时钟或任意FS/RAM认证。Unit父/子前后4个full check，普通phase前后各2个，checkpoint一次；保留固定leaf内部约2496次显式read以及各前驱和当前输入的fresh bookends。pin-memo仍不采用，不追加局部基准。

## 采样阈值、身份与失败

memory_drain_v1同步在原drain主poll loop采样，没有额外monitor thread；分别记录父控制器、直接子进程的working set、peak working set、PrivateUsage。后者是私有commit量，与working set分开解释，见[PROCESS_MEMORY_COUNTERS_EX](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex)与[GetProcessMemoryInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo)。64-bit本结构为80B；原native counter路径只在已计划startup/actual冷进程内形成观测。

诊断停止阈值：每进程observed peak working set或private commit>268435456B，或二进程同次采样合计>536870912B即停止直接子进程；requested poll10ms，最多4096次，统计只保留O(1) maxima/last。查询失败、类型/结构异常或样本帽同样停止，沿原kill/wait/readers/pipes/writer/stdin/HANDLE收尾，原primary及raw/partial保留。读线程未终态、pipe-close或其他cleanup问题均拒绝，不填写完整关闭证明。

生产drain不接受注入sampler/clock；测试入口单独标记injected_test，不能通过生产healthy验证。native sampler通过GetProcessId核parent pseudo-handle/真实child handle与PID，并逐sample核原handle对象/value/closed状态及PID。parent在Popen前强持并书挡drain/checker code/defaults/closure，drain在任何线程/流操作前核其actors、关键函数与primitives，返回后再书挡；receipt的parent-controller PID、child kernel identity、direct-child PID与memory binding逐项join。

仅在poll显示live后请求采样，采用last_live_poll_only，退出后不再发新查询；无live样本则拒绝。不为证明终止handle查询追加native校准。10ms不是调度间隔上界，短暂峰值/descendants/采样后的处理不获连续覆盖保证；continuous_bound_verified、combined_retention_verified、resource_admission恒false。新阈值用于本次有界诊断停止，不替代原128MiB combined-retention门槛、整链RAM预算或正式资源准入。

本版parent的memory_observation只投影guard已观测的child peak，新增memory_observation_source=last_live_memory_guard并在receipt/saved/checkpoint保留、核相等；不再调用旧版退出后的memory_observation(process)路径。旧NFC6的终止后peak记录仍按原定义，新版是最后live poll之前的observed peak，不能静默当作完整生命周期峰值。

独立fixture使用BytesIO与fake process验证健康终态、阈值、query/type错误、无退出后查询、timeout/output/reader错误、样本帽、kill/wait失败、pending reader与pipe-close失败、入口actor/global漂移零副作用及记录篡改；finally恢复fake状态并终止注入reader，fixture不创建进程。其实际调用纳入本包14节点，不能仅据文件存在认定通过。

## 门槛与后续

进入cold前须完成本包size/登记、完整30帧/report/exit0的unit及收尾、独立PRE_SEAL、live process核验；startup首次native memory观测及profile accepted后才可唯一2048。任何拒绝保存本包端点后停止，不自动重试、续时或退款。

即使自然返回，finder metadata/registry、Source49末端bookend、import boundary、runtime owner/handoff、OBSERVED/LIVE、issuer/permit/quiet/父端采用仍须分别核；这些门槛不由return自动填充。现阶段无P1/实际role/OwnedChild/Job/F、model/solver、native校准、长实验、外部下载或paid query。所有科学/资源/正式/run字段false，39项并行dirty原bytes保留，宽goal保持active。
