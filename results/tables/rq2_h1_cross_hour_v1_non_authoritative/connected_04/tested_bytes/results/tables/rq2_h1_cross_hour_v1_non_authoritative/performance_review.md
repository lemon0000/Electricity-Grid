# 跨小时完整链：有界诊断与整体性能审查

状态：DRAFT_NONAUTHORITATIVE。用户授权继续跨小时完整链，并要求启动前先审查整个实验的优化空间。此文件规定形成性能证据的有界诊断；完整预算实测尚未闭合，不启动长实验或 native。

本包只验证 fresh 192h root 的前两小时，不把声明的192h当作已执行。三lane为network/cfe/joint；source/catalog和solver-shaped候选为synthetic，历史reader、source join、registry算法、精确business、数值replay、配对存储和重开均用原实现。正常环境运行两个实际短Windows Jobs，Rref/Actual在父进程安装fake solver，real native calls=0。旧chain07及独立后验04保持原字节复用，无重跑。

执行DAG：source/catalog fixture → 新controller/192h声明 → 内部source N0 → 3-stage fake Job → N0 terminal → holder/owner genesis fresh → hour0一次Rref(3stages) → 3 Actual(各2stages) → intent → 原scientific transition/replay → 第二次独立fresh → paired outcome → 完整readback → owner guard内完整replay/need → branch reservation → durable hour1 attempt → capability/predecessor核验 → 内部current source N1 → 3-stage fake Job → terminal/post token → hour1 fresh join → Rref(3) → 3 Actual(2×3) → intent/replay → 独立fresh/post token → paired outcome → 完整readback → 全部close → holder+owner重开/完整readback → historical controller prefix2与parent snapshot重开 → 报告/全部close。

固定调用量：2 normal Jobs/6 normal stages，2 Rref/6 selector stages，6 Actual/12 selector stages；合计18 selector captures。每小时至多9 captures/9 solver-shaped seconds（每stage声明1s；非真实native预算）。Rref失败不运行Actual；停止lane不消费Actual，不推进business/A carry。intent之后失败保留pending而不重试。whole episode未完成，停止在合法两小时prefix。

优化决策：

- 使用现有旧链作golden evidence，构造新的小网络2h用例；不引入旧writer恢复/科学状态迁移框架，不重跑72h主体。
- successor `_stable_replay` 每次操作只做一次完整科学replay，返回同一操作的immutable state；原`_ready_rows`先inspect再restore的重复完整重放被合并。每次调用仍核DB/holder/lease bookends，重开重新replay。
- 同一次operation的current/state供Rref和3 Actual共享；它们有独立carry，A不写回N/Rref。
- paired前第二次fresh和结束完整readback保留，不用第一次动态baseline冒充独立鉴真。不跨小时缓存，不降低任何数值限。
- 不采用并行：三Actual的小例启动/IPC成本未证实有收益，同一owner操作及源观测合同优先；正式大包的独立任务并行仍待DAG/资源证据。
- 本次复用entry6已记录的code/path/metadata读取优化；其收据必须完整保留。此entry改变I/O开销，不替代source fresh或scientific replay。生产无此entry的成本仍未知。

已知成本证据：旧two-N source测试outer358.875s，旧18 owner单元测试outer113.891s；二者任务不同，不能相加/倍乘作为整链预算。旧hour0 chain259910.325s亦不能外推。当前重复hash、历史prefix重放与失败收尾的实际次数/耗时由下面诊断测量；未覆盖168/192的成本仍未知。

首次代表性诊断固定：1次2h/3lane，无native；wall上限600s，整个观察到的进程树RSS上限1024MiB，任务root+out存储上限128MiB，5s采样心跳。180s为每个normal Job原资源上限，非整链预算。无阶段进展120s为停止条件（阶段日志、子worker文件变化均计进展）；异常、RSS/存储/总wall超限停止本次owned进程，保存所有已写原件及终态，不追加时限。若未覆盖完整路径，结论必须是性能审查未闭合，定位后只重跑受影响短诊断。

runner在启动前保存精确命令、解释器/环境、源码/config/source-fixture SHA及plan SHA，复制绑定bytes；期间禁止修改被绑定文件。监视器只声称观察到的PID+creation-time后代退出，不能声称完整未观察进程树证明。每个normal Job另有自身quiescence记录。成功后必须核source unchanged、全部任务lease/handles关闭、observed PID退出和保存prefix bytes，再做只读PRE_SEAL审查。最终whole-workflow性能审查是否完成以实测报告为准；此计划不打开formal/resource/native gate。

科学验收：非零workload=.1、baseline25MW；hour0 source cfe_call_fraction=.6、hour1=.2（按既有R=1-source规则）；alpha=.5/f=.5/rho=.1。独立Fraction检查CFE/Joint首小时q=.02，下一小时floor12 EDF恢复，debt=q-.85*r，q+r≤D；N/Rref/A各自carry与source hour推进到2，保存头/科学状态close/reopen一致。fake solver没有最优性/工程安全结论。

持久化边界：reopen验证历史N及配对科学状态；本版没有持久化的atomic-live capability receipt，所以不宣称重开认证原进程的live join，不支持normal writer进程退出后的可写恢复。

首次诊断connected_01：outer90.688s，pytest失败（82.28s），在N0 Job导入synthetic测试依赖时缺少tests搜索路径；Job exit1且quiescent，未产生N0科学outcome，real native=0，原件/root全部保留。峰值观察RSS401469440bytes，存储20733395bytes；source unchanged，观察4PID均退出，monitor errors=0。失败不计作数值链完成。

下一次有界诊断仍为同一2h/3lane问题、600s/1024MiB/128MiB和120s无进展停止条件。修复child tests路径；测试fixture仅需要pinned Resolver与coordinate，去掉旧fixture未使用的真实RTS current装载（首次启动大部分时间在test body前；该小例不声称真实RTS source）。增加pre/post controller token、aggregate budget和失败冻结针对性单元。新request再次绑定新bytes，不修改connected_01保存的bytes或时限。

connected_02：outer79.578s，pytest71.07s失败；N0 child进入数值capture后发现synthetic assignment误用了不带normal索引的generation标签，Job exit1/quiescent，仍无N0 science outcome。385126400bytes峰值观察RSS，观察4PID均退出、source unchanged、monitor errors=0；原件保留。
修正fixture的generation和分段功率，并在任何下一次Job前用两小时各3个canonical normal模型检查完整变量inventory、功率/成本锁及1e-9残差。下一connected仍原2h/3lane与原资源/停止上限。

unit_04：11项定向（包含两小时共6个normal模型offline残差/目标检查与dispatch替换负例）全部通过17.50s/outer26.657s、source unchanged、观察PID退出、读窗handles关闭。connected_03启动后，静态核对发现新增测试cleanup断言误读已置None的lease.stream；在下一Job前停止该non-authoritative诊断（外部停止原因保存于connected_03/external_stop_reason.json），outer63.578s/exit4294967295，观察2PID均退出、无新Job，原件保留。此停止不算数值失败/成功；修正为保留原stream并核closed以及lease.stream=None/locked=false。
connected_04继续同一固定问题与600s上限；增加已保存根close/reopen前后全部文件bytes/hash相等、两个Job exit0/quiescent、全部原stream关闭及read-only重开拒绝生产的检查。资源和科学限制保持原值。
