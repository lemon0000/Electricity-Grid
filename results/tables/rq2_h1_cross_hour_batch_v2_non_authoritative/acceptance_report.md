# 跨小时批量重放后继验收记录

2026-10-20，DRAFT_NONAUTHORITATIVE。批量历史重放后继完成 **2小时、3分支合成成功前缀**：N0 → Rref/Actual → paired → 同一owner内attempt/N1 → Rref/Actual → paired → 全部关闭 → 重开完整重放。2个outcome覆盖6个lane-hour。完整168h enrollment及至多24h follow-up仍OPEN，episode尚未终结。

`connected_01` exit0，pytest为`1 passed in 503.18s`，outer **509.516s**。旧v1 `connected_06`同规模记录604.266s，本次少94.750s（15.68%）。这是单次开发fixture观测，生产成本和192h预算仍未知。

主要证据：[启动绑定](connected_01/request.json)、[终态](connected_01/terminal.json)、[只读文件/Fraction补验](connected_01_postcheck.json)、[补充依赖绑定](connected_01_dependency_bindings.json)、[可读性能复核](workflow_performance_review_readable.md)、[只读PRE_SEAL findings](preseal_findings.md)。原case位于`D:/h1_batch_connected_01_non_authoritative/test_two_hour_three_lane_batch0/`。

| 验收项 | 观察结果 |
|---|---|
| 持久链 | intent → outcome → attempt → intent → outcome；2个outcome/6个lane-hour；三lane均active，无pending |
| 执行 | 2个受限fake Windows normal Jobs均exit0/quiescent，PID40564/47320；18 selector captures，0 real native |
| 科学等价 | 两小时projection去掉版本化request_key/request_contract后与旧06全等；完整最终科学state全等；逐小时decision及exogenous scientific identity一致 |
| 关闭重开 | 所有原handles/leases关闭后取快照，重开constructor完整replay，加独立historical与snapshot，再次全部关闭 |
| 文件 | 新三root共212个文件（含lock）名称及SHA前后一致；旧06的212个文件保留原SHA |
| 动态校验 | 每次source有两个新Reader，constructor inspect和显式inspect均保留；current与paired前fresh独立；批量current/frame/proof仅存活于本次调用 |
| 非预见性 | 保存oracle中hour0单独读取与含N1批量读取的audit完整字节相同；逐小时decision/frame/origin/action及精确业务输入与原prepare相同 |
| 身份/故障 | 固定source/reader原callable，构造建root前及读前拒绝替换；8顶层audit+3嵌套proof+3统计形状+4错terminal map负例拒绝 |
| 清理 | reader/lease关闭失败仍尝试其余close并清空captured、保留primary；reducer失败清空本次batch |
| 资源 | 采样树RSS峰值378.84MiB，logical峰值20.54MiB；观察6PID均退出，monitor/cleanup errors为0；完整未观察进程树证明仍false |

原exact business和数值replay保持执行，并以独立Fraction计算补验：

| lane | h0调用q | h1恢复r | h1剩余debt | Actual MW h0 → h1 |
|---|---:|---:|---:|---:|
| cfe | 0.02 | 0.023529411764 | 0.0000000000006 | 20 → 30.882352941 |
| joint | 0.02 | 0.023529411764 | 0.0000000000006 | 20 → 30.882352941 |
| network | 0 | 0 | 0 | 25 → 25 |

q/r/debt是normalized业务量。debt精确为`3/5000000000000`，保留未清余额；逐小时核`q+r <= min(D=0.5,f*w=0.05)`及`power=250*(0.1-q+r)`。两小时Rref request均0 MW，正网络调用与事故修复覆盖仍OPEN。

本次新增独立DRAFT实现：historical batch一次前缀观察捕获各被选小时；source batch两遍独立观察后逐小时构造current；owner v2保持原科学FSM/transition，按本次batch查current。request、projection、source audit与owner头采用新版本身份；数量payload维持原口径。原phase owner/controller/exact source/business、v1 owner/test字节均与旧06相同。

| owner源层指标 | v1旧06/路径推导 | v2实测 |
|---|---:|---:|
| historical API调用数 | 32 | 20 |
| API层prefix-hour权重 | 40 | 28 |
| 对应parent inspect遍数 | 64 | 40 |
| parent inspect层prefix-hour权重 | 80 | 56 |

API权重下降30%。每个历史API有constructor+显式inspect两次底层遍历；表中不含独立historical postcheck、普通snapshot及内部anchor额外重放，不能把它解释成总I/O或wall预算。

| 非重叠阶段 | wall秒 |
|---|---:|
| body开始至N0 terminal | 65.409 |
| N0 terminal至hour0 paired | 78.963 |
| hour0 paired至hour1 paired | 246.306 |
| 全部关闭及首次快照 | 0.099 |
| 重开、完整重放、独立historical/snapshot、关闭及比对 | 54.634 |
| fixture/入口及其余收尾 | 64.105 |
| 总墙钟 | 509.516 |

嵌套owner timings另存JSON，不能与父阶段重复相加。继续使用原test-only静态code/spec memo：46708次入口、15个唯一键，先恢复全部原函数，再逐键原实现复算，bookend无误。326项code read范围关闭，全部request source SHA一致。`production_overhead_measured=false`，未覆盖未观察runtime dependency ABA。

验证范围：units_02中未变v1的36项guard通过，随后新纯数学测试误传records元组导致该attempt exit1，原件保留；修正测试pack/unpack后，units_03当前差异23项通过6.17s/outer10.875s/exit0。03后仅未选中的保存oracle函数增加故障矩阵；补验核其request/snapshot SHA，并确认剔除该函数后的完整module AST相同。saved_probe_02为1passed168.04s/outer173.625s/exit0，原203个normal文件未变。36项属于前驱v1回归，当前v2差异由23边界、保存oracle及本次完整链支持。

128MiB帽只计每遍所选packet/result/after数据，64MiB帽只计materialization元组；records/evidence/views/reader及多份数据共存总量另受诊断RSS监测。当前最大所选frame数据35967 bytes。owner最多保留2048条非权威cost数据，超限在source前拒绝，其UUID仅区分统计观察；192h内存可行性尚未知。

下一步仍沿跨小时主线补正Rref、事故延续/修复、分支停止/缺输入右删失的有界整链与预算；enrollment/follow-up边界按真实168+至多24合同验收，WINDOW保持原值。完整窗口、真实RTS、production成本、writer可写恢复、持久atomic-live认证、seal与official review尚未闭合。raw Job的数值/资源认证flag及formal/native/resource各门保持false；旧Common/source-factory findings保留。启动审查原件及快照保持原样，新可读性能说明同时记录了原追加段的编码问题。
