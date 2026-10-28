# 独立profile配对与LIVE：未执行准备草稿

2026-10-28，DRAFT_NONAUTHORITATIVE；未实现、未登记、未执行、未分配新预算。承接[OBSERVED→CLOSED实测](continuation_handoff_20261028_saved_fresh_post_return_observed_v1.md)。完整F及相关正式权限继续未完成，宽goal仍active。

冻结前驱NFC9 checkpoint SHA5fb9c83a6ec9e7933e684a7f4ca2491fa52d9d7e1a6a8b7cc3740d9eb30428da，17文件2285992B，diagnostic_accepted=true；累计937.488786600002s、不接受38条。105文件8636628B及旧预算/失败保留，本包余42.22140910002054s不转用。

NFC9仅import_discovery，未传独立import_profile，finish正确产生OBSERVED。下一后继须先设计独立参考profile的来源及新normal case连接；原NFC9 import_profile.json为501203B，必须按原raw/pin使用，不能删行、改路径、放宽类型/排序或重算到目标结果来迎合相等。相等只能产生条件性本地LIVE状态，不能授予角色、permit、producer或F权限。

准备顺序：

1. 核当前parent manifest/check_plan、case路由、create-only输出与profile匹配实际DAG；旧POST validator只接受import_discovery/OBSERVED，不能直接换case后复用。新normal/LIVE前置与关闭后CLOSED必须分别核验，所有旧失败和cleanup路径保持。
2. 枚举新root/transport/helper身份对modules/cache/path/finder profile的影响。完整固定输入/Source49与当前环境相同不自动证明跨child profile相同；差异必须保存，不能修剪参考。新startup/profile必须有自己的raw/PID与收尾，Source49/freshness/两次profile一致保持。
3. 固定参考profile复制或外部ref白名单、文件cap和input闭包，明确其原始NFC9 raw SHA及自身路径/transport provenance；检查normal分支JSONL/journal是否增加文件或产生其他历史重放，不能写满已冻结NFC9 root。
4. 给出新的完整次数/预算/资源/输出上界与故障矩阵，覆盖参考profile缺失/漂移、schema/false claims/TCB变化、OBSERVED冒充LIVE、boundary已闭合但finish不匹配、失败后清理、raw/derived/saved重开。再建立versioned constructor/oracle、unit和独立PRE_SEAL。
5. 只在上述短诊断合同闭合后考虑唯一有界配对路径；不启动native校准、P1/实际role/OwnedChild/Job、模型/solver或长实验。其他动作仍受原授权与agent.md第7/9节约束。

可复用的成本证据只限覆盖相同的路径：NFC9 parent6.2097452s、外层actual9.7616024s，30图21 namespace/9 adapter、5 Source49 bookends、finder_check10、adapter_check8、profile2；adapter图137 nodes/28501B、namespace2940/376728B。新参考读取、case/journal、比较失败及保存成本需单独界定。原sampled256MiB/process、512MiB/pair、40图/4MiB image、stdout131072/stderr32768与command30000等帽不能由旧余量自动扩张。

LIVE之后仍需真实producer binding、父端采用、当前F完整闭包及适用资源/硬停止证明。loaded Python graph、registry/finder behavior、任意RAM ABA、连续/descendants/128MiB retention、native effects、独立TCB与科学/正式结论仍OPEN/false；这些是实质剩余边界，不由文档、goal状态或本地测试改变。
