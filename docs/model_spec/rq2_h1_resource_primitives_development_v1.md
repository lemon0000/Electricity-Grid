# H1 资源原语开发记录

状态：DRAFT_NONAUTHORITATIVE。本批次位于新增 experiments/tests 路径，未接入 v3 runner，未建立执行包或任何运行权限。既有科学阈值、raw serializer、冻结源码和结果保持。

## 分段计时原语

`experiments/h1_segment_timing_development_v1.py` 提供单进程、单线程、单独时钟域的内存 Ledger 和独立序列化 reader。request SHA、PID、thread、clock domain 绑定整份记录；每个 span 保存 stage、phase、parent、start/end ns、open/complete/unknown 状态。

同一 stage/phase 只允许一次；需要多次 build/audit 的完整 worker 以后必须显式定义 occurrence 身份及其上限，当前接口不能直接套用。stage=-1 为生命周期，0..231 为单小时槽位。嵌套时间按父跨度扣除直接子跨度，再归入各 phase；未覆盖时间另列。字段名 recorded_window_wall_ns 仅指 Ledger 开始至 finish 最后 tick，不是整个 worker/Job wall。

异常、时钟回退、错误调用会 poison；未闭合 span 保持 unknown，分项合计返回 null。reader 拒绝错误 schema、重复 stage/phase、错误父关系、兄弟重叠、越界和状态不一致。进程或线程变化禁止继续使用该 Ledger；不同 clock domain 不相减。

Ledger 是内存对象，不是 crash-durable journal。进程被杀时没有 snapshot 只能记 unknown；当前尚未实现 durable span-start 协议。序列化 snapshot 最多2MiB，exclusive create、flush/fsync、精确 readback；短写或任何失败保留已有文件，不重试覆盖。

记录窗口内的 bookkeeping 仍包含在相应 span 或余量中。finish 后的 snapshot 构造不在该窗口；write_snapshot 单独计量 analyse、encode、write、fsync、readback 和 digest，并返回绑定文件 SHA 的独立 observer interval。该 receipt 的构造、返回、后续持久化仍在 observer interval 外。因此 observer_overhead_separated、instrumentation_coverage_verified、component_budget_verified 均为 false，不能由本原语证明旧2440s分项限额。

验收覆盖：嵌套exclusive时间和余量的独立算例；异常/null；clock回退/错误类型；duplicate stage；未闭合finish；跨PID/thread；非LIFO；独立reader畸形输入；snapshot复制隔离；exclusive写入；短写/fsync/readback失败；byte cap；外部observer时钟回退和status一致性。

首轮只读开发审查指出缺少逐span status、最终记录I/O位于已报告wall之外，两项均按上述显式状态与窗口边界修复。完整worker的instrumentation接入、重复phase身份、持久化失败窗口以及controller/worker协调仍待开发。

## 条件 JSON 字节界

`experiments/h1_report_byte_bound_development_v1.py` 实现 exact object-key grammar、逐字段校验、compact sorted JSON 等值检查以及可复算的组合上界。这是已产 raw 的只读开发验证器，不在 collector 接受路径上；grammar 不匹配不改变原始 witness、科学判决或任何归档。

条件为：assignment/referenced_assignment 各最多891项；constraints最多1211；canonical/native objective terms及各自algebra各最多362项；变量名完整JSON token（包括引号及escape）最多38字节。有限binary64的规范hex内容最多24字符；数值JSON token最多24字节且逐值验证；状态token有长度/字符集限制；solver options精确固定；其余整数、SHA、布尔、nullable和无解分支均有限且拒绝额外key。原有certification/formal flags严格保持false。

Fraction界以整数算术推导，避免log舍入：有限binary64绝对值小于2^1024且分母整除2^1074；乘积的分母整除2^2148。T项系数聚合分子绝对值小于T·2^2098，T项乘积加常数分子绝对值小于(T+1)·2^4196；减去一个lower用T+2。将这些整数界转十进制位数，再加符号、斜杠及分母位数。T=362时aggregate Fraction最多961字符，objective numerator1267、denominator647，exact-minus-lower1915，两个float差958；单float也保守使用958。此界允许同名项聚合，不依赖无重复的观测。

对上述完整grammar，serializer组合上界为 **929218 bytes**，小于1MiB。独立极值语法对象几乎达到该界，并非科研witness。v3封存DB SHA256=bc9ff4270ec834347f440444fdbf0d0d328705b4d4a6c4c7aad8114e8fcd2115；只读拼接232原始raw并逐项核对payload hash/length，全部通过grammar和精确re-encode，实测最大177312 bytes。

**producer_coverage_proven=false。** 362项和38字节是明确前提，尚未对所有未来来源/carry/model构造证明。仅将term上限设为891时组合界超过1MiB；变量数本身甚至不自动限制带重复项的native expression长度。后231个单变量目标及operating_cost固定成本模板仍需解析模型证明、输入inventory和solver导出证明。实测报告不替代这些证明；不把929218升级为新的writer cap或完整资源准入。

异常字符串、collector抛错和被杀进程不属于成功返回report grammar；其单独失败通道及资源预算仍待。旧solve_once在encode后cap检查，直接降低cap会丢失尚未返回的raw，因此保持旧16MiB采集合同。本轮没有实施两通道quota、fail-stop collector、重试或新native运行。
