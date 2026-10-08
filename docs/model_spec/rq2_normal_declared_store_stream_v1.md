# 流式声明入口的一次性调用日志

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE。

`normal_declared_store_stream.DevelopmentDeclaredNormalStore` 为完整
`normal_declared_execution_stream.run_declared_normal` 提供本地一次性 intent/result 日志。
它沿用旧 normal store 的 SQLite 事务和 NTFS lease 机制，使用独立 schema/application ID，
保存新 `DeclaredStreamingNormalResult` 及嵌套 source/kernel/raw/witness，不改旧源码或数据库。

## 请求与身份

构造只持有小型 `NormalTaskSourceRequest` 和全部外部执行 pins/spec/budget 的私有副本，
不读取年度数据、不运行 prepare、不预存 assembly。header 绑定 request、source/binder/kernel
及 declared execution 身份、source wrapper 源码、日志和lease源码、Python/SQLite版本、
规范目录与目录身份、完整记录字节上限。每次操作重核 header 和当前实现。

source execution pin 在 header 中独立保留；完整 declaration/pair/content lineage 在
intent 之后由原声明入口重建验证。journal 不因一个语法有效的 pin 而宣称来源已验证。
已存声明文件发生变化时仍可对原 request/pins 的日志作完整性核查，不能重新执行。
源码或私有请求漂移则拒绝正常操作，现有文件保留。

## 一次性事务与实际动作

执行顺序为 unused 检查 → 独立 intent COMMIT → 新连接 readback →
完整 prepare/source/normal 调用 → 完整结果序列化 → 独立 result COMMIT → 新连接摘要读回。
intent 在 prepare 之前持久记录。内存 poison 从尝试写 intent 起生效。

| 持久状态 | 允许行为 |
|---|---|
| unused | 完整身份核验后可调用一次 |
| unresolved_intent | 只核查；禁止重试，调用数不能推断为零 |
| returned_record_unreplayed | 只核查完整记录与独立 head；不能恢复为可执行结果或认证 |

prepare 失败、丢失下层返回、超大结果或提交前退出均保留已提交 intent。
已知 source/kernel 结果但 post-declaration 失败时，保存完整 unresolved declared result，
其中已知调用数及 raw/witness 保留。wrong owned type/request/execution identity 返回不归档。
进程死亡释放锁不代表未调用。结果提交成功但响应丢失，可使用预存 genesis 核对单次链；
一旦有 intent，重新打开仍不能重试。

本地 fixed NTFS、`_non_authoritative` 新目录、非继承锁、进程内锁registry、文件身份和
reparse/hardlink 拒绝逻辑沿用已有实现。SQLite 要求 DELETE/FULL、foreign keys、精确
schema/application ID/user version 和完整性检查。不同进程的同目录并发拥有者被拒绝。

## 证据范围

`inspect` 验证 canonical JSON、完整 encoded result 摘要和记录 lineage，不恢复 owned 对象。
`numerical_evidence_replayed=false`、`native_execution_authenticated=false`、`formal_result=false`。
独立 current head 能发现结果及内部摘要被自洽改写；genesis 不绑定未知后续结果，不能据此
认证原生执行。journal 不把自己的持久化能力写回 inner kernel 的 flags。

`max_record_bytes` 限制完整结果封装的 UTF-8 bytes，超限不写部分 result；它不是 SQLite
目录总量、内存或磁盘预留限额。序列化在检查之前，完整资源仍需 Job/controller 覆盖。
此模块没有新增数值阈值或扩大开发预算，未执行真实 H25 或正式实验。
真实进程退出测试检验软件事务窗口，不是断电/硬件持久性认证。

## 验收与下一步

验证包括 tiny 完整声明→prepare→source/binder→原生 HiGHS→日志、精确嵌套wire、
intent/readback先后顺序、四个真实进程退出窗口、丢失提交响应、独立head、复制/硬链接/schema、
wrong owned return、结果字节超限、声明文件变化和失败证据保留。
tiny来源loader/package依然是synthetic fixture，不能作为真实业务或RTS规模观测。

下一必要工作是新的独立数值 replay：从 pinned 小型 request 重建 prepare/source 输入，
解析而不恢复三层 owned wire，复核全部 source/kernel 数值、assignment、调用记账、
timing/peak/payload 字段与 declared 接受条件，并绑定独立 record/result/store/replay pins。
随后将本store与replay接入worker/controller Job并验证真实H25全链资源。
恢复右删失、风险分母、current/四臂、科学注册及正式启动门继续开放。

## 工件与核查

源码SHA256：`99df60a67522ba5f6e8bd5b2a8a4a3b7c840bf5dc70688efba49f98bed538742`。
测试SHA256：`52119ac17827a13ba7aa599828c05e519f12b8bbceccdb877a118b39393f0668`。
旧五批诊断索引22+13+11+13+15项bytes/hash全部一致；`git diff --check` 无错误。
首轮19项测试通过（72.34s），随后增加7项声明入口专属验证。这些hash是开发记录，
不构成production seal或official review receipt。

独立只读 R3 pre-seal 审查26 passed in100.65s，源码/测试hash与上表一致，无开放实质finding。
审查确认事务顺序、四个退出窗口、丢失提交响应、禁止重试、声明变化后的证据保留及
完整nested wire；独立数值replay、Job整任务资源和真实H25仍未验证。本日志包含本地路径
和原始诊断文本，属于local non-authoritative记录，不是公开数据交付包。

主相关回归：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_declared_store_stream_v1.py tests/test_rq2_normal_store_v1.py tests/test_rq2_normal_declared_execution_stream_v1.py tests/test_rq2_episode_store_v1.py::test_close_releases_handle_even_when_unlock_raises tests/test_rq2_episode_store_v1.py::test_hardlinked_store_files_are_rejected tests/test_rq2_episode_store_v1.py::test_real_junction_store_path_is_rejected`。
结果81 passed in202.15s，包含新日志、旧日志、声明入口及相关lease保护回归。

## 2026-09-21 固定 worker 运行态检查接入

声明入口和日志的未seal draft 增加 before_source 运行态检查位置：日志 intent/readback 后准备输入，在source求解前执行固定worker postcheck。检查失败保留pending intent，不调用source、不自动重试；callback不进入header/result，也不作为认证证据。此改动改变draft implementation/execution pins，前文SHA与测试数字保留为历史记录；当前验证与精确SHA见 rq2_normal_task_worker_stream_v1.md。旧冻结工件保持原字节。
