# 目标历史长度的业务validator与序列化成本

R3 / DRAFT_NONAUTHORITATIVE，root唯一writer。先补整链预算，再做真实168h/≤24h连接和episode终结；无新formal/native/长链权限。前轮constructor窗口修复最终core/final为207/208 bindings，final SHA925f9370ad00f72d8cb0a3af7abdca26dcb8eb168f346ba9ac24b763232fcb20，候选仍未adopt，16准备门全false。

证据先复用：phase unit_04的exact_due_192事实SHA482ef4cbb986dad4818ed4bc3e7d90ee9b7cee56cbe94df4d59f0ca58e3c6c0d，旧detached完整业务路径16.099025s/194次_validate/历史长度和18720；不重跑旧unit主体或其余8份事实。旧4/16/32h总validator对照和record-cache负结果继续复用，该cache不采用。旧192h是fixture参数，不当冻结v2 anchor测量；尚缺target长度单次validator及科学/full-carry编码成本和大小。

本诊断只建一个detached JOINT业务history，从genesis逐小时到192；使用冻结v2 anchor的f=.20、headroom=.10、eta=.85、event cap14、duration4、rest1、energy2.8、debtcap.20、response1及12位恢复。alpha=.50、D=.50为明确benchmark参数，非最优capacity结论。w=.50/source-CFE=.50，hour168仅grid birth=.017，直到hour192把source-CFE置0，允许r=.02精确偿还.017，due192先恢复后snapshot0。无source实际装载、Rref/Actual grid witness、paired commit、持久owner或phase terminal。

完整路径：核冻结protocol和继承/旧final pins→安装no_solver与显式source/Job拒绝fixture→原业务初始化→192次原prepare（构建单列、每8小时写进度）→h168/h192各一次原_validate（不优化、不装recordcache）→分别编码scientific payload和完整carry审计（时间/bytes/SHA分列，编码不当owner event上界）→验证科学payload前后相同/解析债务和due事实→保存fact/JUnit→outer核文件/进程终态。测量仅各一次，不提供时间分布或硬上界；实际参数/原代码pins固定。

固定1个pytest诊断case、1条192h业务历史、2次目标_validate及各2种编码，0新normal Job/native，无source/selector/DB/holder写。wall90s、无worker进度30s、sampled owned tree RSS512MiB、逻辑输出32MiB（含base和日志/snapshots），2s采样/30s心跳。依据为旧192h16.10s且本次只增两个末端测量；90s是硬诊断额度而非完成保证。超限仅停止PID/create-time匹配owned树，保留所有文件和独立after pins核验，不扩时或自动重试。业务hour progress仅证明detached构建活动，不证明科学整链进展。

7个旧constructor诊断及旧hour0/2h/3h保持原件；不编辑它们的代码/结果或保存case。正常生产232-stage、源层prefix二次重放、业务ready/post cubic量、576 operational events/旧cap32、完整档案/失败/scratch/reserve/RAM/wall仍需预算。目标组件观测不关闭整体性能/资源/正式门。
