# C：生产runtime绑定与successor角色合同交接

2026-10-25，DRAFT_NONAUTHORITATIVE，接续[source复用交接](continuation_handoff_20261025_saved_fresh_source_bytes_reuse.md)，起始HEAD `860864eb8a6ae3926dda6b70781b9dac3aa4e058`；最终hash以远端读回为准。[本轮合同](staged_deliverability_c_saved_fresh_runtime_binding_scope_budget_v1.md)固定90s静态/受控反例预算，root唯一writer、独立只读PRE_SEAL。canonical ENTRY/tests/scientific src/SF49不改；epoch仍`84b6dafc7793caa2799ec99d3a38a5dfe3f3275448e3d30d3f2f01755a79e419`，原63节点仍匹配，没有新增pytest或科学操作。

实际产物：全49路径、41 Python/37 production candidate、1844 code对象、429 imports、33显式根的v2候选inventory；不是可达图或runtime闭包。初版跨unit id缓存导致946 fingerprint差异，原版保留，只用v2。五项受控RAM替换被当前10-direct preparation binding接受，替代对象未执行并恢复，不能称生产旁路。

先前witness05在case前因NumPy testing尝试lscpu被audit拒绝。补充witness06只对固定库pin/stack/phase/参数的唯一Popen抛专用OSError，仍阻断创建，走库False fallback；记录attempt1/blocked1和forced_SVE_false=true。声明audit P1 open=0及指定API=0不证明任意native读取/副作用为零。audit hook仅惰化、留至进程退出；其他插桩原对象恢复。生产外部probe政策仍UNDECIDED_BLOCKING，不能把诊断fallback直接用于actual F。

当前31字段spec v3已逐项固定type/约束/provenance、nested exact E匹配、大小及固定profile路径/SHA；20字段request不含未来ACK/context，五个数据摘要有精确canonical对象等式，两个profile SHA等于固定artifact pin（request/context一致）。v1/v2不完整proposal保留。38节点成功协议DAG包括host broker arming/ready/START和broker_ACK_verified→controller_permit→真实controller owner；controller issuer显式强持G0，parent/fresh真实owner构造及到quiet的同进程能力也显式保存。parent issuer持parent独立hold，不传G0对象；fresh无issuer，H3独立。context首次唯一create-only即successor，保留expectation/full=false，不能G0后换文件或加ACK造成循环。仍未实现生产validator/role接口。

详见[报告](../../results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/validation_report.md)。前序3390路径/P1全683/旧导航保全，actual F结果树及父目录不存在，无新模拟小时或solver/native-owner调用。

下一步实现完整successor静态validator与配套role bootstrap/store/owner接口，保持旧域拒绝；固定生产NumPy import-probe策略及whole-process预算，再推进33根传递绑定和ACK/G0能力。source6500、180s、失败成本/wire最大值、H3外部硬停止及实际F授权仍OPEN；科学采用、资源、正式及actual F门禁保持关闭，不重复已完成的十次source重读优化。

恢复先核Git/进程及保存oracle：`D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/saved_checks.py`。不得以当前census/反例/spec打开生产权限。
