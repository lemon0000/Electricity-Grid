# 冻结输入校验的单次只读调用计数

2026-10-28，DRAFT_NONAUTHORITATIVE。NFC v3的14项test body已输出OK，但子进程在最终report前被timeout终止；stdout仅29帧，不能称整个检查通过。拒绝checkpoint为当前账本端点，0 cold。原包已用13.555978000011237s，累计775.8277461000646s，不接受34条；单测累计7.278094400011469/8s，不再启动单测child。

本补充只回答冻结check(reg)显式Path.read_bytes重复了多少次/多少bytes。不执行测试、adapter、模型、solver、P1或cold，不采用缓存或改变冻结实现。唯一metadata检查≤2s，原30s/static22/unit8预算继续累计；无child。临时包装Path.read_bytes，正常调用原方法并仅记录absolute path/bytes/SHA，finally恢复原方法。最多8192次显式读取、2048个路径、1GiB计数字节；不记录或认证importlib/native隐式I/O和总系统调用，也不代表全部墙钟开销。

完整有序journal以canonical JSON压缩保存，保存raw/compressed pins，进行有界decompress/重计；保存路径基数、重复次数与字节、每路径读取次数分布、当前pin是否跨重复读取一致。该观测不能作为替换expected truth、跨phase缓存或减少fresh bookend的授权。后续若优化，应从固定expected pins集合构造依赖DAG，每phase独立fresh核每个唯一输入，并证明旧特殊断言未丢失。

输出仅新独立driver与inspection，共≤2文件/262144+65536B；原20个失败包文件全保留，组合≤30文件/4MiB。所有失败保留费用，最终记录create-only；source/input执行前pins及原checkpoint绑定，root唯一writer。编辑/审查/Git和最终记录写入沿原账口径不计capture；无scientific/resource/formal/run authority。
