# C：import policy v1 两次失败冻结

2026-10-26，DRAFT_NONAUTHORITATIVE。起点7e091fc3，接续wire completion。v1仅开发依赖导入guard，原runtime v2的UNDECIDED/admissible=false保持；尚未运行真实cold child，也没有saved/terminal成功、runtime lease或角色能力。

v1 root为results/tables/staged_rts24_saved_fresh_import_policy_v1_non_authoritative，38个文件保留。collection/pytest_a/collection_retry/pytest_retry原stdout/stderr/exit、source/helper snapshot和两版admission均保全。首次pytest_a因image把canonical bytes直接放入JSON而失败，7.811273s；修复后pytest_retry 31项通过、关闭正例失败，7.8745911s，仍不计整个35节点通过。

代码检查和环境metadata已定位第二个原因：compute python.exe与Lib/subprocess.py的st_nlink均为2，NumPy utils为1；guard调用通用read默认要求单链接，导致external bookend拒绝。v1 policy没有显式外部hardlink策略，当前不是生产运行可用版本。原P1/Source读取规则与所有运行/科学/资源/正式门禁保持。

本轮原账已用static79.36616/120、pytest339.0513453/420，总418.4175053/540，剩余121.5824947s。v1冻结后改用独立v2 root明确固定外部文件的hardlink策略；不覆盖v1字节，不重置原540s，不把v1失败/部分通过计为新版本通过。v1上限仍64files/4MiB；v2另有64files/4MiB，组合上限128/8MiB，原wire root的204/16MiB保持。
