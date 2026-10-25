# C：successor 角色切口与当前进程锚实现合同

2026-10-25，DRAFT_NONAUTHORITATIVE，接续[静态数据接口交接](continuation_handoff_20261025_saved_fresh_successor_data.md)，起始HEAD/origin `572d56a11394cd487f77a06ea9b3fe2d9e474871`。root唯一writer，独立只读PRE_SEAL。沿原38节点DAG推进实际角色连接，先实现它们共用的 retained self process/thread identity primitive；角色专用上游能力、完整bootstrap/store/owner仍按下表逐项接通，不把本primitive当作角色验证。

## 角色依赖切口

| 角色 | 已持上游证明 | 必要入口观察 | 入口之后的同进程能力 |
| --- | --- | --- | --- |
| host | 独立E、源/EXE/环境/时间、H0 | 真实self身份；arming前request原raw/SHA | 外部broker owner/HANDLE/Job强持到quiet；H3独立full hold |
| broker | host START、真实host/broker端点及request | request/START方向nonce；context首次create-only；offer/ACK raw/SHA | ACK经本地核验才有controller permit和真实owner |
| controller | request/context/ACK、mailbox方向nonce、独立上游controller owner绑定 | direct main/alias/path/flags/cwd/env、OS command line、source/EXE/context handle书挡、self身份与stage endpoint | G0原full683；bootstrap+外部owner+full-input/runtime能力后才建store/issuer，原+155/+165 deadline |
| parent | controller permit/G0链摘要、原reservation start、绝对deadline | 同上；原context/tree/endpoint和permit绑定，不能从收到的argv推expected | parent独立full hold/store/issuer、真实fresh owner至quiet，原+110/+125 |
| fresh | parent permit/parent hold链摘要、原reservation start、绝对deadline | 同上；无issuer | fresh独立full hold/result，原+80/+90 |

ACK/permit/G0不写回create-only context；跨进程packet只有绑定数据。expected argv必须由已持上游对象推导，不能由incoming argv自证。三子角色的真正bootstrap需同时绑定local self、外部retained owner和full-input/runtime能力；self HANDLE不能证明Job归属、observer持有或角色启动。logical main/channel正例若未来实施，必须使用不同exact type且生产store/owner永拒。本轮不创建logical角色bootstrap对象，也不以当前进程观察拼接出fresh验证。

## 本轮实现

在现ENTRY追加`SavedSelfProcessAnchor`及无注入参数的`open_saved_self_anchor()`：仅用标准库ctypes打开**当前**process/thread的query-limited、不可继承HANDLE，保留两HANDLE及实际PID/TID、各creation FILETIME、thread→process归属、kernel image path、系统原始command line。参数由GetCurrentProcessId/GetCurrentThreadId取得；不接受caller PID/TID/raw数据作为身份真值。

成功对象不可序列化，普通构造关闭；entry/raw访问检查创建PID/Python thread与native TID、不可变state/commit、原native函数对象及签名、原HANDLE身份/flags、image和command line前后相同。command line原样保存，不解析或声称已等于未来role expected argv；GetCommandLineW的系统返回内存不释放/修改。raw≤128KiB。关闭前做独立bookend，逆序各关闭自身新开的thread/process HANDLE一次；一个失败仍继续另一个。关闭成功的HANDLE立即从pending移除，后续close幂等；closed/unresolved对象不能再次entry或提供live raw。

构造任何阶段失败均清理已取得的自身HANDLE，保留原primary；cleanup也失败时抛不可序列化`SavedSelfAnchorUnresolved`，强持partial anchor、primary及全部cleanup secondary。未决对象不自动重开、不自动重复CloseHandle、不发行任何permit；普通测试的故障恢复只能在恢复原API后、核对仍属本测试的HANDLE身份后显式释放，不能把强持未决称已关闭。无借入upstream/channel/owner可被本primitive误关。

