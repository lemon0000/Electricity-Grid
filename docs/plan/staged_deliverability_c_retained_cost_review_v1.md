# C保存结构成本审查

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。本页接续[journal_v2交接](continuation_handoff_20261023_journal.md)，补正旧规格中将完整key/root/前缀工作统一概括成O(T²)的表述。旧绑定规格、源码和保存工件保持原字节；本页给出适用条件和分层成本，不赋予运行权限。

## 增长与实际路径

令t为已提交小时数，K_t/B_t为累计CAS对象数/字节，E_t为第t条entry字节，J_t为全部root文件字节，C_t为保留cohort数，S_t为展开科学state的编码量。以下阶数假设单步网络/点形状与数值位数有界；cohort、allocation、Fraction位数另计。

- `after_cas_keys`逐entry保存累计全集：若每步新增对象数有界，K_t通常线性，E_t=Θ(K_t)，累计root存储J_t可二次增长。
- CAS虽共享frame和点，每个ExecutionState根仍内联records tuple、row字典及DebtLedger/cohort。新state快照的历史部分含Θ(t+C_t)，全部历史state保留使累计B_t可能二次增长。
- 每个成功hour有4次`_check`、10次完整CAS inventory、6次root inventory；finish分别为2、8、4次。每次_check还读genesis/head及完整旧entry链。因此writer累计读取/解析含ΣB_t和ΣJ_t，可能三次增长。单次fresh的存储读取含4次全CAS inventory、所用对象的首次读取/末端读回及全部root；在上述有界增量假设下约为二次字节量，不能与逐步writer混为一谈。
- 科学审核的reference编译数按前缀二次增长；audit每个历史row还摘要其prior，单次长度L的审核含Σ_{i<L}S_i。外层逐步重放反复审核时，S_i线性即可再产生三次编码量。单独调用一次digest(state)仍只对应S_t；不能直接称其三次。

源依据：[journal](../../src/staged_rts24_journal_v2.py)、[CAS](../../src/staged_rts24_evidence_store_v1.py)、[科学audit](../../src/staged_rts24_causal_audit_v2.py)。runtime源/解释器反复hash、目录stat、pack重构和JSON复杂度扫描另计。现有read counter含逻辑重复读取，不能解释成物理磁盘I/O或以总wall反推各阶段占比。

## 本轮只读核算边界

[核算工具](../../experiments/staged_rts24_saved_size_audit_v1.py)只读v1/v2已保存completion及其531/138核心文件，对固定成功v2 journal解析typed引用图，不实例化模型、不解码科学对象、不调用策略/replay/solver或生成数值点。两个completion SHA预先固定；逐文件核hash/bytes并在末端复核原字节。限定单文件1MiB、总成功逻辑读8MiB、30秒合作式检查、单个输出128KiB，独占新目录`results/tables/staged_rts24_saved_cost_v1_non_authoritative/audit_01`，只保存一次JSON；没有新性能测量或硬配额声明。普通静态核算失败即保留已有输出，不重跑旧attempt。

工具列出每条entry的K/ΔK、B/ΔB、累计root、key列表字节、state records/cohorts/字节、payload与state的可达闭包、CAS kind分组。另按已绑定源码推导成功append的inventory/check逻辑字节分量，明确不含publish/get/readback、runtime、其他case与报告。

一次静态核算的机器报告保存在[report.json](../../results/tables/staged_rts24_saved_cost_v1_non_authoritative/audit_01/report.json)，解读与开发核验另存于同目录，不能倒写本页绑定字节。

若旧库存字节为B、写payload后的库存为P、新库存为N，则hour的10次CAS inventory合计读取`5B+2P+3N`，finish的8次为`3B+2P+3N`。旧root字节J、旧head字节H、新root字节J'，hour的root inventory加_check内genesis/head/链读取为`9J+J'+4H`，finish为`5J+J'+2H`。这些公式是成功路径的结构子项，不是总read counter、总I/O或预计wall。

## 优化决定与后继顺序

1. 先在新版本合并同一append内的pack/batch put/inventory，保留采用前完整CAS/root/目录/runtime核验；begin到commit之间有外部数值等待，不能跨该窗口盲目复用。
2. 后续用增量key表及可核累计根、持久record前缀等降低元数据和历史state重复编码。仍须证明旧CAS/root删除检测、trusted前缀、发布未知与fresh等价，不能退回v1的缺口。任何变化使用独立successor及失败窗口审查。
3. 独立完整科学audit先保留；同操作已审前缀复用须证明依赖freshness与失效条件。不能为性能省略parent/child/KKT/ledger检查。

公共数值接口开发与上述成本核算并行。完整公共轨迹/139节点合同层/长cohort及真实数值失败尚无代表实测，C整链与D/E资源保持OPEN；现有两小时解析结构不支持公共wall或192小时准入。
