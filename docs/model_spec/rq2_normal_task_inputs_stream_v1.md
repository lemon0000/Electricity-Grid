# 流式 pair binding 与 prepare 后继

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE。对应 `pair_normal_stream.py` 与 `normal_task_inputs_stream.py`；只准备机制输入和来源对应关系，不创建模型、solver、normal store 或执行结果。

前置证据见 `rq2_source_normal_stream_v1.md`：真实H25来源候选已在768 MiB Job内复现旧内容摘要，并保留8784小时年度数据。该单次组装证据不覆盖本文件的重复来源重建和完整prepare资源。

## 身份与快照

`StreamingPairBinding` 是新类型，分别绑定normal内容、新source assembly、pair内容、新实现及新binding identity。`legacy_content_json` 是完整旧格式power+pair报告的canonical JSON；其中旧implementation hashes仅用于复算旧内容reference，不声称旧binder运行过。`legacy_content_binding_identity` 对应旧报告内容hash，新binding identity另由新contract、normal/new assembly/pair/wire/implementation计算。

新binder的implementation identity绑定自身、流式source实现、旧power/pair模块、source_pair/source_window/workload_projection与window audit源码；source实现继续绑定旧normal依赖及runtime。外部必须提供新binder/source implementation、新assembly与pair pins，并在末端检查实现漂移。

完整staged pair先经旧source_pair重建；unresolved hours直接拒绝。随后 `source_normal_stream.validate_source_assembly` 重新读取并核验来源，取得owned rebuilt。power窗口对应与业务baseline检查共享这一份rebuilt，不额外deepcopy年度assembly。调用者的原assembly与rebuilt仍可能同时占用内存，真实资源表现需单独验证。

power对应保持旧 `_alignment` 的split、seed、trajectory、raw/continuous小时、timestamp、system load及1e-6残差检查；window/config/package/RTS manifest pins全部保留。baseline用Fraction按原语义检查映射后的MW、workload occupancy乘normalized unit，以及power source hour。初值历史、观测功率映射、注册coupling、assignment和formal认证flags不提升。

## 完整 prepare

新prepare接收原 `NormalTaskSourceRequest`，用于读取已固定的旧build-only机制声明。新 `task_source_identity` 把旧请求身份、source/binder新实现和本模块/旧reader源码独立绑定，不能把旧request pin直接当作新prepare pin。

保留旧prepare的声明字段inventory、typed scale、role、零solver/一model-build记录、旧normal/assembly/pair/binding外部pins，以及三份有界文件的前后重读、SHA和实现检查。来源组装走新source，重复内容校验也使用流式normal hash；pair对应走新binder。消费binder返回值时检查exact新类型、全部identity字段、canonical旧内容JSON，重算新binding identity，并逐字节对照saved旧binding。输出为新Owned `PreparedStreamingNormalTaskInputs`，包含新assembly、新binding和分段timings，不恢复旧assignment、terminal carry或执行cursor。

本入口仍是候选输入构造。后续执行消费者必须预先独立保留并校验新prepare/source/binding pins；本次派生新binding不能替代执行入口的外部验收。旧controller/worker/kernel/store/replay尚未接入此新类型。

## 验证边界

tiny synthetic验证包含：完整旧power+pair报告差分；完整旧prepare与新prepare的输入/旧内容wire差分；来源/窗口/业务对应故障；unresolved pair拒绝；caller mutation时的owned snapshot；禁止旧完整normal hash/binder或solver入口；所有wrapper身份字段篡改；机制声明不合法时拒绝在source load之前；末端文件变化拒绝。

这些测试验证语义保持和新身份分层，不证明真实H25完整prepare在768 MiB内完成。下一必要步骤为独立审查闭合后，在明确新实现pins和同开发预算下进行一次零solver完整prepare探针，观测重复重建峰值；之后才能接入normal execution/store/replay。正式科学注册、恢复右删失口径、四臂真实规模与正式启动门仍开放。

