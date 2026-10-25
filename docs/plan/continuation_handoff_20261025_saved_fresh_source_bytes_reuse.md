# C：操作内 source 字节复用交接

2026-10-25，DRAFT_NONAUTHORITATIVE，接续[投影交接](continuation_handoff_20261025_saved_fresh_expectation.md)，起始HEAD `5c3e885cb3b6dd50479ad685593590d5bd0ade86`，最终hash以远端读回为准。root唯一writer、独立只读PRE_SEAL；[合同](staged_deliverability_c_saved_fresh_source_bytes_reuse_contract_v1.md)固定200=160pytest+40static。实际F和整包科学/资源/正式门禁保持关闭。

原_adapt仅将initial49已核字节保留在局部字典供十个code比较使用；原adapter.sources及projection末次source guard均保持完整。initial read/compile/code失败也独立做source final，保留raw primary/secondary。当前49 raw精确1156762B，2MiB仅为已核字典逻辑上限，读取缓冲、编译和失败traceback另计；成功binding不持raw，不跨调用缓存。

当前epoch `84b6dafc7793caa2799ec99d3a38a5dfe3f3275448e3d30d3f2f01755a79e419`下63节点（10+35+18）全部终态通过，当前93.093s，含保留失败首轮的全部pytest 109.625/160s。旧失败为测试漏算loaded源码重读，修正断言后原guard不变；旧11通过及历史53/161不作为当前节点。除原_adapt外旧函数/类AST不变，scientific src、其他47依赖、前序3270路径及P1保持。

补充profile loaded=36：projection selected-source 223次，按49+2×(49+loaded)+fixture4核对，比前序233减少10；full为174次。P1仍683/53，当前caller image相同、full_P1_content_verified=false。首个profile因公式漏算fixture4次而失败、未保存操作内数据；保留原失败及旧合同，在原预算内登记一次补充，先保存逐文件raw后核公式，终态通过。Python traced峰值见[报告](../../results/tables/staged_rts24_saved_fresh_source_bytes_reuse_v1_non_authoritative/validation_report.md)，不是RSS或增量内存因果估计，也不与前序非traced wall比较。本轮执行helper/script前后pins及snapshot已保存。

下一步枚举生产adapter传递global依赖及角色能力，固定验证闭包/失效窗并接真实G0与trusted supervisor/ACK。prototype仍real_verified=false；生产G0/H3、issuer/driver、source6500、失败成本、180s逐边deadline、合法最大wire和host外部硬停止尚待完成。原G0–G3、parent/fresh hold、原科学审计、四库存和host末次full全部保持；actual F结果树及父目录不存在，无新模拟小时或native/solver调用。

恢复先核Git/进程，再做保存核验：`D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_source_bytes_reuse_v1_non_authoritative/checks_01/saved_checks.py`。当前保存checker使用固定本地标准库oracle，不导入可变ENTRY或递归旧checker；先核前序原字节及冻结receipt，再独立核固定外锚的P1全683。旧profile helper绑定仍false，目录身份仅限本次扫描书挡；保存层核验不升级生产权限。首轮saved14和修正前helper/report/support均保留。不要重复已完成的十次code读取复用；先推进生产闭包与trusted-role/G0合同，完成整体费用证明后再申请实际F。
