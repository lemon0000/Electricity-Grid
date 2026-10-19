# Reference sequence 同步窗口复用设计

状态：DRAFT_NONAUTHORITATIVE / design only。2026-10-19，root 唯一 writer；
`/root/parent_window_review` 提供只读代码分析。尚未实现、测试或形成 official verdict/运行权限。
48 的读取 overlay 没有获得完整路径收益；后续原型以 entry11 的已有局部合同为基础，不默认叠加 entry12。

## 范围与锁

首版只考虑 Actual 的 `run_pre/run_release/run_quiet/run_post` 和 public `validate`。
Parent3 的 run 在 `h1_selector_parent_controller_development_v3.py:237` 至 348 持有原 reference guard，
validate 在 389 至 399 持有该 guard。维持原来的锁顺序、生命周期及外部 callback 边界。

两种 construct 窗口继续逐次 fresh：source_window_v1:243 对 construct 强制 ref=None，
Parent3:97 在 construct_prepare 后才设置 reference owner，construct_finish:122 也不持 reference guard。
首版不把新锁获取和构造失败恢复变更混进复用。

## 静态调用量

| 每个 Actual 窗口 | 原 reference sequence.inspect | 后继上界 |
| --- | ---: | ---: |
| construct_prepare | 4 | 4 |
| construct_finish | 20 | 20 |
| run_pre | 12 | 2 |
| run_release | 12 | 2 |
| run_quiet | 16 | 2 |
| run_post | 28 | 2 |
| 每次 validate | 16 | 2 |

可优化部分为 `68 + 16V -> 8 + 2V`，最多减少 `60 + 14V` 次。
一次 run 加一次 validate 为 `84 -> 10`；构造及 capture_actual 仍 fresh。
这是静态 reference-inspect 调用量推导，不是运行时间预测、完整预算或测得的收益。
推导来源：snapshot_v2.rebuild:190 双 _build；worker_v2.request_document:78 单 rebuild；
preparation_v2.prepare:105 双 request_document；bind:148 双 prepare。

## 私有路由与诚实 payload

在新 source-window engine 中给克隆的 snapshot._build 注入私有 sequence proxy，保留 canonical
_root 和 _configuration，只替换 inspect。首次合法调用执行原 canonical inspect，随后合法调用
借用；source tail equality 成功后用保存的精确参数再执行一次 canonical inspect，比较完整签名。
body 失败时不新增 tail I/O，直接记录首错并清除缓存。

canonical sequence.inspect:185 返回 fresh_at_return=True。借用路径不得返回其原完整 envelope。
私有 _build:139 实际只读 request_sha256 与精确 ReplayResult；每次返回新的这两字段 mapping。
新 execution identity/receipt 明示 entry_original_fresh=1、exit_original_fresh=1、borrowed_calls、
per_call_fresh_at_return=false、bookend_only_freshness=true。
只声明 scientific payload compatibility，不声明 legacy observation/report 相等。

## 依赖、freshness 与失效

每窗只接受一个 exact reference key；第二 key 为错误。至少绑定 reference root/terminal/request、
frame/disclosure/before、完整 args 及递归 exact types、config 与 _configuration digest、
Actual raw/declaration reference、原 reference Parent/completion/guard/creator、
ExactSource binding/entry signature，以及 _build/sequence/replay/physical classes/stable read/
solver guard 的 callable/code/default/global identities。

entry/tail 比较完整 canonical _snapshot view：完整目录 namespace、全部预期文件的 digest/stamp/cap，
不能仅比 terminal SHA。原 snapshot 参见 owned_selector_sequence_v1:98。
两个书挡间的 mutate-restore ABA 不在此合同内；各窗口互不复用，不跨 Job、callback 或 owner 生命周期。

ReplayResult -> SelectionCandidate -> PhysicalCandidateCarry -> disclosure 的 frozen dataclass 是浅冻结。
stage_diagnostics 当前在 origin_selector_replay_v1:319 为 primitive tuple，records 为 bytes tuple。
每次 borrow、下一次 borrow、tail 和 clear 前，仍需 exact typed graph 与 canonical encode/digest 检查。
借用仅能来自私有克隆 _build 的精确 code/globals/owner frame；原缓存 mapping 不得逃逸。
无法证明 caller confinement 或对象签名时，依赖该证明的复用保持阻塞。

Actual output inspection保持逐次真实执行；只减少它嵌套的 reference saved-sequence replay。
Parent3._inspect:218 与 output_inspection_v2:78 的 transport/output 文件检查不缓存。

## 后继 cut 与验收

最小原型：独立 reference-sequence window engine、source_window_v2、Parent4 及对应测试。
canonical snapshot/sequence/preparation/inspection/worker 文件保持原字节。
连接 Handoff 时，因 exact-type 和硬 import，还需要 parent-validation_v4、post-negative_v3、Handoff6
及 integration-helper 后继；旧 validation/post-negative 各自克隆 _build，不能漏接。

实现前固定矩阵并覆盖：

- 五个 eligible 窗口的 `12/12/16/28/16 -> 2`；construct `4/20`、capture 和 Actual-output inspect 不变。
- entry/tail canonical result 与原 typed payload differential，原数学、限值、输入、状态延续保持。
- caller/globals/thread/reentry/第二 key、owner/guard/completion/source/code 漂移。
- 缓存返回对象各层篡改，saved 文件增删/替换/stamp 漂移。
- entry/tail/body/cleanup 每个失败窗口，首错、真实锁与缓存清除，输出对象原消费生命周期。
- 真实 completed reference saved-root 的有界零 Job/native/solver 探针；随后才考虑完整普通链路。

仍需新的 scoped PRE_SEAL 和完整 DAG 性能审查；复用旧链主体/独立补验，不重跑主体。
genuine N0 完整 registry/receipt/oracle、typed graph、完整优化链、资源与所有正式门继续 OPEN。
