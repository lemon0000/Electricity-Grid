# 流式声明日志的有界归档捕获

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE。

`normal_archive_capture_stream.py` 将既有只读归档捕获接入声明日志的独立schema/application ID。
复用旧 `ArchiveCaptureBudget`，保留database/record/time上限、1 MiB header限制和64 KiB分块读取。
新的 `StreamingNormalArchivePins` 与旧类型区分；capture identity绑定自身、当前journal、lease、
kernel及提供budget类的旧capture源码。旧文件、数据库和冻结诊断工件不修改。

## 行为与边界

调用者先证明整Job静默；capture本身不证明静默。它取得合作lease，核对规范本地NTFS路径、
目录/锁/database身份、精确schema与数据库完整性，并使用SQLite mode=ro/query_only读取。
sidecar/journal/WAL/SHM存在时拒绝，不自动恢复或清理。mtime/大小/身份和实现pin在末端复核。

header有界解析，并把独立store identity、目录身份、max_record_bytes及declared execution pin
与记录交叉核验。无intent的unused状态也必须匹配declared pin；不能把任意语法有效pin配到既有store。
pending/returned状态另精确核intent bytes，结果BLOB逐块计算摘要和head。

capture不运行prepare、不构建年度输入或模型、不调用solver，也不解码result payload。
claimed result identity保持未验证，交由独立数值replay核对；即使payload不是合法数值记录，
opaque capture仍可能完成，其成功不代表结果被接受。
result_identity_verified/numerical_evidence_replayed/native_execution_authenticated/
whole_job_quiescence_verified/formal_result均false。

## 验证与接入

测试包含新声明日志→opaque capture→零solver独立replay、错误claim由replay拒绝、
64 KiB读取上界、payload不解码、deadline/byte gates、sidecar、schema/index/trigger、
hardlink/复制目录、锁与中断释放，以及旧新schema双向隔离和unused/pending执行pin拒绝。
tiny来源及网络是synthetic fixture；没有真实H25全链或正式运行证据。

下一步接入固定worker和controller。worker必须保留准备后、求解前的运行态复核：
packet/cwd/environment/argv/intent/launch/claim或身份漂移不能在求解后才发现。
新声明入口把prepare放在一次性intent之后，接入时须在这一入口内部保留等效的前置复核位置，
不能为了适配而删掉旧worker的检查语义。当前尚未实现该连接或Job全链资源验证。
current/四臂、恢复右删失、风险分母、科学注册与正式启动门继续开放。

## 验证记录

首轮31项通过（51.08s）。扩展后主相关回归命令：
`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_archive_capture_stream_v1.py tests/test_rq2_normal_archive_capture_v1.py tests/test_rq2_normal_declared_store_stream_v1.py`，
91 passed in165.02s。

pre-seal审查发现unused状态未核header中的declared pin；新增反例修复前明确复现
1 failed,35 deselected in4.08s。补header mapping形状/唯一string keys/declared pin核验后，
`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_archive_capture_stream_v1.py`，
最终新捕获全组36 passed in58.18s。前述91项不代替最后修复的直接测试证据。

源码SHA256：`05ef07b7bf498aa662ff2f7365d9940acdc48038a5ebb9f2bfa03f2a575176d4`。
测试SHA256：`c52c15347518697d9581b7572253aba7b9d633604d7673a79a830258d31a5906`。
旧五批74项工件bytes/hash一致，`git diff --check` 无错误；无真实H25全链或formal run。
以上为开发记录，不构成production seal或official review receipt。

独立只读 R3 pre-seal 全组36 passed in58.37s，最终源码/测试SHA一致，finding闭合，无开放实质问题。
范围仍为合作lease下的本地只读完整性，不证明hostile ABA、断电持久性或Job静默；
本地header含路径/runtime信息，不是公开数据交付物。该意见不是official verdict或运行授权。