最终相关回归命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_task_inputs_stream_v1.py tests/test_rq2_pair_normal_stream_v1.py tests/test_rq2_normal_task_inputs_v1.py tests/test_rq2_pair_normal_binding_v1.py tests/test_rq2_power_normal_binding_v1.py tests/test_rq2_source_normal_stream_v1.py -k 'not real_pinned_h25'`，140 passed, 1 deselected in19.52s。明确排除的是旧uncontained真实H25准备测试，本次只做tiny/故障与相关回归。独立新binder+prepare测试45 passed in14.71s；限定pre-seal无开放实质finding，不是official verdict/receipt。

| 文件 | SHA256 |
|---|---|
| `pair_normal_stream.py` | `5f28eb19aeeb3b4cfa1df2c9e21d21aaf358306bf4f33f9747b89aa6540c728c` |
| `test_rq2_pair_normal_stream_v1.py` | `63ebca0858a2ddb2ab89ebd36fcc1e6bb15b5264a136b97b87123e24d57860e0` |
| `normal_task_inputs_stream.py` | `18b559083a3bf2b17e8f16e115906b27faebe64376d4e17f79d9636dcdd9bbf1` |
| `test_rq2_normal_task_inputs_stream_v1.py` | `9427898f301c65d8386487c260fa43d3a44bac21e40ae6a3e7da3b58d72ac072` |

原attempt22项、prepare probe13项、stream source probe1的11项及probe2的13项bytes/hash均再次核验一致。本轮没有启动真实来源probe、solver或正式实验，所有旧源码/结果保留。

## 完整 prepare 受限探针

`experiments/diagnose_rq2_stream_prepare_v1.py` 是已验证source probe v2的显式后继，保持原pinned H25 YAML、768 MiB process/Job、117秒phase+3秒quiet和16KiB单JSON限制。默认只读；仅 `--execute-development` 触发新non-authoritative sibling目录中的一次零solver prepare。旧probe与旧源码保留。

新probe实现pin除自身和既有监督helpers外，还绑定prepare源码和binder实现；request packet新增新prepare request identity。child继续从固定declaration环境顺序重算进程指纹，并精确核验实际环境键值及PID/creation/root/预算。request在spawn前、launch在release前写入。

child调用完整 `normal_task_inputs_stream.prepare_task_inputs`，输出有界 `prepared.json`，包括来源内容/new assembly、新prepare request、新binding/implementation、旧binding内容reference及canonical wire SHA、五段timings、年度小时数、零solver与机制标签。parent独立从pinned旧record重算这些身份，并检查timings字段集合、finite非负float、分段总和及外层耗时关系。仍要求成功exit、Job静默、有效资源观测、无reserve/API error和全部非认证flags；任何缺失或异常为unresolved，failure最多8帧。

本探针不调用model build/normal execute/store/replay；完成也只说明本次完整prepare及重复来源重建在所观测预算下返回一致内容，不构成整个normal任务、四臂或正式实验资源认证。

运行前主验证：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_diagnose_rq2_stream_prepare_v1.py tests/test_rq2_normal_task_inputs_stream_v1.py tests/test_rq2_pair_normal_stream_v1.py`，114 passed in29.11s，其中新probe69项。新增元数据故障测试包括自洽新binding摘要但旧wire不符外部pin的反例；parent直接核旧binding body/hash，新报告显式要求 `normal_assignment_verified=false`。

外部保留probe implementation pin `7195891d5840bb5b1f23cd2ec5842a00a7c94cdf4f92c61fa4183933595557c7`；script SHA256 `4a93ed52d7227650d12146b7248b845de0ba7f23ce34292ab0cc01581c25129a`；test SHA256 `a9733ce9e1c0f75e416cd33d5803e1cbfae6dc88b87957783421c803ef791e52`。同pin默认只读入口已返回headroom sufficient=true、errors=[]，尚不代表保留资源或实际运行成功。历史22+13+11+13项证据再次核验一致，新probe root/log尚未创建。

