# 2048或自然返回：后续准入草稿

2026-10-28，DRAFT_NONAUTHORITATIVE；尚未实现、登记或执行。依据[真实1024交接](continuation_handoff_20261028_saved_fresh_actual1024_v1.md)，目标是扩大一次有界真实import观察并争取自然返回，不把有限stop替代OBSERVED/LIVE、完整F或资源准入。

前驱NFC6 root16文件965896B、cp SHA 5c5a2e47010031bb6b0da99fc9cd928917a590c91e04db2f9db88ea00d7daad3冻结；累计830.1274519000538s、不接受37条及所有旧余量/失败保留。NFC6在1024 stop完整收尾，但未自然返回；cache11→117，machinery observed2/authenticated0/pending，direct peak WS129970176B仅观测。

候选问题为“2048个guard-passed open之前是否自然返回；否则在2048处取得完整受控stop及异常链”。每次仍仅一次adapter import，最多2047次窗口内physical open；预期progress帧数由10增至18。新版本须以精确constructor及相关反例明确修改limit、schedule、reason、parent schema与oracle；原1024 helper/parent/core/results全部不动，不静默重解释旧记录。Source49和全部科学约束继续原样。

待核的完整DAG为size/注册→唯一完整unit→PRE_SEAL→startup/profile→唯一2048或return→saved→checkpoint。可供实施评审的预算候选为6/3/10/4/5/4/20/4/3秒，即static49+unit10=59s，最坏累计889.1274519000538s；这是未分配、未登记的候选，不是已获准入的运行包。NFC6 actual audit8.7689s中parent5.7918s、窗口3.5519s只覆盖1024，cache增长使更大窗口成本可能非线性，不能用翻倍外推充当完整路径实测。

进入任何新执行前还需闭合：精确source/DAG与新增调用量；实际命令≤30000 UTF16和registration/packed/root布局；18帧census在24576B与总stderr32768B、stdout131072B帽中的最坏保存；新增limit/schedule/两种终态与错误/超限的完整反例；current注册事实、runtime origins和source freshness；独立PRE_SEAL。不得靠增加递归历史checker或继续pin-memo局部基准替代这些工作。

**内存与停止策略尚未闭合**：123.949MiB的单child peak WS不证明128MiB combined retention，也不能给更大窗口RAM上界。先区分direct RSS、retained对象/bytes和整链预算，核新窗口的观测及安全停止策略；未定前不得启动2048。所有旧缓存与gate定义不改，任何新观测只支持本次诊断，不授予资源权限。

即使自然返回，仍须分别核finder metadata/registry、source49末端bookend、import boundary终态、runtime owner/handoff、OBSERVED/LIVE、issuer/permit/quiet/父端采用；不能据一次return填满这些未核门槛。现阶段不启动P1/实际role/OwnedChild/Job/F、native校准或长实验。失败保存原raw、收尾和拒绝端点后停止，不自动重试/顺延/退款；新预算不得挪用旧余额。
