# Phase dependency 读窗与 consumer 接线切口

状态：DRAFT_NONAUTHORITATIVE。root 为唯一 writer。独立只读 PRE_SEAL 切口分析已返回；尚未完成独立只读 reader 实现或整链验收。旧body、failed attempts及旧schema全部保留。

## 直接成本证据

95的真实空registry header在300.328s触顶；首创建、inspect、guard和关闭完成，Bootstrap4重开完成，Roster重开未完成。进程两次逻辑读计数约6.70GB到11.76GB，未采Python栈，不能只凭它作行级归因。

96仅运行两次canonical detached `prepare_group('training_ub',0)`：各973 paths /42,587,617 bytes，1960次`read_stable`。带cProfile的总wall约0.993/1.004s，read_stable累计0.608/0.590s，纯`_project`累计0.144/0.139s；cumulative times有包含关系，不能相加。每次process逻辑读94,670,077 bytes、4739 read operations。两次完整输出SHA均为b6f4514ebfb2223d094317e5bf6ce31742907d9a18243a47b4bf9cd71e92961d。不能拿带profile基线与未profile窗口直接算提速比。

源码显示旧verifier的`read_stable`通过`path.open('rb')`读取，绕过entry14的`Path.read_bytes`缓存。Roster `_candidate`在phase cache建立后仍可触发六次完整phase-group扫描；constructor在journal前至少十五次，后续check/view/replay继续叠加。这是静态计数，不是95的函数采样。

## 保留旧exact owner的最小路径

新增两个独立模块：phase依赖data window，以及接受exact Bootstrap4/Roster3的只读observation。后一模块自行重建旧owner/Roster的读侧检查、phase候选、registry和journal replay。原对象、header、phase cache与写入route保持原样。

新reader不能调用旧owner `_check/_registry` 或roster `_check/_replay`，也不能调用会回调roster `_check_live`的旧Roster journal.check/rows；否则会重新触发完整旧扫描。需要versioned functional replay，固定原storage/base-journal/code routes，并完整保留creator/thread、closed/poisoned、aliases、declaration/config、implementation、registry declaration、journal heads与N0合同。

旧phase audit仅作为predecessor payload与header逐字对比。新receipt必须明确entry/exit physical validation、internal held-byte projection、per-call physical freshness=false、between-bookend ABA covered=false，以及实际完整扫描、logical projections和复用计数。不能把旧payload内`fresh_at_return_only=True`当成本次新路径执行事实，也不能构造旧PreparedManifest冒充当前canonical prepare。

可以把新reader的phase window和retained N0私有kernel窗组合到一次同步Common里，各自单独identity/receipt。新consumer负责三guard、caller与root/pin绑定；纯phase data window不产生consumer credential。

若选择优化Bootstrap公共构造、reopen、`_check`或写入新header，则需要Bootstrap5/Owned5/Roster4。该更大类型图尚未选择。旧group-v1科学投影仍可保留；只有替换public phase prepare/return schema时才需要phase binding后继。

## 当前原型与待验项

独立phase operation draft已写入。97首轮六项单元通过，六份predecessor payload与canonical before/after逐字一致；窗口总2.930s含entry0.746s，尚无相同环境/未profile的对照。它的source/resource alias防护、重复物理读取计数、失败与并发窗口仍待PRE_SEAL修复，不能接入genuine caller或称优化验收完成。

还需覆盖四sibling ordinal、direct/header-only group、dependency缺失/替换/漂移、same-byte identity replacement、runtime alias、partial acquisition、exit失败、first-error、nested/reentry/thread与关闭后字节清空，并完成一次真实old/new reader own-root差分。所有正式、native和资源门继续OPEN。
