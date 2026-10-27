# C/F：pre-ENTRY 本地输入持有与真实冷探针检查点

2026-10-27，DRAFT_NONAUTHORITATIVE。接续[根 catalog 交接](continuation_handoff_20261026_saved_fresh_root_catalog_v1.md)、[初始范围](staged_deliverability_c_saved_fresh_pre_entry_lease_scope_v1.md)、[cookie 修订](staged_deliverability_c_saved_fresh_pre_entry_cookie_repair_v1.md)及[descriptor 修复后继](staged_deliverability_c_saved_fresh_pre_entry_descriptor_repair_v2.md)。root 唯一 writer，独立只读 PRE_SEAL；没有 official verdict、review receipt、production seal 或运行授权。宽 goal 继续 active。

## 当前实现与证据边界

新增独立 v2 stdlib bootstrap，以 `EXE -P -B -s -S -c <held loader>` 运行。父端固定 manifest/raw/pins、Source49 开发 epoch、EXE、flags/env/cwd/argv，先持 Popen process HANDLE、核 PID/creation/image，再通过有界 stdin frame 释放 child。early audit 在 codec/其他 stdlib import 前安装；frozen os 添加的 DLL 目录 cookie 强持至结束，关闭前标记 attempted，避免重复尝试。

新 child 先匹配独立 discovery 后 create-only admission 的画像，取得本进程/线程的真实不可继承 query HANDLE，才读 Source49。不可变 raw 与原方法、绑定、控制状态和资源 owner 由 `LocalPreEntryLease` 强持，唯一 owner 引用赋值完成同进程 `LocalPreEntryInputs` 转交。正常 probe 在目标仍 live 时仅编译已持 ENTRY raw，随后关闭句柄、退出。序列化记录证明曾持有和消费，报告时 live=false；不能由 stdout/JSON 重建该能力。

Source49 集合与全部原字节保持，epoch 仍为 `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`。未执行 ENTRY 顶层、导入科学 adapter、读取 P1、启动 F/OwnedChild/Job/native solver。新 bootstrap/probe payload 的 exec 不等于 ENTRY exec。

整个受控 compute CPython 发行版、VM/compiler、stdlib/pyd、必要 DLL、loader/kernel 是明确的条件性 TCB assumption。六个固定文件和 startup profile 都只是路径/文件观测，不认证 loaded Python 图或 native 行为。普通父端观察 P、绑定数据 D、条件性本地连续持有 L 不证明外部认证来源 E 或上游角色 owner U；E/U 仍 OPEN。原 import v3 的 baseline4/旧 direct-main argv 不能用于当前 baseline3/新 argv；没有伪装旧 main 或重新执行 site/.pth。

## 实际检查结果

当前 v2 的 33/33 unittest 通过、无 skip；包含原 29 项及 fresh compiled namespace 正例、裸 __new__ function、同函数重新包装 staticmethod、底层 code 替换四项。自动 staticmethod 仅在 `_LocalInputs.__new__` 被精确允许，底层 function/globals/code/default/closure 仍完整检查；descriptor 自身与 __func__ 都被持有。

独立 discovery、profile_admission、九例 cold probes、fresh saved metadata 核验均 exit0/accepted。画像观察 83 个 runtime disk 文件、合计 15,242,498B，符合单文件8MiB/合计32MiB的 census 范围；实际保存的是 pins，非复制全部文件。profile 为 26,707B / `882bdc2b9d68e3cf6e4c85cf9351ef9aadd9d37fe708ff15dfde10338e127ffc`；transport 为 19,908B / `6f77d85735a832e0c5ad26c744732998fa5375595e8b804f037043395d964d08`。

| cold case | 实际终态 |
|---|---|
| normal | child0；294 次受控 source open；真实同进程移交；仅 compile；source CONSUMED / target CLOSED，两个 self HANDLE 各 close1 |
| manifest_flip / flags / environment | 精确拒绝目标故障；未取得 self 资源或读 Source49 |
| partial_handle | process HANDLE 已开、thread 未开时注入；close=[1,0]，resource CLOSED，Source49 open=0 |
| binding | 构造后 helper 替换被拒；Source49 open=98，close=[1,1]，原异常及清理 secondary 保留 |
| early_source | self 前项目 open 被 early hook 拒绝，未打开 self、未读 source |
| transfer | commit 前注入拒绝；Source49 open=196，close=[1,1]，未误报移交成功 |
| timeout | 未 release、无 child stdout；父端 kill/wait，writer/reader/pipe/process HANDLE 终态，不声称 child 正常 close |

