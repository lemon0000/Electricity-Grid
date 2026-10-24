# 原始点证据到 trusted journal 的保存 P1 连接

2026-10-24，DRAFT_NONAUTHORITATIVE。起始HEAD/origin为`9c872d000d0f9bbd066e462786376acb6748a54b`，工作区干净；此前四个F/X代表行检查点已发布。本轮按[合同](../../../docs/plan/staged_deliverability_c_saved_journal_check_contract_v1.md)实现[DAG](../../../docs/plan/staged_deliverability_c_scientific_adoption_dag_v1.md)局部E的普通只读集成检查，原src及输入没有修改。

原P1为683文件/2,950,863B；journal为137文件/427,629B，含五个hour、一个terminal和130个CAS对象。外部固定postcheck SHA与完整pins先绑定launcher/start/trusted_binding/prefix0..5。原B独立政策与原C重建五模拟小时/21点，再由原journal_v2.reopen按genesis/head/state/CAS/failure重开；21个重开PointEvidence的typed根和query SHA逐一匹配原C输出，最终state digest和typed CAS根均相同。后者为`29517379c102b40b0f0a0b77711db4d936357025e4f53283f5bdec04fcbc7a41`。

保存终态仍是missing_input/committed/known：五个accepted小时、最后hour2、六entries、130对象，余额0，coveragefalse、两条件null、resume=false，无pending/unaccepted attempt/failure/未引用CAS。尚未观察的后续小时未补齐。完整P1库存/metadata/root、45选定source、外部锚原字节/identity/祖先、完整pins map和fixture/source/caller冻结image首尾保持。

16个定向检查（1条真实保存连接、九字段trusted错误、六个caller书挡反例）和24个原journal相关回归通过，共40唯一nodeid。相关回归覆盖retention、pending/unknown、unaccepted、实际拒绝及终态失败；其writer只作用于自己的pytest tmp解析fixture，真实保存连接禁止writer/put/publish/Popen/Highs或backend调用。独立PRE_SEAL问题已修复，最终记录见checks_01；没有official verdict/receipt/seal。

实测逻辑调用：构模42/snapshot21/import21；B与E的prepare/propose各10，共各20；execution audit33/历史row85；typed pack155=B105+E27+join23，E包含14显式pack与13次get规范化重编码。选定source/runtime内容读2080；P1内容读4319，其中整包库存1366、B单点2152、E journal801；外部锚末次另读1。原parent/KKT审计保留，不把源码/目录/metadata/编码或这些逻辑读数当完整OS资源测量。

chain_04 wrapper wall约29.20s（test call26.66s），bindings_02约32.51s；相关两组约45.06/32.21s，均在各90s硬帽内。原related_01接近90s的成功日志保留，最终按24个原nodeid顺序固定分两组互斥12项，不增加超时。首轮chain_01因漏计13次规范化pack失败，后续修复前通过记录亦保留，最终共同pins只采用chain_04/bindings_02/related_02a/b。这些是普通测试wall，RAM峰值、全outer成本和十小时增长仍未知。

836旧发布路径、三导航旧正文、前轮stdout和原P1全部683文件保持；原P2七输入/packet、B1–B3、guard/outer、原B/C/D/journal/numeric/codec均不变。三份原始stdout中的pytest尾空格或EOF空行按字节保留，[格式例外清单](checks_01/raw_log_whitespace_exceptions.json)固定其pins；Git空白检查只排除这三份捕获，其余源、文档和工件严格检查。局部saved_P1_journal_reopened=true，全P2 journal_replayed、scientific_evidence_adopted、完整139/F-X、resource/formal仍false。无新native、公共P2或长实验。

后续F仍需同输入fresh与最终父采用/失败发布的有界DAG及预算，不能把历史fresh.json或本轮同进程重开当新fresh验证。完整319、昂贵失败/十小时/full wall/RAM/storage、65s父端余量、C整体与D/E现实输入/方案选择/敏感性/冻结后留出仍OPEN。见[交接](../../../docs/plan/continuation_handoff_20261024_saved_journal_check.md)。
