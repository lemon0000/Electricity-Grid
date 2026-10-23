# C：严格域摘要等价原型

2026-10-23，DRAFT_NONAUTHORITATIVE。接续[保存P1剖析](continuation_handoff_20261023_profile.md)。原重放的plain/asdict重复遍历已定位；本次只建立独立helper与普通等价测试，不接线或替换原development/plain/digest，不生成journal、CAS或新native结果。

[原型](../../src/staged_rts24_plain_v1.py)仅对codec.CLASSES中的精确dataclass、精确dict/list/tuple、None/bool/int/float/str/Fraction进行一次递归转换；dict只接受精确str键。Fraction仍转原字符串，tuple/list仍转list，dataclass按原fields次序展开，同一JSON选项生成bytes/SHA。静态类字段元数据不是输入或摘要缓存；每次调用从根读取全部值，重复别名分别遍历。

未知类型、所有子类、其他dataclass、namedtuple、非str键、循环或深度超过64触发私有Unsupported，并整根调用原plain；不把局部快结果与回退结果拼接。深度64仅限制快路径，科研输入仍由原函数解释。只捕获Unsupported，不吞原错误。探测使用type身份比较和已知字段；未知对象不做str/deepcopy/getattr/迭代，未知metaclass不参与hash/eq。当前注册类须验证无自定义字段访问或descriptor副作用。

等价假设为调用期间对象静止、同线程且标准库与注册类未被修改。原asdict先复制，直接遍历在并发突变下不能宣称相同快照；本候选不用于该情况。NaN/Inf仍由同一allow_nan=False编码器拒绝。循环等回退后比较异常类型及可观察副作用，不把RecursionError文本作为跨环境合同。

[普通测试](../../tests/test_staged_rts24_plain_v1.py)比较规范bytes/SHA、fast域确实未回退、未知对象整根回退与副作用、类型/子类/字典键碰撞、深度63/64/65、循环/共享别名、非有限值；读取全部403个保存P1 typed CAS根（journal130+point273）及所有P1 JSON mapping根，使用原ReadView完整bookend。完整683文件首尾SHA相同；所有注册类须实际覆盖，缺类补最小合成例。原model/solver/CAS put/publication在新测试中显式拒绝，原plain/digest身份保持。

这些是有界普通开发检查，不是性能attempt，不设提速阈值、不报告速度优势。生产接线属于独立R3后继，需解决依赖方向、实际执行身份绑定、反例和完整重放等价并独立审查；本原型不授予资源准入、seal、official verdict或运行权限。原P1唯一native授权已使用，C整体、139/F-X时序和D/E仍OPEN。
