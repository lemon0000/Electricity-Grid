# 剩余 namespace case 的有界诊断

原 suite_01 的 240s 是 2s 采样 watchdog 阈值；在 suite=241.344s 检出，第 9 项 case=34.782s，含清理外层为241.812s。8项 accepted，第9项无 worker terminal，namespace 注入、Reader finally、hooks/guard恢复均未证明。FileNotFoundError是停止后读不到worker terminal的次生归档错误。原attempt完整保留。

先验把无instrumentation的H3成本用于5个完成prefix-hours，低估了9次冷进程及trace/profile诊断开销。真实H1后期故障case6/7外层47.093/44.891s，H2 case8为81.843s。本次只登记尚未验证的一个H1 case，不重跑前8项；新attempt保持原单例90s限，总额也固定90s。任何超限均停止，无自动重试或续时。

继续使用 exact v1 worker。其独立profile观察cleanup是必要的：trace callback直接raise时CPython会停用trace，故不能简单合并二者并声称前8项等价。第9项仅在第三轮namespace的第一个root安装_names返回值seam，原_inventory拒绝额外名称；不改变磁盘内容。原expected counts=2 saved Job inspections/10 M5 stages/1正常_after return。前8项结果只按其原tested bytes及terminal SHA复用。

路径为旧2483绑定+原suite2492 pins+所有原attempt/support04工件fresh核验 → 原support04 16项/6份稳定源快照复用 → 只变plan路径/终态scope的runner机械successor及AST核对 → 一个fresh worker读原465文件 → 目标故障、真实cleanup、恢复、case SHA → 外层退出/清理。无新normal Job、selector或native solver。sample=2s，heartbeat=30s，无case-read activity60s，RSS768MiB，输出logical64MiB，只允许直接conhost。停止线检测及清理允许采样/清理尾部，不能宣称绝对wall硬上界。

两attempt合计最多10次Reader调用、6个完成numeric prefix-hours/12个Job inspections/60个M5 stages的先验上限；原被终止case的实际调用数未知。组合accepted cases若齐全，仅观察到其中5个完成prefix-hours/10Job/50stage，不能据此补写被终止case计数，也不能改写suite_01为9/9。

维持全部scientific/resource/formal gates。此有限保存M5故障矩阵不证明真实M232适用性、完整输入闭包、ABA、owner adoption、H168/F≤24连接或正式实验预算。
