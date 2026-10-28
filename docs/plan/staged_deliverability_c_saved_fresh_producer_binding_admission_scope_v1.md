# LIVE到真实producer/consumer：未执行准备草稿

2026-10-28，DRAFT_NONAUTHORITATIVE；未实现、未登记、未分配预算、未执行新路径。承接[profile-matched LIVE交接](continuation_handoff_20261028_saved_fresh_profile_matched_live_v1.md)，宽goal继续active，完整F未完成。

冻结前驱NFC10 checkpoint SHA8abd5d04628ee39cb93dc31f4e4eb307ecf9f49f99b80063d77d903e0a24bd65，16文件1824018B；累计977.1529690999844s、不接受38条；121文件10460646B及各旧预算/失败保留，原余45.33581750001758s不转用。

当前已有的只是conditional local runtime：在同一child内精确匹配NF9 profile，真实LIVE后CLOSED。它没有产生可跨进程搬运的能力对象或producer授权。新路径必须重新建同进程LIVE对象，不能恢复已关闭的PID12980或用JSON true/opaque image SHA发行能力。

首先完成三个实质工作：

1. 枚举实际消费者。旧ENTRY `_expectation_adapter`自行import并绑定6个adapter函数+4个依赖，仍属preparation；`capture_saved_expectation`会读取anchor/P1及53条数据。Controller/parent/fresh的wire/data API仍把producer/actual_sources/kernel等视为声明。对照原runtime-binding合同、33根catalog/能力DAG及当前Source49，写出需要同对象连接的真实调用图，不能将14个adapter直接根当完整生产闭包。
2. 先定义bootstrap LIVE→provider→consumer的进程本地接口、原owner/creator/namespace/adapter/bindings/retention及失败生命周期。Provider必须在真正消费前后重新entry/bookend，不通过可重绑moduleglobal选择expected roots，不触发第二次不受控import。明确旧data-only输入的拒绝域、如何保持Source49历史与新version/epoch，不能原位改已执行sources。凡跨进程只传有界摘要，真实能力必须在消费进程由其合法bootstrap建立。
3. 按完整入口、回调、依赖图、读取、持久化、失败/partial owner、cleanup、重开和父端采用计算DAG/次数/成本。优先复用已证明等价的代码，新增可达依赖/方法/常量/外部边界需绑定与反例；没有freshness/ABA证明不删检查。登记独立预算、RAM/存储/输出/硬停止及失败保存，再考虑有界connected integration。

新验证应覆盖：provider确由同一LIVE owner创建；同字节不同对象/creator/namespace、CLOSED/OBSERVED冒充LIVE、adapter/function/default/closure/class/global漂移、引用或retention丢失、回调中变更、consumer异常、partial ownership及双close。正例要真正调用获准的消费接口并保存同对象链和时序；仅声明一个新类或逐字段logical测试不算接通。

本草稿没有授权P1读取、actual role、OwnedChild/Job、native校准、模型/solver或长实验。若新消费路径需要这些动作，先按原合同和agent.md第7/9节形成具体可审实施与完整性能准入，再遵守已有明确授权范围。可以先做不触发这些动作的接口实现与独立synthetic fault tests，但不得以synthetic证据冒充真实producer/父端采用。

旧资源/身份/门禁边界保持：local profile equality不是独立TCB；registry/finder behavior、任意RAM ABA、native effects、连续/descendants/128MiB retention、资源/科学/正式/run/F均OPEN/false。最终F还需真实producer binding、父端采用、能力和资源闭包，不能用本轮LIVE替代。
