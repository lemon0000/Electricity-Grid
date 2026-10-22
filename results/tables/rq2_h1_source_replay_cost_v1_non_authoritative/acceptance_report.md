# Source重放成本分解与下一优化边界

2026-10-21，DRAFT_NONAUTHORITATIVE。本轮补齐当前三小时source路径的函数成本与调用量；没有实施或采纳新的优化，完整168h/≤24h整链预算仍未闭合。

`run_profile_v1.py profile_02`正常终态exit0：一个保存3h prefix的原historical Reader，两次parent inspect；Reader脚本elapsed74.837764s，其中replay内部metric74.159304s，cProfile root cumulative74.289820s；runner outer79.578s，sampled tree RSS206053376B、logical2623169B。所有耗时含cProfile/诊断开销，不是未profiled吞吐或192h预测。1302 source pins未变，PID16072及direct conhost34372退出；0新normal Job、0 real native。

三个hour的normal audit canonical bytes与旧owner intent逐字相同，historical proof在JSON解析后作Python结构对照相同；465个case文件及444个owned文件SHA保持。只重装原synthetic source/catalog/manifest fixture，沿用旧15个静态identity memo targets；其中本次5个实际计算、4676次wrapper调用。没有缓存source/current/history/input identity或metadata.version；这不证明生产开销或完整动态闭包。

| 当前单Reader，H=3 / 每小时5 stages | 实测calls | cProfile cumulative，秒 |
|---|---:|---:|
| parent完整inspect | 2 | 73.206409 |
| constructor调用的inspect边 | 1 | 38.211012 |
| caller显式inspect边 | 1 | 34.995397 |
| inspect_job | 12 | 62.170465 |
| timed_stage.inspect | 60 | 41.826，详见原profile |
| normal_input_identity | 1560 | 38.709371 |
| normal_input_identity中的_dependencies | 1560 | 36.393289 |
| importlib.metadata.version顶层函数 | 10922 | 26.701224 |

各行存在包含和嵌套，不能相加。38.211/34.995来自call_edges中两条不同caller→Reader.inspect边；它们证明重复发生的位置，不是后继的实测节省。10922个顶层version调用与其底层同名method调用是同一工作链，不能当作21844次独立查询。profile共78267919 calls/76305368 primitive calls；原pstats、全部functions及caller edges均保留。

原调用关系为 `prepare_many → replay_prefixes ×2 → parent.inspect ×2 → 每小时(clock.inspect → inspect_job，ChildReference.inspect → inspect_job) → worker/hour/stage replay`。单Reader内Job科学重放为4H、stage检查为4HM；对照实测12/60。目标调用量见[整链工作量后继](call_dag_and_work_units.json)：在原192h完整成功prefix及M=5条件下，源层597520次Job replay、2987600次stage replay；它们不是新Job/native求解次数。现toy max_events32仍在第11小时预留分支拒绝，未改预算、上限或执行路径。

优先候选是复用constructor首次inspect已返回的state/captured，避免caller随即再做一次完整遍历，同时保留双Reader以及views/inventory/prefix/source/implementation的后置观察。当前下游明确要求metric=2；必须用独立versioned schema、oracle和新validator，不能原地改变。逐类失效窗口与验收要求见[候选设计](constructor_inspection_successor_design_v1.md)。该设计尚未实现、未通过等价/故障验证，parent遍历减半只是条件计数。

第二Reader跨越registry/source/materialize窗口；paired前第二current跨越selector/transition/intent+ticket append；outcome后replay验证新持久化状态，这些freshness均保留。owner锁不锁N/source/registry，ReadView不证明外部静止；registry不同小时prefix不能按最大小时切片。完整动态闭包/未观察ABA、writer重建、persisted atomic-live、crash durability、真实phase terminal/reopen、typed followup right-censor、resource/native/formal均未关闭。

`profile_01`失败保留：setup在toy source安装后调用完整open_manifest，误入真实168h source audit并报错，尚未进入Reader；随后空pstats触发报告错误，外层terminal正确记录exit1。源码、request、stdout/stderr、error.txt、空pstats及monitor保留。后继按前驱保存profile的MANIFEST_PIN+私有_resolver编译冻结bytes，并修空profile保留原错；不声称重新验证真实manifest源。未扩大诊断规模或延长180s上限。

旧hour0/2h/3h和phase-body证据按绑定复用，没有重跑链主体。新的整链wall/RSS/storage仍为null，long_connected_launch_admitted=false；本包无seal、official verdict/receipt或运行授权。
