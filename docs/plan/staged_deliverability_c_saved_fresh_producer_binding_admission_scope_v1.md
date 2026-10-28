# LIVE到真实producer/consumer：未执行准备草稿

2026-10-28，DRAFT_NONAUTHORITATIVE；承接[profile-matched LIVE交接](continuation_handoff_20261028_saved_fresh_profile_matched_live_v1.md)。本轮实施同步一次性binding consumer，先完成独立开发验证；真实连接的cold/startup/normal不在本轮执行。宽goal继续active，完整F未完成。

冻结前驱NFC10 checkpoint SHA8abd5d04628ee39cb93dc31f4e4eb307ecf9f49f99b80063d77d903e0a24bd65，16文件1824018B；累计977.1529690999844s、不接受38条；121文件10460646B及各旧预算/失败保留，原余45.33581750001758s不转用。

当前已有的只是conditional local runtime：在同一child内精确匹配NF9 profile，真实LIVE后CLOSED。它没有产生可跨进程搬运的能力对象或producer授权。新路径必须重新建同进程LIVE对象，不能恢复已关闭的PID12980或用JSON true/opaque image SHA发行能力。

首先完成三个实质工作：

1. 枚举实际消费者。旧ENTRY `_expectation_adapter`自行import并绑定6个adapter函数+4个依赖，仍属preparation；`capture_saved_expectation`会读取anchor/P1及53条数据。Controller/parent/fresh的wire/data API仍把producer/actual_sources/kernel等视为声明。对照原runtime-binding合同、33根catalog/能力DAG及当前Source49，写出需要同对象连接的真实调用图，不能将14个adapter直接根当完整生产闭包。
2. 先定义bootstrap LIVE→provider→consumer的进程本地接口、原owner/creator/namespace/adapter/bindings/retention及失败生命周期。Provider必须在真正消费前后重新entry/bookend，不通过可重绑moduleglobal选择expected roots，不触发第二次不受控import。明确旧data-only输入的拒绝域、如何保持Source49历史与新version/epoch，不能原位改已执行sources。凡跨进程只传有界摘要，真实能力必须在消费进程由其合法bootstrap建立。
3. 按完整入口、回调、依赖图、读取、持久化、失败/partial owner、cleanup、重开和父端采用计算DAG/次数/成本。优先复用已证明等价的代码，新增可达依赖/方法/常量/外部边界需绑定与反例；没有freshness/ABA证明不删检查。登记独立预算、RAM/存储/输出/硬停止及失败保存，再考虑有界connected integration。

新验证应覆盖：provider确由同一LIVE owner创建；同字节不同对象/creator/namespace、CLOSED/OBSERVED冒充LIVE、adapter/function/default/closure/class/global漂移、引用或retention丢失、回调中变更、consumer异常、partial ownership及双close。正例要真正调用获准的消费接口并保存同对象链和时序；仅声明一个新类或逐字段logical测试不算接通。

本草稿没有授权P1读取、actual role、OwnedChild/Job、native校准、模型/solver或长实验。若新消费路径需要这些动作，先按原合同和agent.md第7/9节形成具体可审实施与完整性能准入，再遵守已有明确授权范围。可以先做不触发这些动作的接口实现与独立synthetic fault tests，但不得以synthetic证据冒充真实producer/父端采用。

旧资源/身份/门禁边界保持：local profile equality不是独立TCB；registry/finder behavior、任意RAM ABA、native effects、连续/descendants/128MiB retention、资源/科学/正式/run/F均OPEN/false。最终F还需真实producer binding、父端采用、能力和资源闭包，不能用本轮LIVE替代。

## 本轮实现合同及预算

root唯一writer；既有wire_root_review只读PRE_SEAL。新文件为core38、namespace helper v2、probe36及独立consumer测试/开发controller；原Source49、NFC10执行字节和121文件10460646B全部冻结。开发工件进入 `results/tables/staged_rts24_saved_fresh_consumer_binding_unit_v1_non_authoritative`。新core/probe仅预留未来NFC11位置；本包不创建其manifest，不启动cold child。

固定目标为实际ENTRY `_expectation_binding_entry`，不是调用 `capture_saved_expectation`。调用图为：原runtime entry → IMPORTING且boundary CLOSED时prepare → 从held Source49编译consumer和10个root → 一次提交immutable plan/PREPARED → 原profile-matched LIVE → consume_once固定request → 原consumer(binding) → adapter返回身份检查 → plan/runtime/Source49后置检查 → CONSUMED → held close → 仅返回bounded canonical bytes。consumer不收到owner/runtime；六adapter根和四leaf模块/函数/default/globals/registry/路径及连接边逐一绑定。默认CONFIG按固定路径和原Source表达式验证；不能只比较可变global与default。plan/state进入runtime seal，plan内可变对象的原身份/metadata在每次entry和消费前后复核。

消费状态为PREPARED/RUNNING/CONSUMED/FAILED，runtime本身保持LIVE至close。拒绝重入、重复使用、异creator/clone、OBSERVED/CLOSED冒充、plan/函数/default/kw/closure/globals/retention替换。consumer异常、post-check或cleanup异常均无可采用输出；保存原primary和cleanup secondary。部分prepare提交失败也执行held cleanup。独立logical fixture不得称为实际LIVE连接；真实正例留待另包。

开发DAG固定：baseline保存 → compile/migration和原1124-input closure重开 → 注册当前源码/规格/测试/fixture → 一次受控unittest（旧25节点加本轮精确枚举）→ 独立只读PRE_SEAL → saved canonical重放/原输入fresh bookend → checkpoint。所有执行保存stdout/stderr/exit、阶段费用和原输入pins；失败不覆盖、不退费、不跨包重置。人工审查与工程编辑wall另列，不计作受控执行时间。

本包上限：static60s、unittest30s、总90s；阶段size5、register4、unit30、PRE_SEAL5、saved5、checkpoint4，其余static37s为同包失败保存及收尾余量。unit子进程一次，wall cap25s，完整捕获上限stdout128KiB/stderr32KiB，超时终止并保存失败；其余命令不重试，后继须另行登记。单进程开发诊断256MiB采样停止帽，非连续资源证明；最多12文件/4MiB，单record1MiB。旧累计977.1529690999844s、不接受38条，NFC10余45.33581750001758s保持原包。测试不能取得P1/role/native/模型/solver权限；模拟跨度新增0h。

验收必须保存精确测试枚举、完整终态及反例：同code clone、equal-but-different default、四leaf同步替换、kw原dict内容变化、plan替换/可变成员、retention删除、callback中替换、重入和失败重试、callback成功但后置/close失败、prepare partial commit。独立review findings闭合才发布开发checkpoint；全部authority/science/resource/formal/run/F flags仍false。

后续真实连接单独准入：当前命令29996/30000 UTF16仅余4，不能直接追加payload。先对exact successor验证传输和完整compiled identity/输出帽，再独立startup/profile admission，normal仍匹配原NF9 501203B profile；不得重算reference。本包不改变已冻结zlib loader，不以局部XZ压缩比较授予新的transport或cold权限。
