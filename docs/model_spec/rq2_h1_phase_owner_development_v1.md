# Phase owner FSM draft

2026-10-09，DRAFT_NONAUTHORITATIVE，尚未闭合。根唯一writer。
目标为design_v2的192h owner/controller接线；本文件记录当前实现边界，不能替代完整目标。

owner使用新的phase TicketHolder，重放全部DB和holder tickets。head计算保持只有paired outcome
推进outcome head；attempt、intent、witness、episode_terminal只推进registry head。
prepared exact-before自动进入recovery_required；exact-after只采用已提交的同一个event。
same PID/thread、固定原lease与holder实例、配置/文件身份及外部双heads检查维持独占状态。

当前genesis仍消费已经固定的accepted N0 terminal：advance仅允许hour0、exact genesis terminal。
这一消费接口不实现bootstrap producer；bootstrap的一次性attempt必须在后继入口另行接线，
不能把owner中的科学intent冒充N0运行前日志。

hour1+调用prepare_next：在owner operation guard内重放、由内部business carry派生need。
need=true则在DB和holder同时检查整个成功/失败分支的logical event/body容量后写attempt；
need=false则写episode_terminal，不加载下一source。一次成功分支保留attempt+intent+outcome
以及一个最终terminal的空间；bootstrap分支保留intent+outcome+terminal。
分支均使用manifest.max_event_bytes作单event保守上界，实际append还会重验真实字节大小。
检查不证明文件系统空间、时间、内存或完整任务资源准入。

attempt绑定phase/hour、双heads、state、重算assessment、固定source binding、上一正常小时terminal
和分支caps。live_controller_attached=false：还没有exact controller predecessor/operation nonce
和一次性capability，不能把prepare_next返回值用于生产授权。

complete_saved消费后继N terminal及Rref/A saved records，只允许已有attempt；来源与数值重放后
写science intent及paired outcome。来源读取/数值异常保留attempt或science intent并poison handle。
重开不会执行N；prepare_next拒绝pending attempt，witness不能插入pending attempt中。
该方法是人工提供既有证据的开发接口，后继live run_next不能在guard之外调用任意producer回调。

lane由业务/实际共同成功提交推进；业务或actual未决冻结原两份carry并转halted_unresolved。
每次成功paired commit重算followup need，已完成lane转completed并冻结；后续actual records必须空。
episode_terminal由内部roster评估决定，terminal后拒绝任何suffix或witness。
一个primary cohort失败不自动终止其他pending cohort，继续沿用已固定的followup assessment。

当前明确缺口：

- 来源适配器已接到phase historical/exact-source，公共进度最多192h；header记录
  `phase192_historical_saved_prefix`。只接受新phase controller格式的既有历史证据。
- controller实际前驱绑定、mutual live attachment、一次性capability未接线。
- bootstrap producer的先attempt后source入口未实现。
- 已确定N失败的terminal与提交未知的区分、来源缺失的typed右删失terminal仍待接线。
- 初始测试仅覆盖synthetic source seam下已有真实selector/business replay、attempt顺序和恢复窗口；
  不覆盖真实192h N prefix、h=168 completed/mixed roster或全程运行预算。

这些缺口使本单元保持DRAFT，不生成开发闭合或official门禁证据。
resource_admission、formal_execution_ready、formal_result均false。真实native/Job不在本轮范围。

## 第一轮审查修复

tail replay后重新检查DB rows、holder tail和live binding再返回；create必须是exact bool。
witness从fresh roster判断完整容量：仍需后续小时保留2个witness events加4个后续分支events，
已停止则保留2个witness events加1个terminal。两侧均用同一branch，检查期间DB变化拒绝。
测试增加prepared terminal exact-before/after、重入tail变化、错类型create、witness分支容量，
以及显式progress/assessment seam下的边界检查；最后一项不是实际168h来源证据。

## Phase source 接线

phase source 的两小时合成Job重放与40项独立零Job检查完成后，本草稿切换到新版适配器。
owner测试显式替换新版source API作为synthetic seam，保留实际business/selector重放。
168/191小时允许构造followup attempt，192小时拒绝；边界测试不持久化人为跳过的carry。
这个接线不证明完整192小时prefix，也不赋予prepare_next或私有controller入口执行权限。
