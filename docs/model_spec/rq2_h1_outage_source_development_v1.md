# H1 outage source prefix development v1

状态：DRAFT_NONAUTHORITATIVE，R3。仅来源适配开发；零 native / Job。

`prepare` 使用 pinned `source_window.load_source_window` 读取同 split、seed、chain 的
raw_start-1 boundary 与当前已揭示 prefix；最大192当前小时。raw_start=0、split/chain
左边界缺行必须 unresolved，不跨 split、不读取未来事件结局、不默认无事故。
这不是完整支持目录覆盖证明；所有原有义务仍保留，无法取得边界的义务阻塞后续完整运行。

完整事故三字段、source hour、时区时间连续性及声明的 component inventory 均须匹配。
boundary映射为0、当前小时为1..hours；入窗仍持续事故的 observed_start_hour=None。
同component更换event ID、同event变component、已结束ID重现均拒绝。
source ID与timestamp仅留审计，decision identity只绑定中性disclosure projection。

generator repair return cap由机制输入逐小时显式提供，只在观察到generator结束时出现。
来源适配器不证明cap可执行；后续physical kernel必须继续核验nameplate及物理边界。
不得从未来event end或nameplate自动生成cap。synthetic source不代表经验事故观测或安全认证。

prepare前后校验implementation identity并重读pinned window。返回值仅fresh-at-return；
公开Prefix可手工构造，不是认证凭据，消费者须在owned调用内重读外部pins并重建/消费，
或另建持久receipt/reader。normal_source_correspondence_verified、detached_consumer_authenticated、
formal_result均false。尚未连接N root、persistent lane owner或业务事务。

验收：零solver来源实测及合成反例，覆盖trip/continuation/repair、缺边界、split/seed/chain、
隐藏替换、ID复现、输入/实现漂移、decision identity不受source ID/clock影响。
必须独立只读PRE_SEAL审查；本规格不提供official verdict或运行授权。
