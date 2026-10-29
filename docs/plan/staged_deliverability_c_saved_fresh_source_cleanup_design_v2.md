# F：Core46 来源清理合成验证 successor

2026-10-29，DRAFT_NONAUTHORITATIVE。保持 [设计 v1](staged_deliverability_c_saved_fresh_source_cleanup_design_v1.md)的机制、32方法验收矩阵与未证明边界，使用 [scope v2](staged_deliverability_c_saved_fresh_source_cleanup_scope_v2.md)。root 唯一 writer、独立只读 PRE_SEAL，无 official verdict/receipt/seal。

v1唯一32方法执行为24正常、2 failure、6 error：合成 `Fixture.bookend` 捕获了 `state` 闭包，四成员 spec 经 `FunctionType(code, globals, name, defaults)` 重建时没有 closure，触发 `TypeError: arg 5 (closure) must be tuple`。同一额外 primary/secondary 导致两个顺序断言失败。原66帧、stdout9488B/stderr16074B、rc1及全部错误保存；capture无截断/kill，HANDLE/pipes/readers终态。v1包费用5.308336200003396秒不退款，checkpoint仅接受失败元数据，diagnostic_accepted=false。

Core46与已冻结Core45逐字节相同：93922B / SHA `7cfa6f44dff03d4c160935d59f9511c08b4b3ffffc052f6bcdea9985e041d7a4`。test v2只改source路径和合成 bookend：`bookend(owner, _state=state)`，函数体仅读 `_state`，从而不再形成闭包。原实现、v1测试/设计/scope/driver与失败root不改、不重跑。

这是精确 Core 创建/交接/cleanup 与合成effect domains的普通验证。项目 Native/P1/Source49 target 调用为0；ordinary validation child单独记实际1，Capture1/DRAIN1自身Native sampler保留。真实source check/use、晚绑定两写窗口、完整Native等价、actual entry/full context、P1/source physical复用和完整F资源审查继续OPEN；所有原 gates 为false，NFC12沿用已有证据，新增模拟跨度0h。
