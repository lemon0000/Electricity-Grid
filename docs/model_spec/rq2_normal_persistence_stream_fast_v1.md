# 快速编码执行链的日志、回放、归档与worker后继

日期：2026-09-27。状态：DRAFT_NONAUTHORITATIVE。

消费`rq2_normal_execution_stream_fast_v1.md`的独立执行类型。旧日志、结果、源码和冻结
配置保持。本轮只验证小型合成来源；未启动真实年度fast kernel任务。

## 一次性日志

`normal_declared_store_stream_fast.py`使用独立schema
`draft_local_ntfs_one_declared_fast_streaming_normal_invocation_v1`、SQLite application ID
`0x4e465331`，公开类为`DevelopmentDeclaredFastNormalStore`和`DeclaredFastNormalStoreInspection`。
独立header绑定当前实现、compact request、外部execution pins和原record限额。

保留原NTFS lease、SQLite事务与内容编码；intent COMMIT/readback先于prepare，求解前
callback仍在声明入口原位置。缺完整返回保留unresolved intent，不重试；完整返回按
新owned type和identity核验后存result，包含未接受但已返回的raw证据及已知调用数。
before/after intent与before/after result四个真实进程退出窗保留unused/unresolved/returned区别。
日志完整性不认证求解器运行，也不能恢复成可执行cursor。

## 独立回放

`normal_declared_replay_stream_fast.py`使用独立schema、replay identity、
`DeclaredFastNormalRecordReplay`和`FastSourceRecordReplay`。解析三层新的encoded类型，
通过原stream prepare和新fast model/kernel规则重建来源绑定、完整assignment和witness，
复核数值、资源记录及各层error词表/投影。所有旧schema/type和旧replay pin仍拒绝，
即使外层摘要按篡改内容自洽重算。

store入口仍要求独立current head，genesis不授权数值回放。replay不调用solver；
缺raw/无assignment/timeout继续保持其原不确定性。native execution和历史资源测量
authentication均false，archive_consistent不等于数值accepted或工程认证。

## 有界归档捕获

`normal_archive_capture_stream_fast.py`连接新journal schema/application ID，使用独立
capture identity与`FastStreamingNormalArchivePins`；复用旧budget、64 KiB只读分块、
合作式deadline、文件及lease检查。opaque result identity仍须独立replay核验。
不做来源prepare、模型重建或solver调用；调用方须先证明Job静默，capture本身不证明静默。
未完成/sidecar/文件或实现漂移仍拒绝，不生成cursor或正式结果。

## 验证记录

根首轮store/replay全组运行及新旧隔离定向记录分别保留，不将后追加测试计入已启动的整组。
新增旧application ID、旧replay pin及三层旧type反例定向6 passed,107 deselected in38.71s。
独立store/replay完整链及隔离7 passed in53.78s，四个真实进程退出窗4 passed in35.48s；
差分审查未发现实质finding。

capture首轮37 passed,1 failed in84.57s。失败发生于新增双向隔离测试同时请求新旧
supplied fixture，重复改写同一临时normal record，触发正确的来源hash拒绝；不是capture
实现失败。去掉新测试多余fixture依赖后，受影响双向stream隔离2 passed,36 deselected
in5.94s。未改实现；保留首轮失败记录，不声称该次38项全通过。

固定worker后继已接入（验证见下），下一必要工作为controller连接新类型和三层回放报告，随后按受限后继声明
验证真实H25完整执行资源与有效assignment。此前编码组件改善不证明60秒门已过。
初态及业务功率映射保持机制假设；完整current/episode、UID/四臂资源、恢复右删失、
风险分母、科学注册和正式启动门仍开放。

| 文件 | 本轮SHA256 |
|---|---|
| normal_declared_store_stream_fast.py | `3786885fb49be455a14d3e51908da27389cd3055f32ca391126af86fce677f2b` |
| normal_declared_replay_stream_fast.py | `e264a99e8aaf847248b1c3e5ad9d4ae13cc02bd05bed47b83a7c4d6c19480706` |
| normal_archive_capture_stream_fast.py | `e48159a759627962a1d772979813baae66b716c30f79a8683dbb7a3bb5c6c91d` |
| test_rq2_normal_declared_store_stream_fast_v1.py | `4044bca5f198bdfacec2f8a763fde71069b6b318c0e2ee4f3061c899882d1c39` |
| test_rq2_normal_declared_replay_stream_fast_v1.py | `9dc0a3520dd9e7c57ebbf563c90798729f4228e63460bf0aca96f52560b31a05` |
| test_rq2_normal_archive_capture_stream_fast_v1.py | `7d07a1b7aaf92bbcf38a6fb79f28c781122d061f12d4e5d40ddec9b408cbf95f` |

源码在src/rq2_joint_deliverability_boundary_v1，测试在tests。新增模块未被真实运行结果绑定。
独立capture双向schema隔离、禁止prepare/model/solver和capture→replay共4 passed in21.78s，
差分审查无实质finding。所有独立结论限定pre-seal范围，不生成official receipt或运行授权。

## 固定worker接入

`normal_task_worker_stream_fast.py`使用独立schema和`FastStreamingNormalTaskRequest`，
固定argv导入新worker。task identity绑定新replay/journal/kernel链，compact decode保留exact
字段与数值类型验证；旧worker request对象不被接受。prepare仍使用原stream source contract。

execute/replay阶段保留原cwd/environment/argv、PID/FILETIME、packet/intent/launch/claim、
文件与root检查。prepare后、source调用前再次检查运行态，失败留下不可重试的intent；
执行存新owned三层结果，回放完整新报告。worker不认证整Job静默、硬资源限额或双阶段顺序，
这些仍由待接入controller承担。真实固定argv测试仍仅为受限Job下的缺失来源负例；
完整execute→capture→replay正例使用tiny合成来源，不能称为真实RTS执行。

新增旧worker request类型隔离1 passed,29 deselected in2.75s；整组与独立审查终态另记。

## 最终根验证记录

命令统一使用`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`：

- `tests/test_rq2_normal_declared_store_stream_fast_v1.py tests/test_rq2_normal_declared_replay_stream_fast_v1.py`：
  首轮108 passed in761.94s，含四个进程退出窗口及完整数值篡改反例。运行启动后新增的
  五项隔离测试由上文6项定向覆盖，不计入108；不是最终113项单次整组通过。
- `tests/test_rq2_normal_archive_capture_stream_fast_v1.py`：修正测试夹具后的最终全组
  38 passed in76.44s。
- `tests/test_rq2_normal_task_worker_stream_fast_v1.py`：首轮29 passed in153.86s；
  后加exact type隔离由上文1项定向覆盖，不声称本次为30项单次整组通过。

以上进程均exit0，无未结束的根测试会话。测试中的solver仅为tiny受限调用，未运行年度求解。
worker源码SHA：`073e45ef84ff95218ccd0a519b625a0c78fed0367be1d86f5b5cefb2b20bbdfa`；
最终测试SHA：`e1fd7a6e448cd781ffb140e61788f016be68e7d80c5df766c8d58088c2ce0348`。

独立worker复核：compact identity不prepare/solve、execute→capture→零solver replay、
prepare后六类运行态漂移共8 passed in56.10s；旧request exact type追加1 passed in2.52s。
源码与测试SHA一致，相关pre-seal findings闭合。task身份闭包、失败留存与求解前检查位置
保持；仍需controller证明顺序两Job及静默后归档流程。没有official verdict/receipt或正式门变化。
