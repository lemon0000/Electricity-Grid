# stack诊断：统一watchdog启动条件的有限后继

2026-10-27，DRAFT_NONAUTHORITATIVE。原stack后继startup通过，但import case在SELF阶段以conditional TCB profile mismatch拒绝，source_open=0，self资源未构造，DLL cookie关闭，父process/pipe终态。该case在1秒采样前结束，无stack；原报告与费用保留。它是新增诊断条件不一致，不能称为原import超时的根因。累计意外不接受记录20。

新core v10、probe/parent v7及独立runtime_stk root，BS3/namespace2/Source49不改。两种case都import faulthandler并在相同入口启动一次1秒watchdog（repeat=False），finally取消；discovery通常先完成。重新独立发现/核准画像。若startup已产生stack，discovery parent可保留诊断stderr并核原profile报告，不能删除原raw；不把native watchdog当作已认证线程闭包。

最多2个新cold child，并发1，adapter import最多1；static/总≤8s，登记≤1s、startup≤2s、admission≤1s、stack≤3s、保存≤1s。原stack12秒/2child帽及所有原结果冻结，本scope独立，不称旧帽增加或组合通过。任一失败保留并停止。新root results/tables/staged_rts24_saved_fresh_runtime_stk_v1_non_authoritative ≤16文件/4MiB，command30000UTF16、stdout131072/stderr32768、payload131072维持。

stack child允许预期timeout并保存一次真实栈，source/self-close缺失仍未知；不授予成功runtime、B_S、F、科学、资源或正式结论。旧27/27与三finding闭合只支持对应开发行为。前驱guard/trace/stack费用与20条不接受记录全部累计。Native仅原self query/cleanup及watchdog；无模型/Highs/solver/P1/hold/capture/replay/OwnedChild/Job/F。全部formal/run/role/permit/science/resource gates保持false。
