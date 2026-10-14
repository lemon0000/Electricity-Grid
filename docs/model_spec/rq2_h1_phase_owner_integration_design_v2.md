# H1 192h producer 接线实施边界

2026-10-09，DESIGN_ONLY_UNIMPLEMENTED。承接已固定的 design_v1 和 prepared-ticket
956 pins；本文件记录独立只读设计核查与根代码核对，尚未证明实际 producer 接线。
根代理唯一 writer，旧168h模块和结果保持原字节。

## 一次性 bootstrap0

新的入口先验证纯配置与外部 pins，在独立 bootstrap journal/lease 中留存 attempt，
随后才调用 source/network loader 和构造192h controller。现有 controller 接受外部传入的
network 和 expected_source_identity；新入口不能要求调用方预读当前行来满足这些参数。
静态校验、目录/lease创建与科学来源读取要分别计数；attempt 前不得调用科学来源 loader。

attempt 绑定固定192h任务声明、family/ordinal/obligation、源起点、solver与资源声明、
bootstrap root及genesis predecessor。必须先为成功及失败记录预留完整逻辑容量。
输入身份不能依赖尚未读取的当前 source row；静态输入 pins 与实际 source identity 分开记录。
N0接受后固定完整 controller/clock/parent terminal，再创建 TicketHolder/owner，绑定
genesis_terminal_sha256 并消费hour0。失败和提交未知分别保留；重开不自动再次执行bootstrap。
bootstrap 的来源访问例外仅适用于hour0，不扩展到hour1或followup。

## Owner 是 hour1+ 的唯一入口

run_next 持续持有 owner operation guard，按以下顺序执行：

1. 检查固定implementation、PID/thread、exact controller/holder实例、lease、外部双heads。
2. 重放DB与holder整链并核对prepared tail，拒绝pending/conflict/terminal。
3. 从重放所得业务与物理carry派生active/completed/halted_unresolved及need。
4. need=false时只追加episode terminal并返回；不得加载下一source或进入headroom/clock/Job。
5. need=true时先检查整条成功/失败分支容量，再持久化pre-N attempt。
6. 建立仅本次guard内可用的live capability，交给相互绑定的controller。
7. controller核实并消费capability后才执行headroom、内部加载来源、clock/parent intent和N。
8. 验证完整N terminal交叉引用，fresh current join，执行共同Rref、业务/A并paired commit。

capability至少绑定exact owner/controller实例、PID/thread、有效operation nonce、双heads、
attempt identity、hour/phase、parent及clock predecessor。不能通过任意callback、字符串、
Assessment或可构造类型获得权限；重复消费、退出guard后使用和绕过owner均拒绝。
controller API不接受调用方预先读取的source identity。锁序owner→controller→clock→parent；
验证回调不可重新获取已持有的owner锁。

根核对 h1_bounded_file_parent_development_v1._restore：来源读取由既有intent驱动，
ready prefix只重读0..h-1；pending prefix可能包含h，必须先识别并拒绝继续。
历史回放读取已揭示行合法；不能将其误写成“整个操作零来源读取”。验收区分已揭示历史行和下一行。
phase_binding.bind会进行168h enrollment预校验和当前行join，只能用于need/attempt之后的审计。

## 新schema与192h读写端共同实现

新holder/owner事件白名单统一加入attempt及episode_terminal，恢复、DB检查、append前检查和
重放状态机必须一致。只有paired outcome改变outcome head；其余只改变registry head。
prepared exact-before阻止任何重做；exact-after仅采用那一个已提交event。失败/未知不清理现场。
每小时attempt+science intent+outcome为3events，192h至少576加terminal及显式witness预算。
在调用N之前同时检查owner和holder的整分支事件数、单record与总logical bytes；
SQLite/NTFS分配、scratch、内存与全程时间另作资源准入，不能从logical bytes推导已满足。

新的phase controller直接组合通用bridge/SourceParent，不放宽旧obligation controller常量。
历史reader使用新schema，inventory为0..191，完成条件取声明192h；按phase重建binding，
保留同family/ordinal/obligation和source origin。新exact-source/current路径组合新reader；
旧公共接口的<=168限制保持。旧root不能改成192h，新旧reader必须拒绝互相冒充。
全168h enrollment义务预检保持；缺followup行只在need确定后按类型处理，不删义务或补未来结局。
completed/halted lane冻结business与A，actual records必须为空；active lane clock等于outer clock。

## 必须运行的验收反例

- bootstrap attempt前source/network/controller构造计数0；失败重开拒绝重做。
- h=168无primary need：下一行读取、headroom、clock/Job目录创建、producer计数全0。
- h=168仍pending：attempt持久确认先于下一行读取；来源失败保留pending且禁止重试。
- stale heads、prepared-before、conflict、terminal、错误phase在下一行访问前拒绝。
- forged、重复、已失效capability及controller公共step绕过owner均拒绝。
- mixed lane完成后carry不变、actual records空；primary失败不掩盖其他pending cohort。
- 历史reader在167/168/191边界仅重放对应已揭示prefix；非法suffix拒绝。
- 新旧root双向拒绝；956 pins及旧168回归保持。

独立设计核查记录：results/tables/rq2_h1_phase_owner_integration_v2_non_authoritative/design_review_01.json。
本轮未运行测试或native。后继实现仍需独立PRE_SEAL审查；此设计不是实现审查闭合。
完整192h producer、真实raw ingress/Job/计时、所有任务家族与合法reuse DAG、同合同LB/UB、
完整资源准入、successor seal、全新official review及具体新native授权均未完成。
resource_admission、formal_execution_ready、formal_result保持false。
