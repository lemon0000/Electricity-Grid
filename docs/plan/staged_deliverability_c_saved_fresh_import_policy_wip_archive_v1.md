# import policy WIP归档范围

2026-10-26，DRAFT_NONAUTHORITATIVE。接续[冷导入WIP交接](continuation_handoff_20261026_saved_fresh_import_policy_cold_v1.md)。只做一次≤4.4s的stdlib归档检查，计入原static120与总540；开始前账为static115.5054887、pytest353.8217016，不包含Python最初启动/编辑/审查/Git。

检查原4616前序路径、当前42项pytest Source49和harness、v2→WIP仅loader立即commit及EOF新增回归的AST差异、8失败记录与02/03诊断false组件状态、保守准备补账及逐次ledger、所有helper snapshot、四共享导航前插/原body、三policy根≤128/8MiB及wire≤204/16MiB。归档自身输出单一WIP checkpoint，绑定检查器和归档前全部工件；不是保存oracle/完整cold通过或生产seal。若接近预算，记录未完成检查并保留false，不再启动验证。

独立review仍为PRE_SEAL findings；必须保留真实cold未闭合、import machinery差异未定位、Source49 expected truth/self-anchor/transitive root未认证、actual F未实现等未决项。不得以归档accepted或42个逻辑测试提升任何运行、资源、科学或正式gate。

实际终态：charge3.3670161s，accepted=false，failed_check=resource_caps_and_binding。127文件/8,462,120B超过组合8MiB 73,512B；完整导航snapshot与此失败全部保留。此前Source/AST/ledger/导航检查已执行，最终bound_files未生成。终账static118.8725048、pytest353.8217016，不再运行验证；本scope的原帽仍生效，不能把字节超帽当通过。
