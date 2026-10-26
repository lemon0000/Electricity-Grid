# C：successor wire／startup／projection 合同交接

2026-10-26，DRAFT_NONAUTHORITATIVE。起始 HEAD/origin `147fa6162be10976eb16336ae71740e143f8d594`；接续[三角色数据入口交接](continuation_handoff_20261025_saved_fresh_role_data.md)，以[本轮范围预算](staged_deliverability_c_saved_fresh_wire_scope_budget_v1.md)为准。root唯一writer，既有独立只读PRE_SEAL，无official review/receipt/seal或运行权限。宽goal保持active。

本轮固定45个新逻辑域、94节点扩展DAG、完整编码容量和结构化cross-field约束：9个mailbox域，三角色各9域，7额外local projection及host/broker failure。它们是生产接口的设计合同，validator/emitter/bootstrap仍implemented=false。Source49、ENTRY/tests/科学adapter和全部前序4290路径不改；4290显式包含前序4123、role-data root165和两份前序新文档。

三个entry transport新增有界projection bundle slot，将broker ACK及controller/parent的完整原projection按1/4/4传递。header/projection/binding/packet全部commit后才构造owner；bundle raw→冻结packet projection-SHA字段逐项绑定，双侧重哈希bundle/header不能跳过packet。stage保持独立header加16帧，即17×4096B；bootstrap占逻辑frame0，之后phase按原descriptor逐sequence映射，成功总帧数controller12/parent7/fresh3；terminal/error是吸收态。proof commit必须先于controller G0及parent/fresh hold。child不消费parent私有startup capture，也不认证独立producer。

return reference固定target/writer/kind/context/request/stage/episode/pin，包含comparison candidate；G3_image_sha在controller return中固定None，adoption/host消费权限等保持false。failure最多24摘要，最大canonical value上界24242B；角色stage仅传compact code，完整记录使用controller既有failure target、parent/fresh各自JSONL、broker return或host本地诊断。JSONL正常事件恒留32769B给完整failure+LF，文件帽仍64KiB。未知quiet不能读child工件。

必须区分两个设计epoch。原design_02结构检查为43 mutation+3合成hash关系，保留其原stdout/stderr/exit、三设计JSON snapshot和三helper原字节。后续PRE_SEAL发现proof/hold图边与逐phase吸收规则不足；draft_revision_03将原设计、baseline、旧新helper和原records绑定，再用原reserve_05 cap18核修订版。reserve_05已终态0/accepted=true，50 mutation+3合成hash关系通过，不继承旧43项为新缺口通过。两版均不构成runtime fault验证，36项runtime矩阵全部UNRUN。

一个wrapper曾在Python解析时退出，target未创建。原wrapper/scope和工具combined decoded输出保存，明确没有target分流raw；工具观测0.8421054s加0.5s reserve计1.3421054s。baseline_01/design_02/reserve_05均已终态成功，含该失败的saved前静态账为9.3848743s。余下saved/terminal各≤30，仍计原120s。四个原目标加reserve及wrapper失败最坏119.3421054s；Python初始启动、编辑/review/Git与实测capture范围分别说明，不宣称workflow wall/RSS/hard stop准入。

保存入口为 `D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_wire_contract_v1_non_authoritative/final_package_01/saved_checks.py`。恢复先核Git/进程、[报告](../../results/tables/staged_rts24_saved_fresh_wire_contract_v1_non_authoritative/validation_report.md)、checkpoint_status.json和reserve_05/saved_03/terminal_04原exit。oracle只读新设计/快照和pin绑定的前序stdlib archive，不import当前ENTRY/生成器；main freeze在修订design外部exit之后建立，本次capture由外部exit/checkpoint/Git承接。

旧480节点和P1全683只复用；本轮new executed pytest/cold probes/模拟小时均0。下一实现按45域补exact validators/emitters、完整transport prefix和startup join；旧21声明和三data-only API保持其原域。之后才连接真实issuer/retained owner/Job。生产NumPy probe政策、33根闭包、source6500/180s、完整workflow资源/停止及actual fresh/最终父端采用/科学采用/正式门禁仍OPEN，不能由设计计数开放。
