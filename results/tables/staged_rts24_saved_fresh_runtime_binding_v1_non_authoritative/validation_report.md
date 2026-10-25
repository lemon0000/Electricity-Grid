# C：生产依赖与角色连接准入证据

2026-10-25，DRAFT_NONAUTHORITATIVE，起始HEAD `860864eb8a6ae3926dda6b70781b9dac3aa4e058`。范围见[合同](../../../docs/plan/staged_deliverability_c_saved_fresh_runtime_binding_scope_budget_v1.md)，接续[source复用报告](../staged_rts24_saved_fresh_source_bytes_reuse_v1_non_authoritative/validation_report.md)。root唯一writer、独立只读PRE_SEAL；canonical ENTRY/tests/scientific src及49-source集合全部不改。source epoch仍`84b6dafc7793caa2799ec99d3a38a5dfe3f3275448e3d30d3f2f01755a79e419`，63普通节点仍属于同一已验证epoch，本轮没有新增pytest、科学replay或模拟小时。

## 实际依赖清单

[census v2](checks_01/python_census_v2.json)覆盖49路径，其中41 Python文件、37生产candidate文件（src+ENTRY），递归1844 code对象、429 import sites、33显式根；当前preparation binding仅10个direct targets。所有metadata由冻结源码在固定EXE/version、原filename、dont_inherit=True/已记录optimize下compile和dis产生，未exec这些code，也没有仓库import。

这个inventory保守包含未使用/不可达code和local imports；它不是完整可达调用图、import target解析或运行时闭包。globals/module attribute、class/constructor、常量容器、builtins/第三方/native和动态dispatch仍须真实绑定。初版census_03 exit0但其跨unit id(code) memo可能复用已释放对象ID；限制为每compiled unit后，census_04同源码metadata/keys一致而code SHA有946项差异。初版JSON/helper/raw完整保留；只采用v2 fingerprints，启动终态不自证metadata正确。

## 五项受控RAM反例

首轮witness_05在五项之前终止：仓库导入经src.grid→PYPOWER→SciPy→NumPy testing触发check_support_sve的subprocess.run('lscpu')，Python audit在Popen事件拒绝（0.656s/12、exit1）。它不贡献任何反例数。失败原栈、script snapshot和source pins保留。

补充witness_06已事前登记一次≤12s，实际5.047s、exit0。在repository_import阶段，仅参数(None,'lscpu',None,None)、固定NumPy源码check_support_sve/module调用与固定subprocess.py审计点全部匹配时，继续阻断创建，但抛专用OSError走库原False回退；第二次或其他进程调用一律拒绝。NumPy/subprocess/compute EXE的实际pin和原字节snapshot已保存。生产import策略仍UNDECIDED_BLOCKING；这项插桩不变成生产政策。

| 替换symbol | 当前preparation guard | 替代对象调用 | 恢复 |
| --- | --- | ---: | --- |
| codec.parse | 接受 | 0 | 原对象及globals字典身份保持 |
| adapter._replay | 接受 | 0 | 原对象及globals字典身份保持 |
| core.digest | 接受 | 0 | 原对象及globals字典身份保持 |
| adapter.HeldInput | 接受 | 0 | 原对象及globals字典身份保持 |
| adapter.METRIC_FIELDS | 接受 | 0 | 原对象及globals字典身份保持 |

这五项均按预注册预期建立：[raw结果](checks_01/global_binding_witness_v2.json)。它们只证明当前10-direct preparation binding未覆盖这些symbol，不是生产旁路或科学结果改变。baseline+五case仅调用6次_expectation_adapter，未创建科学input capability/issuer/owner。

整个仓库import前已安装audit/open/process及声明API观察，import完成前通过hook阻断solver factory，随后安装具体科学操作拒绝器。分phase计数为：声明Python audit P1 open-attempt=0；Popen attempt=1、blocked fallback=1；声明科学/solver/native-owner API与替代对象调用=0。不能把它扩成任意native文件读取/进程创建或所有副作用均为零。numpy_sve_support_forced_false_by_instrumentation=true，结论限于该受控状态。replacement/import/profile原对象恢复；audit hook不可移除，finally惰化，仍留至短进程退出。保存层baseline/最终oracle另会读P1全683验证保全，不属于上述witness窗口。

## 可实现的successor数据合同