pre-seal加固：query snapshot/checked-api/creation/native-error helper的function/code/default/kwdefault/closure身份在构造时强持、纳入commit，entry之前核对，拒绝事后替换重放旧观察。该局部绑定不认证构造之前的任意Python全局状态，完整cold import/runtime可信链仍由后续bootstrap负责。关闭helper返回后，必须用对象强持的原GetHandleInformation独立得到ERROR_INVALID_HANDLE(6)才移除pending；空返回或其他结果均未决。若关闭与numeric handle复用之间出现不确定性，不自动重试关闭该数值，也不将它作为仍有确定所有权的资源处置。

本轮只证明当前Python进程/线程的本地观察与保留语义；不观察source49内容、EXE文件pin、环境、clock、context、direct main/role、外部owner或完整runtime，也不导入scientific adapter、创建Job/子进程/目录/共享映射。不修改现有函数/类AST、旧schema拒绝域、scientific src、SF49集合、guard/outer、P1和原F合同。raw中的`role_bootstrap_verified`、`external_owner_verified`、`full_runtime_closure_verified`、`full_P1_content_verified`、run/F及五gates恒false。

## 验证、预算与保存

普通检查新预算300s：全部pytest attempt≤240s、baseline/collection/静态/保存≤60s，单次≤40s。开测前固定精确nodeids、互斥组和组帽；重跑现有184节点及新self-anchor针对性节点，不继承旧epoch的当前通过。预留pytest失败修正帽至少20s。静态baseline≤10s、prepare≤8s、collection≤8s、admission≤3s、finalizer≤3s、两次保存核验各≤12s；实际按累积余量准入，不扩总帽。保存stdout/stderr/exit、SF49与实际helper前后pins、三源码与helper原字节snapshot；失败/超时保留，不重试actor。

测试正例使用真实当前process/thread query handles（同一pytest进程），与独立ctypes API交叉核对；fake失败窗口仅注入查询/close失败，不将替身成功结果标作真实角色。覆盖开第二HANDLE失败、初/末查询失败、identity/commandline漂移、raw/handles/creator/函数签名或状态tamper、跨thread使用、closed/pickle/普通构造拒绝、一次关闭失败仍清其他、primary+cleanup聚合及显式测试清理；确认各真实HANDLE最终无遗留。本轮不运行fresh科学重放、actual F、OwnedChild、solver或native校准。

证据仅写`results/tables/staged_rts24_saved_fresh_successor_self_anchor_v1_non_authoritative/checks_01`，≤12MiB/192files；文档另计。前序所有pins/历史结果/P1全683保全、三导航仅前插；保存oracle自包含stdlib且不import当前ENTRY/validator/helpers。future mutable变化只保留冻结测试证据，不冒充当前通过。发布按已授权检查点同步Git，读回远端并核空porcelain；所有运行/科学/资源/正式门禁保持关闭。

本轮保留三个失败：smoke05的kw bytes commit编码错误（3.984s，尚未打开query HANDLE）、admission17误读前序不存在的group03（0.094s，新helper修正，原失败文件不覆盖）、rest06中查询helper漂移被close过早拒绝（5.718s，22过1失败）。close现先仅核对象自身所有权，再将query漂移记primary并继续逐HANDLE清理。此后只有ENTRY变更，collection14的完整tests原字节不变；admission21据此前收集精确复用nodeids并固定新epoch `d217017c11d0b9c82e67b6300b0b413342da71f23816bf1a74c6d75889b3bbb4`。按已有smoke/rest成本将新self帽固定10+14s、其余184组帽183s；207+已花12.624=219.624≤240，仍余20.376s失败空间。当前218=34新+184回归全部终态通过，所有pytest实花151.686s；旧epoch部分通过24节点只保留历史，不计当前。

## API一手依据

采用query-limited access读取[thread creation time](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getthreadtimes)与[thread所属process](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessidofthread)，读取[kernel image](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-queryfullprocessimagenamew)和[当前OS command line](https://learn.microsoft.com/en-us/windows/win32/api/processenv/nf-processenv-getcommandlinew)。本primitive关闭自己打开的两个对象HANDLE，按[CloseHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle)语义计次；不关闭pseudo handle，也不通过close终止process/thread。