## 真实 H25 完整 prepare 结果

独立probe targeted69 passed in16.11s，限定pre-seal findings闭合后实际运行一次。命令为 `D:/Miniconda3/envs/compute/python.exe -B experiments/diagnose_rq2_stream_prepare_v1.py --declaration configs/rq2_normal_task_h25_development_v1.DRAFT.yaml --expected-sha256 9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6 --expected-implementation 7195891d5840bb5b1f23cd2ec5842a00a7c94cdf4f92c61fa4183933595557c7 --diagnostic-root results/tables/rq2_stream_prepare_probe1_non_authoritative --execute-development`。

终态 `prepared_content_reproduced`，errors=[]、failure=null。PID12872，creation FILETIME134344446516393634，process identity `3e1005737f84401c1b056f0bb3855c04f587deca7c49b779e1d842e850a82c95`。进程33.734秒exit0、Jobquiet=true，156次采样；process/Job commit峰值474931200/476151808 bytes，lifetime working-set峰值496750592 bytes，最低host commit余量16921927680 bytes；无reserve/API error。工作集和commit分别记录，不互换口径。

prepare本体31.440253秒，声明读取0.0585343秒、来源组装及其输入复核15.1086916秒、source binding16.2174079秒、末端检查0.0556192秒；child函数外层31.5708087秒。完整8784小时data保留，raw0..24→source1..25，solver_calls=0、normal_assignment_verified=false、observed_power_mapping=false、formal_result=false、whole_task_resources_verified=false。

| 身份 | 观察值 |
|---|---|
| normal内容 | `d9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c` |
| 旧assembly内容reference | `626f7dbe49772302d35da13bb05f2ffb69f1f599e35310484177c00711b32e7a` |
| 新assembly | `689ac1bc2d2a527b1a0efbe75e51d4f2a44cddb27cca7a1c623b5a0a6cabbe9e` |
| 旧binding内容reference | `e29ff34021a20becbbd4d6f79f5f316d34d61b96ff6725c5b1c6983fe6cd5abd` |
| 旧binding canonical wire SHA | `a93dae3f530a4f6f398b84144091e138824273c5b8a673706540b6f2beab04eb` |
| 新binder实现 | `6c2074b475f8c0c7cd93ea029cc3d784e666596b99d351477a2cda24bd657a4c` |
| 新binding | `a7b3acbeeac657d5429a9204873ad15c64bc08ae6deb68a3143fb24d243192fd` |
| 新prepare request | `0d8924e62b7e468a9ce935e06ddfb624de6c24b7418cd79613a2935dda6b3b39` |

summary精确绑定observation SHA `e423f12dbf43fcc5e5365c0fad6bbcd8e5ffa6728a7d99507e363daa19759d82` 与prepared SHA `3cc5c56ca49a98c9fd6f01265f09da48d9ad7a4dcfbd5355058ee2c542719710`。15项bytes/hash索引为 `results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_prepare_probe1_evidence.json`，SHA `2dcf84dfd4a898aa20acb80668d479fcc59de92013cb24bb30ef70620bd8832d`；历史22+13+11+13项与新15项均核验一致。

本次实际证据支持完整prepare及其重复来源重建在上述开发限额下返回一致机制输入。下一必要工作为normal model build/audit与数值执行后继，覆盖其内部旧normal identity调用，再连接store/replay/controller。尚未运行这些路径，未证明正常调度可行或四臂/整任务资源，未改变科学注册及正式启动门。

独立只读复核确认新15项与历史22+13+11+13项bytes/hash、summary/prepared/observation绑定、PID/creation/root/process identity及全部内容pins、timings均一致。限定pre-seal证据核验无实质差异，不是official verdict/receipt；后续执行入口仍须消费预先独立保留的新prepare/source/binding pins。