初版31字段清单/28节点DAG仅为proposal，漏了broker本地ACK/owner链并缺类型细则；v2仍缺request摘要等式、parent/fresh真实owner及controller issuer。原文件/helper全部保留，前两版不作为完整性依据。当前[spec v3](checks_01/successor_context_spec_v3.json)为31字段逐项type/constraint/provenance及cross-field关系合同；原expectation的27字段与source AST精确匹配，新增仅4个。它不是已实现的JSON Schema/生产validator，也没有生成context实例。

canonical ASCII raw≤2MiB，拒绝duplicate/nonfinite，depth≤256/nodes≤1000000；Pin、49-source/683-input、executable、environment、原stage/limits均有固定规则。caller core exact15键/库存exact3键，所有嵌套子树必须逐字等于host独立持有的E；不会把incoming context自算hash当独立期望，更不把E/full=false升级为全内容验证。broker_identity的pid/creation_filetime exact有界正整数必须由真实owner/ready/START及controller bootstrap kernel核验支撑。

| 字段合同 | 固定artifact路径 | exact raw SHA256 |
| --- | --- | --- |
| runtime_binding_contract | results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/runtime_binding_contract_v2.json | 767b0119ee6de14f720099897eafb158803433b4291529a786a4e3e281ed148d |
| deadline_contract | results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/deadline_contract_v2.json | ecffb262d87b6595e4d66451768ada7780c73e6e2ea0fc0e5b88834aadb32343 |
| request_contract | results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/request_contract_v2.json | fbb536393e7246487f3b91af0b691da317f1dbb238f5fdd40f770c286ce3dc1e |

request canonical域由20字段合同固定，≤32KiB，在H0后/arming前由host独立构造，start在H0前确定；不含未来context/ACK。五个数据摘要逐项等于host独立source/env/input/caller core/envelope的精确SHA，两个profile字段在request/context中均逐项等于固定artifact pin SHA；外层request_sha不能替代这些关系。runtime profile明确当前不能用于production；deadline profile保留原earlier offsets，actual enforcement仍false。

[38节点DAG](checks_01/capability_edges_v3.json)从host expectation/request、broker owner arming/ready/START开始。host ACK只是跨进程数据，broker须本地ACK_verified→controller_permit→真实controller_owner_constructed，才到controller bootstrap。controller侧G0→controller_issuer→parent_permit→parent_owner_constructed，parent侧parent_hold→parent_issuer→fresh_permit→fresh_owner_constructed，真实owner分别强持至对应quiet；permit/packet不能代替owner。controller issuer强持本地G0，parent issuer强持parent独立hold；跨进程只能传绑定数据，fresh无issuer，H3为host独立hold。设计oracle确认无环，并拒绝ACK→context反向边和跨进程G0能力。该成功协议DAG不代替所有import/失败/清理/资源调用图。

实际saved broker首次且唯一create-only context.json必须使用完整successor，保留caller_expectation_core/sha与full=false；G0后不换文件、不改full标志。ACK/context SHA、G0和permit由外部协议/同进程能力绑定。新schema不能穿入旧RoleStore/SavedOwnerInputs/bootstrap/ordinary入口；下一实现需成套successor validators/store/owner/driver，而非改mode、别名或global issuer。

## 保存、预算与剩余工作

前序3390路径、P1全683与导航旧正文逐字保全；当前source49完全匹配原63-node epoch。检查预算90s，包装前已记录16.422s，所有失败及初版均计入；包装/最终checker另由外部终态exit计时。本轮结果目录≤8MiB/128文件。自包含stdlib保存oracle不导入当前ENTRY；前序oracle在逐字核其原文件后调用，保留其frozen/current分离及无ENTRY执行边界。

下一实现先按31字段完整数据合同添加successor静态validator和角色专用bootstrap/store接口，保持旧域拒绝；同时把本轮发现的NumPy import probe明确纳入生产import策略与whole-process预算。随后实现33科学/角色根的真实传递绑定与ACK/G0同对象连接，不能以五反例或38节点设计oracle代替。生产global闭包、G0/H3、issuer/driver、source6500、失败成本、180s逐边硬停止、最大合法wire及host外部I/O仍OPEN。实际F、F局部verified、科学采用、资源及正式门禁均false；没有production manifest/lease、official verdict/receipt/seal或run authority。

保存核验：`D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/saved_checks.py`。见[交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_runtime_binding.md)。
