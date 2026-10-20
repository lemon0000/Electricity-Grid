# 三小时整链性能复核

2026-10-20，DRAFT_NONAUTHORITATIVE。本文件整理终态实测；启动前原件为 [整体审查](design_and_performance_review.md)、[checkpoint 与监视设计](reopen_checkpoint_design_v1.md) 及每次 request 的 tested_bytes。没有由本记录生成运行权限。

DAG：synthetic source/registry → fresh N0 fake Windows Job → owner genesis → 每小时 ready 历史 batch → h>0 的 durable attempt/normal Job → 独立 current → 共同 Rref/各 active Actual → intent/ticket/原科学 transition → paired 前独立 fresh → outcome/ticket → 完整 replay → 缺 h3 的 ready/attempt/source 拒绝 → live checkpoint → 全 close → fresh constructor → public inspect → 独立 historical → parent snapshot → 全 close/全文件 SHA → identity bookend/报告。

复用旧 hour0、旧两小时整链、batch v2、36+23 项 guard 及本次 unit06 六项科学/预算证据。1279 个继承 pins 精确相同。保留当前 batch 的两次独立 Reader，current/history/业务/数值状态不跨 operation 缓存。15 个 test-only 纯静态 identity 目标共有 147608 次调用、15 个原函数计算；先恢复别名再逐键原函数 bookend，全部相等、句柄关闭。该测试设置未测生产原始开销。

当前 complete path 的 owner 源层实测 API=32、prefix-hour 权重=64；每个 API 的 Reader constructor+explicit inspect 使 parent inspect=64、其 prefix-hour 权重=128。此计数排除独立 historical、parent snapshot、内部 anchor 与 normal 内部额外遍历，不能当作全部 I/O。最大一次 batch 33.283s、最大 selected frame 数据 62516 bytes；并不构成 192h 内存证明。

| 不重叠 trace 区间 | 秒 |
|---|---:|
| start → N0 terminal | 102.246 |
| N0 terminal → h0 paired | 120.101 |
| h0 paired → h1 paired | 293.674 |
| h1 paired → h2 paired | 490.879 |
| h2 paired → h3 缺源拒绝 | 72.204 |
| 拒绝 → checkpoint 保存 | 0.193 |
| checkpoint → 全关闭/初次比对 | 0.162 |
| 全关闭 → fresh constructor 验证 | 68.841 |
| constructor → public inspect 验证 | 62.356 |
| inspect → 独立 historical | 29.578 |
| historical → parent snapshot | 14.512 |
| snapshot → 最终关闭与结果保存 | 0.144 |
| fixture、入口、bookend 与监视收尾 | 60.078 |
| 外层总墙钟 | **1314.969** |

trace 首尾合计 1254.891s；其它 60.078s 由总墙钟减得，并非单独计时的内部阶段。嵌套 owner timings 在 postcheck JSON 中，不能再加进上表。normal 子阶段合计 412.519s、source_selectors_paired 260.603s、final_full_replay 123.465s 是 body 内观测，不能相加为整链总时长。

| 固定预算/观测 | 结果 |
|---|---|
| 总 wall | cap1500s，actual1314.969s；没有延长 |
| 无活动 | 120s；文件 signature 或 sampled owned-tree CPU 前进至少0.25s |
| CPU 口径 | `(pid,create_time)` 区分进程；monitor 自身不计；CPU 活动不是算法进展或科学通过，wall 仍固定 |
| normal Job | 每个240s；3 个 fake Jobs、完整15 stages；正常 TimeLimit5s不变 |
| selector | 每小时上限13次/13s；34次 fake captures，单次合成预算1s |
| 采样树 RSS | peak403148800 bytes，约384.47MiB，cap1GiB |
| 逻辑存储 | peak23223898 bytes，约22.15MiB，cap128MiB；不计磁盘 allocation |
| 终态 | exit0、source unchanged、8观察PID均退出、monitor/cleanup errors空；完整未观察进程树证明仍false |

昂贵失败路径保留：connected_01 outer250.047s 在首小时 selector 前因旧 toy aggregate budget 拒绝；connected_02 outer1343.297s 被旧的 file-only 无活动监视停止，原 attempt 未续期或追认为通过。新监视先经 detached03 0Job 完整重放实测，再用于 connected03。原只读阶段没有文件写入但有真实 CPU 活动，修正的是监视口径，所有科学检查与验收限保持。

关闭前 checkpoint 只增可审计留存和 SHA 比较，不替代源重建：本次 constructor、public inspect、historical 与 snapshot 都仍调用原路径。Windows 持有 execution.lock 时通过 owning stream 读取真实原字节并恢复游标；关闭后正常读盘、fresh holder/owner 再持锁后仍逐文件比对。独立 0Job Windows probe 及完整链覆盖这三个阶段。

连续 T 个合法 active 小时、每小时一次 run_next、尾部一次 reopen、没有额外 inspect/pending/终结分支时，batch v2 的源层 API=`8T+4`，prefix-hour 权重=`4+4T(T+1)`。本例 T=3 的基础值28/52，加缺源 ready 和显式 inspect 各2/6，得到32/64。T=192 的条件性基础值为1540/148228；该推导未覆盖完整 episode，也不是 runtime 预算。

三小时后半段仍由 prefix/normal/保存重放占主导，完整时域的实质性能瓶颈尚未闭合。下一步先做边界路径的调用图与只读保存证据审查，明确 dependency closure、freshness 和失败失效条件后才允许复用；不得直接照此运行192h，不得缩短168/24合同、跳过来源前缀或用静态单小时重复代替连接验证。针对完整目标包的 production overhead、native solver、RAM/storage 与总预算仍未知。
