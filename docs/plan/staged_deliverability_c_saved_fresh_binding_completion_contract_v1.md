# C：冻结 saved 绑定源码剩余单位检查合同

2026-10-25，DRAFT_NONAUTHORITATIVE。起始HEAD `d985f709f457022b22193c3a25839c34fe0037e0`，接续[绑定交接](continuation_handoff_20261025_saved_fresh_binding.md)。root唯一writer，保留全部旧工件。此前批次238.315s不追加测试；本批次是对同一冻结源码尚未终态覆盖的49个节点的独立有限验证，不重跑此前最终28个节点，不启动真实saved F。

固定ENTRY SHA `cc384f65942c02bda20c8829cc667f762a90c922d1912c79d6e1d46f955df396`、tests SHA `16a0d2c0453113a09a0726da94bef65bce64205ad1ee5801d63a76b73c7a2f0a`、科学adapter SHA `26b919e385f9d7042587db490dab694fc5bf1643665ab4bf94a1c9bac8087396`。逐组SF49首尾及三源snapshot匹配后，才允许将旧28与本批49视为这一个冻结source epoch的77个唯一单位节点；不升级为真实进程、owner或科学采用证据。若随后修改源码，77仅属于该冻结epoch。

预算100s：pytest实际累计≤80s，collection/静态/保存核验≤20s。预先固定互斥3组：fast22/cap20s、late16/cap25s、bootstrap11/cap25s。每组启动前其完整cap须落在剩余80s内；无actor自动重试，失败或timeout保留原日志/源码，不加帽。使用compute Python及`-B`，只用原单位夹具和已禁用的CLI检查。

夹具继续显式模拟main/flags/preimports、实际不存在的OUTPUT父目录identity、tree和native endpoint。只读P1/SF49 capture，不创建实际OUTPUT或其父目录，不进行B/C/E重放、构造真实saved owner、fresh、solver、seal或formal run。原P1、scope-budget、科学adapter、guard/outer及SF49/17 targets/四记录帽保持。

结果保存在独立`results/tables/staged_rts24_saved_fresh_binding_completion_v1_non_authoritative/checks_01`，每次含source snapshot、raw stdout/stderr、source书挡、节点和终态。后续constructor/watcher开发使用另一个事前固定范围/预算，不能把本批通过数计为后续源码运行通过。局部saved verified、F_launch_admitted和整包science/resource/formal/public P2继续false。
