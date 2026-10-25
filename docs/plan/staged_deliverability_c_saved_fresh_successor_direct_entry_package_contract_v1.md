# C：cold-entry 执行证据冻结与机械封装合同

2026-10-25，DRAFT_NONAUTHORITATIVE，接续[执行合同](staged_deliverability_c_saved_fresh_successor_direct_entry_contract_v1.md)。本合同在最终封装执行前固定单独的机械目录；不改变任何执行/科学/资源准入，也不扩大原pytest240s、static/probe80s和总320s时间账。

原`checks_01`的224文件/16MiB上限保持。所有已登记执行终态后，记录其exact count、总bytes、逐文件bytes/SHA和canonical inventory root，再冻结为只读；此后不写、移动、压缩、删除或改写其中任何记录、旧epoch、raw stdout/stderr、started/result或snapshot。预计值不能代替最终admission，超过原帽即停止，不能用本机械目录补做执行。

独立`final_package_01`最多32文件/2MiB，仅承载三个stdlib脚本（capture/finalizer/oracle）、这些helper自身快照、execution inventory、导航/文档/支持pins，以及三次机械命令各自stdout/stderr/exit/helper manifest。不得新增pytest、probe、source snapshot或重跑执行证据。两目录组合最多256文件/18MiB，不能表述成仍在原224文件帽内；本报告及docs单独计为文档交付。原F的8MiB/64files/17targets不变。

允许的分层：先固定execution inventory（含exact names/count/bytes和root SHA）；再捕获三个机械helper当前bytes及snapshot；finalizer create-only生成nav/document/support pins，support不包含自身及未来机械exit；两次保存oracle通过独立wrapper在退出后补终态wall/source/helper首尾pins。oracle先核execution inventory完整集合和root，再核source epoch、最终node union、8 probes、全部历史保全和隔离前序oracle。只允许执行已hash固定且纯stdlib、不调用可变ENTRY/helpers的前序oracle，不能拿当前实现执行结果当冻结真值。

时间账跨目录累加全部`.exit.json`，含原旧epoch与真实probe；本目录finalizer≤3s、两次oracle各≤12s，并按原80s static/probe剩余量准入，单次仍≤40s。本目录不另起时间预算。失败和超时保留；本目录超过32文件或2MiB即保存未完成事实，不转移、裁剪旧证据。

计时口径修正：执行目录既有wrapper的`wall_seconds`实际为target子进程wall，不包含它自己的source/helper前后哈希，原记录保持不变。因此240/80/320账只支持其明确的已记录slice，不证明整个工作流或交互wall≤320s；完整流程wall成本仍未验收，不能据此打开资源门禁。机械wrapper从最早常量初始化后计时，覆盖inventory/snapshot/child/前后哈希；其`measured_action_seconds`与另收0.5s尾部reserve分列，账面wall为两者和。尾部reserve不是观测或严格OS上界，完整工作流预算仍标false。

support清单排除自身后，由finalizer stdout给出exact support pin，外层finalizer exit绑定同pin；saved/terminal的预生成snapshot都锚同一pin，oracle核support闭集及helper/execution freeze/nav/document/finalizer snapshot全部必需项。后继层不得接受删项或重写的support清单。

机械记录另逐层pin：saved snapshot精确绑定finalizer四份snapshot/stdout/stderr/exit，terminal snapshot精确绑定finalizer与saved共八份原字节。oracle核exact predecessor集合和每份bytes/SHA；terminal自己的四份不自指，由最后Git index/commit逐blob比对和远端hash承接。此链不新增文件或时间预算。

CLI要求当前source/nav匹配；未来archive仅可报告冻结节点，mutable漂移时current节点为0。full runtime、trusted role upstream/bootstrap、OwnedChild/Job quiet、actual F、科学采用、资源及正式门禁仍false。root唯一writer，独立只读PRE_SEAL，完成后按已授权范围Git同步并读回远端/空porcelain；不seal或出official receipt。
