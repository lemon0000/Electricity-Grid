# 校验 I/O 优化开发报告

2026-10-16。范围为里程碑 2 的合成校验性能修复；完整 hour-0 出口仍为 OPEN。

已实现可执行的固定字节入口 `launch_validation.py`，由它加载 `validation_entry.py`：

- `CodeReadLease` 只复用 145 个固定 SHA256 的代码文件。Windows 文件句柄禁止写入与替换，所有祖先目录保持不能重命名；退出时检查路径身份、磁盘字节与持有句柄字节并释放句柄。
- `MetadataParseLease` 只复用 8 个已锁定 METADATA 的 version 解析值。每次仍调用原生 version/distribution discovery；路径变化、外来 distribution、实例 read_text 覆盖等走原 getter，parser/helper 替换拒绝。每个 pytest call 清空解析值并重设 discovery window。
- pytest 的 reader/getter 身份覆盖整个 invocation，包括 collection、fixture、call 和 teardown。每个 call 保存 nodeid、结果、receipt；终态保存调用统计、解释器恢复及前后 hashes。
- 145 个代码文件与 604 个测试/保存 fixture 文件均保留 tested bytes，并对两种计时模式对称复核结束时 hashes。

原始 source、registry、SQLite、保存记录和数值重放结果继续经过原有读取与校验；科学合同、模型、数值限制及成功验收路径没有改动。此次没有执行真实 native 校准或正式实验。

## 实测

所有计时均使用同一份 chain_06 保存记录与原生产模块，在原 chain_07 仍活动的相同条件下串行执行。每个成员在单独进程中使用空 pycache prefix。

| 开发包 / 顺序 | 原版 arm 秒 | 优化 arm 秒 |
|---|---:|---:|
| revision02 pair02：原版后优化 | 52.443 | 35.220 |
| revision02 pair03：优化后原版 | 51.996 | 35.488 |
| revision02 pair04：原版后优化 | 52.608 | 35.782 |
| 最终包确认：原版后优化 | 52.023 | 35.761 |

前三组中位数减少 32.33%；最终包确认减少 31.26%，其整个成员进程计时为 60.023 → 44.244 秒。八次科学输出与完整 audit 的 SHA256 分别均为：

- scientific：`e16f70617322f0304659955c0f2a3466fc329f59dae6b6ac8c11a8eb09fe7b5f`
- full audit：`1b87bd9d42b31add20d672cdcffa8809f4d07de2bb0382dac8cc6395577577e4`

每次 461 个保存文件未变。最终包的两种模式均另证 145 个代码文件和 604 个测试闭包文件未变。revision02 的 plain 成员当时缺少单独的代码 after-pin 证据，因此保留其测量范围限制；最终确认补齐了该证据。前三组与最终包分别绑定各自 manifest，不能把前组说成最终字节上的三组测量。

原先 6h43m 的 common genesis/inspect 区间没有在本优化入口下完成计时；本报告的比例不能外推成全链耗时或 native 预算。缓存代码原始字节约 1.97 MiB、METADATA 约 0.16 MiB；这也不构成完整任务的 RAM/存储准入。

## 验证与失败保留

- `unit_pinned_04/terminal.json`：42 项，41 通过、1 项因 Windows 符号链接权限跳过、0 失败；真实 junction、替换/写入阻止、已有 writer、guard 替换、初始化失败和 whole-pytest 失败清理另有已通过覆盖。
- `regression_pinned_04/terminal.json` 和 `pytest.log`：62 collected、62 passed、0 failed；62 个 call 及 session 的 receipts 完整，145 code / 604 test / candidate bytes 均未变，退出设置恢复。
- `current_entry_pair_01/terminal.json`：最终固定包的两成员 exit0，科学输出与完整 audit 一致。
- `fixed_timing_pairs_02/terminal.json`：此前六成员 exit0 的交替计时。
- `regression_pinned_03/` 保留 60 passed / 2 failed 的原失败。原因是逐 test 替换 reader 破坏了导入期 guard 固定的身份；修复为完整 invocation 生命周期，原 guard 保留。
- `package_revision_01/02/03/`、先前失败 pair、code-view 诊断与 phase 标签 erratum 均保留。code-view 方案未显示额外收益，没有进入最终包。

最终 package manifest SHA256：`0cd4511072ee11cc89a942b3eb76a3a91de4390ca1af5febe0981c216976a59a`。
最终 launcher SHA256：`13333f85abe556fbcfffe35c611149a937076de3422bde6c7f3b471f71242415`。
测量 harness 从外层核对 launcher literal SHA 后 compile 对应 bytes；内部先核对 manifest 和 members，再从校验过的 bytes compile 候选，避免导入旧 pyc。

入口的已验证用法为 `unit`、保存 arm/phase 和已列出的三个窄 pytest suites。完整 end-to-end target 已可通过同一 pytest 入口选择，但尚未在该入口下完成完整链、独立保存重放与报告验收。需要在后续完整合成验证中取得这些终态，不能由 62 个局部回归代替。

## 当前主链与后续

原 chain_07 的 wrapper 43640、pytest 27888、supervisor 42184 保持原进程。已完成三个独立 N0、common、Rref 和三个 Actual；最新完成标记为 `Actual_network_only_shared`，累计 74743.198474 秒。当前继续提交前失败检查，完整 paired commit / close-reopen / 独立保存重放终态尚未取得。原链 36 个启动代码 pins 复核未变。

只读分析确认，对缺失 Actual 提前跳过 common 会改变失败优先级和 freshness 窗口；它没有作为同合同优化接入。当前继续收敛完整链的真实终态和分段耗时。

本目录为 non-authoritative development evidence。独立 PRE_SEAL findings 见 `preseal_audit_notes.json`；未封存、未产生 official verdict，resource admission、formal execution readiness 与正式运行授权没有因此改变。
