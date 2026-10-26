# C：Windows冷导入驱动修正与原账续验

2026-10-26，DRAFT_NONAUTHORITATIVE。root唯一writer，独立只读PRE_SEAL。生产ENTRY和tests保持v2同一Source49 epoch，复用实际accepted的41节点collection_final和pytest_a，不重跑集合/单测，不赋予旧cold驱动成功状态。

v2完整39文件／2,448,486B冻结：其cold_import exit1、accepted=false、missing9、无任何case子工件。stderr明确在第一个Popen的父驱动audit中，`list(args[1])==allowed[...]`断言失败；这是Windows命令行字符串表示与argv列表比较的错误，未启动三个case。source/helper/control前后pin相同，postcheck=false由missing9造成。所有失败与6.0413367s的首collection、5.7953702s的final collection、7.9834763s的41项pytest均原样保存。

新root为`results/tables/staged_rts24_saved_fresh_import_policy_cold_v1_non_authoritative`。仅修正驱动：Popen显式executable固定EXE；audit对executable精确相等、Windows `list2cmdline(expected_argv)`全串精确相等、规范cwd等于ROOT、env为None、三次顺序/数量逐项核对。child代码仍读取冻结v2 policy/admission_final；组件、policy、Source和41项测试均不变。三个case维持normal、after-import处caught effect、已有hook阻止安装；无OwnedChild/Job、native solver或科学API主动调用。内部科学调用未安装profiler，不能据此断言全部native副作用为零。

沿原账static93.5717783/120、pytest347.0348216/420，合计440.6065999/540。新cold≤12s、saved/terminal各≤6s，static最坏117.5717783≤120，总最坏464.6065999≤540；计费含本地准备/目标/后置pin及0.5s尾保留，不含编辑、独立审查、Git和Python最初启动。失败照计，不重置预算。

本根≤64文件/4MiB；v1原38文件、v2原39文件及本根三根合计仍≤128文件/8MiB，本根实际可用至多51文件且2,938,446B。原wire根≤204/16MiB保持。每次capture按最终产物数量及保守字节预留同时核单根与三根组合帽。新baseline引用已pin的v2 baseline原4576路径，并新增固定v2全39文件和v2 scope共40路径，合计4616前序路径，不复制/改写失败档案。

三个新helper的完整pin由新baseline固定，capture前后核Source49、helper、baseline、4616保全与累计记录链。saved/terminal只接受新cold exit所pin的9件真实case工件；保存oracle复用冻结stdlib AST/档案检查函数，独立验exact v1→v2 AST增量、历史失败、41项pytest和完整原账。新case的stdout/stderr、pid退出/kill等待、pipe/HANDLE关闭均保存。三导航前插原body并保存snapshot，外部论文/绘图改动继续保留。

结果仅为dependency-import policy原语的开发证据：固定lscpu拒绝并验证NumPy False、sentinel安装见证、sticky违规和失败关闭。33根transitive runtime闭包、cold-main/self-anchor、full683/G0/H3、真实角色bootstrap、issuer/permit、quiet/read和actual F仍未实现/未授权；原runtime v2继续UNDECIDED，v3 proposal继续admissible=false。所有运行、资源、科学和正式gate保持false。
