# Normal 身份编码的独立流式原语

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE，尚未接入执行链。

真实来源prepare探针在768 MiB Job内，于旧normal_input_identity→_digest→_encode捕获MemoryError，详见 `rq2_normal_task_h25_development_v1.md`。旧实现先构造完整编码树，再构造JSON字符串及bytes；真实RTS数据对象包含整年时序，尽管本次请求窗口只有25小时。

`identity_stream.encoded_chunks` 对dataclass和tuple/list逐层输出，与 `json.dumps(legacy._encode(value), ensure_ascii=True, allow_nan=False).encode()` 逐字节一致。`digest(*items)` 按同一tuple封装更新SHA256。默认JSON空格、ASCII转义、字段顺序、float.hex、datetime和容器标签均保持。

mapping/set仍调用旧编码与repr排序，局部物化整个该子树。尤其mapping的排序是完整encoded pair的repr排序，不能擅自简化为只按key排序；测试包含两个不同class却具有相同编码key的碰撞。此实现节省dataclass/序列整棵树的重复物化，不承诺任意巨型mapping、set或单个字符串的硬内存界。

输入必须在遍历期间保持稳定；不新增原子快照或并发写保护。异常值/不支持类型继续拒绝。正常输入helper仍执行旧_validate，并使用旧CONTRACT、输入和旧_dependencies作为payload；不修改旧模块，也不恢复任何owned结果。

这里保留的是旧内容/依赖payload的编码与摘要。新代码本身的来源尚不由这个内容摘要证明：未来执行入口必须独立绑定identity_stream源码及新的调用合同，不能把相同content hash当作旧实现已执行的证明。现有source/pair/normal/controller/worker/replay路径均未切换。旧冻结和开发结果继续保留。

针对性测试26 passed in2.09s：18组类型/空容器/Unicode/float边界、编码key冲突、100个固定seed嵌套差分例、四种非法输入、tiny normal identity对照及合成序列内存分配比较。合成tuple-of-small-mappings的tracemalloc峰值低于旧编码的1/4；这是Python分配测试，不是H25 Job峰值、系统commit或整任务资源证据。

相关回归命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_identity_stream_v1.py tests/test_rq2_continuous_grid_normal_v1.py`，主验证108 passed in14.98s，独立复核108 passed in14.70s。source SHA256 `3a71d8fe0c20e292258bd04fb2645b1dddb0cf08d1dfef1e12a6ee1feab99b66`；test SHA256 `cd30ab90348fdee2108475e1a10281f408a6a1a77fec8364ca2e50f19e9ea99d`。限定pre-seal审查无开放实质finding，不构成official verdict或执行授权。

下一步先清点来源组装/validate、pair binding重建、normal execution/store/replay中的全部身份调用点，设计显式绑定新原语及adapter bytes的后继合同，再验证真实H25同内容身份与资源表现。只替换某一次prepare的局部调用不能消除后续旧全树编码，也不能复用旧execution pin宣称新实现已执行。

2026-09-21后继进展：调用点清单和独立来源候选适配器已完成，详见 `rq2_source_normal_stream_v1.md`。新适配器显式绑定实现身份，旧normal/task/pair/store/replay仍保持原路径；主相关回归165项、独立新适配器33项通过。真实H25内容等价和资源表现仍待验证。

同日后续：真实source probe2已复现H25的旧normal/assembly内容摘要，完整8784小时数据保留，在768 MiB cap内完成；source8.862秒、Job commit峰值341061632 bytes，零solver。详见上述规格的probe2证据。该验证仅覆盖一次来源候选组装；下一步为binding/prepare整链，重复重建、solver与回放资源仍未验证。
