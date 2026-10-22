# 单次操作内业务record重放复用

2026-10-20，DRAFT_NONAUTHORITATIVE。R3，唯一writer为主代理，独立只读PRE_SEAL审查。原168h/≤24h、科学代码、配置、保存chain和失败原件不改。本后继先作为detached验证工具开发；没有正式运行或长连接准入。

目标：原business._validate在每个旧record调用BidirectionalPolicyRecord.__post_init__，重复确定性数值重放。新后继只将这一处调用路由到操作私有record校验；AST中其余validator完全相同，原cursor链、完整history、current/observation、时钟和implementation检查每次照常执行。

命中限同一个record对象，缓存保留强引用防id重用；每次重新生成完整typed实例字段图：精确class对象、所有canonical __dict__字段和顺序、容器/scalar类型、IEEE float bytes、Fraction numerator/denominator、共享alias关系。未知类型、额外字段、slot或循环布局走原表达式uncached，不缩小原validator接受域。首次仍按record.__post_init__原lookup执行，前后图完全相同且依赖复核成功才存缓存。不同但结构相等的新record对象必须重新验算；不保存可写物理状态快照。

缓存只在同一pid/thread同步operation生存，cap1024records/64MiB raw-key bytes，单record1MiB/65536nodes；dict/tuple/strong-reference等额外开销由整体RSS监视约束，64MiB不是总RAM上限。失败poison并清空，close清空并区分closed_cleanly，禁止复制/序列化。无source/current/registry/外部heads缓存或跨operation复用。依赖捕获复用原runtime-closure v2，并显式登记纯业务module/class字典key inventory、bases/MRO、descriptor、函数code/default/closure、builtin shadow、dataclass metadata及_ARM_TRACKS嵌套set常量；每次record hit/miss前后复核runtime，每次public validate及整operation入口/出口核文件SHA。派生函数使用原globals，callback为新增local参数，不留下可写cloned-namespace绕过。仍不提供任意Python reflection隔离或未观察ABA证明，complete_dynamic_closure_proved=false，不能据此接入production或减少外部source freshness检查。

完整路径：已有真实业务carry或保存record → 原validator对照 → 新operation进入/依赖与文件观察 → 原完整cursor/history对应检查 → fresh typed record graph → 原数值重放或本operation命中 → 原末时钟检查 → 退出fresh依赖/file bookend及清空 → 科学payload/hash/拒绝和资源报告。后续若进入owner，必须保留完整N/source、Rref/Actual、durable append、失败/收尾、外部checkpoint与close/reopen，单工具结果不能替代整链预算。

先做短单元：完整相等record重复、内层字段/类型/历史/record响应篡改、代码/默认值/alias/metadata漂移、cap、creator和关闭拒绝；本包列明的业务合法输入和五类业务非法输入以原函数作oracle，依赖漂移与资源门单独核拒绝及清空，不声称穷举整个Python输入域。close成功后的closed_cleanly记录该次close的历史状态；关闭后再误用可以另标poisoned。固定单次测试包180s、RSS1GiB、logical128MiB，0 Job/native；原件与source pins保存，超限停止owned子进程，不顺延。测试通过后另固定有界profile规模/次数和全wall/RSS/storage，比较原/后继整个validator路径，而非只报缓存命中率。

工作量预期只减少重复record数值求值；fresh图、cursor/history对应和identity编码仍可能呈二次/三次增长。本后继没有预先宣称消除全链多项式瓶颈，实际总收益、source主导成本与生产开销待测。若fresh图/依赖检查抵消收益，保留失败诊断并调整优化点，不以弱化key或科学门取得提速。
