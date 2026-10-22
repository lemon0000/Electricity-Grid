# C：保留闭包后继的短保存重放探针

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。针对最终领域审查F14及v2草稿F15，使用[保留规格](../model_spec/staged_rts24_journal_retention_v2.md)和独立journal_v2；旧attempt_01全部绑定字节/失败原件保留，不重跑或覆盖。本包仍遵守agent.md第7–9节，根唯一writer，明确路由的sol_reviewer在启动前只读审查当前v2代码/测试/合同。

## 固定问题与DAG

只测新保留检查是否使保存、关闭及fresh重放保持原科学state，并测声明删除失败能否停止采用。复用旧attempt_01/full_temporal保存的前两条HourEvidence/actual及第二步完整state；旧核心manifest先逐SHA验证，并在结束后重新核验。不调用旧writer，不重新生成公共或解析点，不执行solver/native或下载。

1. 独占closure_probe_01、外部watchdog、Python/import、当前v2/runtime及直接文件SHA、旧531核心及13旧直接源/旧B1–B3核对。
2. 从旧typed CAS读取两条保存row和期望state；使用同一显式解析late Fixture，full_temporal，h0…1，原观察结束仍为5。
3. v2 create →两步prepare/固定策略/旧actual→accept→独立audit→pure pack期望全集→CAS/root出版前后精确检查→finish缺下一输入检查点。完整state与旧第二步逐值/科学及typed SHA一致，任务债务40右删失。
4. 外部trusted binding→一个顺序fresh子进程→v2累计key集、根链及全部数值/业务重放；不生成新evidence。
5. 三个单独failure case：begin前移出fixture CAS；entry1 rename后移出旧fixture CAS；entry1 rename后仅报readback unknown且CAS完整。前两者writer不采用，fresh拒绝缺失闭包；第三者fresh确认一条final但不制造terminal。故障移出的字节保存在case目录，保留journal内缺口，不恢复或重试。
6. source/旧工件末端SHA→报告/completion→退出→watchdog稳定终态/RSS→只读postcheck。

成功路径writer与fresh各`3T(T+1)/2+2T=13`次子图编译，T=2，描述各44（h0权重8×3，h1权重5×4）。三个failure分别0、3、8次，共11；总**37次/121描述**，P0=37、raw=10、恢复min/max各37。旧full compiler及solver/native请求均0。编译会计不包含typed解码/pack重构、环境/目录扫描或report写入，这些计入整体wall和读写计数。

## 优化与边界

复用已有完整点/证据和旧第二步state，不重跑三方法五小时或新query。保留独立audit、原阈值及同操作ReadView末核。新增完整CAS key集合和root保留检查先采用显式方案，承认其前缀/元数据增长；没有安全增量证明时不省略。只有full_temporal两小时实测，其他方法由相同保存路径的普通正例覆盖，不外推长时域或公共网性能。

## 一次资源与停止

新目录`results/tables/staged_rts24_journal_v2_non_authoritative/closure_probe_01`仅一次启动，无重试。watchdog复制已测v1异常安全/终态扫描逻辑，改为60s总wall、20s无事件进展、单fresh30s、采样进程树512MiB、输出8MiB/600文件；0.2s采样、父+至多一fresh顺序并发。预计数十秒，依据旧保存短路径而非新准入结论；超限/源漂移/闭包不等/child失败即停止并保留stdout/stderr、pending/orphan/缺口及终态，不顺延预算。

直接绑定v2源、测试、两runner、本规格/合同及旧保存输入的completion/report/三个被用entry或genesis角色；间接执行的旧diagnostic helper及其13直接源和28 runtime源一并检查，v2另核28 runtime源/十外部入口/版本。启动前保存Git与安全进程快照。新source/contract/保存输入一经start绑定保持字节；任何后续行为修复另successor。普通测试和sol_reviewer启动前findings须先闭合。

验收以两小时完整state与旧保存一致、fresh一致、逐角色37/121闭合及三个失败裁决为准。新目录源码/manifest、旧531核心和B1–B3字节首尾一致。正例完成不改变服务是否通过，更不关闭公共数值/g、完整F/X、C/D/E资源、native或formal权限。