每例 parent process HANDLE、stdin、writer 和 reader/pipe 均终态，无残余 cleanup 错误。JSONL 每个 append 后及阶段终态都逐字等于实际返回 records 的 canonical concatenation，再由 probes exit 固定。saved 在新普通 child 中只核保存记录/原 bytes/pins/前驱，不重跑 bootstrap/科学逻辑；其观测峰值 WS 为29,962,240B，不能替代整链 RAM/硬停止准入。

## 两次失败、修订与费用

初始登记后29项逻辑测试成功；首次 discovery 因 probe 已关闭 DLL cookie、loader finally 再次 close 而 child1/accepted=false，stdout profile 未采用。cookie 修订重测29项、独立 discovery_repair 和 admission 成功；首次 normal 在 SELF 因自动 staticmethod 被当裸函数拒绝，self 未开、Source49 open=0。两条原失败、所有 code/transport snapshots、raw、plan、receipt、exit 均保持，累计不接受记录为14（前驱12+本轮2）。不重写旧 accepted 或借修复抹去费用。

v1 原结果根34文件的 canonical整集 SHA 为 `7b0311976bc0d1e7f4fa7874d9f31ac2981a3df778864e751b0b348e41c46d2f`，v2 子目录显式排除在该历史集合之外；旧四 helper 与两 controller 同时固定。当前只接受 `descriptor_repair_02` 的新 helper/profile/receipt 链；v1 的正常探针仍失败。原固定合同根和 dependency image 语义修复按其原 data-only 范围保持，本地 L 不能升级为实际 issuer/capability image。

三次登记合计0.5979232/3s；本 scope 含全部失败计费 static7.1758692/50、unittest1.6352277/30、合计8.8110969/80s。九例当前 probes4.1089185s，加原失败 probes0.2742181s，共4.3831366/30s；当前 saved0.4680273/8s。全累计 static161.3614287、pytest366.4889797、unittest2.4766955，总530.3271039s。旧 static120 帽失败与 import8MiB超帽保持；编辑、审查、Git、最终 exit 序列化及初始 Python 启动不在本 capture 计费内，不能称完整 workflow wall time。

## 恢复入口与下一项实质工作

读取 `results/tables/staged_rts24_saved_fresh_pre_entry_lease_v1_non_authoritative/descriptor_repair_02/{registration.json,probes.exit.json,saved.exit.json,saved_report.json,probe_cases.receipts.jsonl,pre_seal_findings.json}`，核 Git/进程、原34整集、helper/profile/Source49，再续账。独立只读 PRE_SEAL 终态无剩余 must-fix；新增 findings 后整个根61文件/1,034,019B，仍≤64/8MiB。所有已执行 controller、原记录及 helper 世代保持；不能再次调用 create-only action 覆盖目标。catalog 旧54根/76节点仍是原冻结的非权威图，不由本检查点改写其 witness/status。

下一步应在一个新、明确登记的同进程接线切片中：消费 live LocalPreEntryInputs → 从已持 ENTRY raw 建立真实的新 module namespace → 核 module initialization/code/global/class/descriptor → 定义并连接新 B_S import profile → 由一个确切 owner 持续持有原 self 资源及 runtime 状态。不能止于再次 compile/JSON，也不能伪装旧 direct-main；先固定完整调用 DAG、规模、预算和失败窗口，再运行短诊断。

transitive live runtime、finder registry 深层 mapping/callback、外部/native 叶、successor request/context、broker ACK、真实 retained owner、issuer/one-shot permit、quiet/return/G2/G3/H3 仍 OPEN。旧 RoleStore/FileBootstrap/OwnerInputs 继续拒绝这些本地/data 对象；runtime v2 UNDECIDED、v3 proposal admissible=false；actual F、native授权、科学/资源/正式/运行门禁全部 false。

Git仅发布本轮新 helper/tests、范围/交接、新结果根与四导航短 prefix；并行论文/文献/绘图和共享导航旧 body 保持。远端 hash 与最终 worktree 状态以本次发布后的实时核验为准。
