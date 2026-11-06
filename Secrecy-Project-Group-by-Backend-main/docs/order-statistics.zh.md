# MIN / MAX / MEDIAN 的论文步骤适配

来源：[论文 §4.4–4.6](https://eprint.iacr.org/2024/141.pdf)，
[同一论文的归档副本](https://www.eprint.mirror.cypherpunks.su/2024/141/1706767899.pdf)。
本轮核对了搜索索引中的协议原文；主站 PDF 直接读取仍返回 403。

| 协议 | 实现 |
| --- | --- |
| 4.6 MAX | 键和值排序后取组尾，以 common 的输出置换压紧 |
| 4.8 MIN | 从末尾标志导出组首标志，取组首值，以新置换压紧 |
| 4.10 MEDIAN | rank+ / rank− 相减，两次 FindZeroOrOne，结果相加 |
| 4.12 rank+ | COUNT 逆置换回组末尾，前缀和后从位置减去前面各组长度 |
| 4.14 rank− | 输出计数左移一格，逆置换、后缀和，计算反向秩 |
| 4.16 FindZeroOrOne | 判断差值为 0 或 1，屏蔽其他行，新建置换压紧 |

## 接口与数值变化

MEDIAN 返回 `(keys, twice_median, denominator, valid)`，所有位置 denominator 恒为 2。
旧版的奇数组分母 1、偶数组分母 2 会额外暴露组大小奇偶，故不再使用。
即使中位数为整数，也不约分。填充结果为 0/2。
MEDIAN 额外要求输入值绝对值不超过 1073741823，防止奇数组中间值翻倍溢出 int32。
其余聚合继续遵守已有整数范围约定；这些是输入前提，不是秘密范围验证协议。

MIN/MAX 的 from_common 必须接收 `groupby_common(..., sort_values=True)` 的结果。
公共 groupby_min/groupby_max 入口已自动设置该选项。
不能将仅按键排序的 common 用于组首/组尾取极值。

## 显式差异

- 使用同一份按键和值排序的 common 和计数，避免 median 的两个秩重复预处理。
- COUNT 采用协议 4.2 的位置差分，并以输出有效位屏蔽填充。
- 有效位屏蔽填充；反向秩以秘密有效行数替代论文未填充输入的 m。
- FindZeroOrOne 清除 int32 最低位后与零比较，等价于协议 4.16 的截断判定。
- FindZeroOrOne 是内部函数，要求每组恰好一个匹配；不对任意外部输入提供恶意合法性检查。
- GenPerm/ApplyPerm/ApplyInv 仍由 SPU 排序封装，不继承论文的专用协议通信复杂度。
- 使用半诚实 ABY3，不继承恶意安全证明。

## 文件清理与测试

已删除 algorithm 根目录的 sum_from_common.py 和 mean_from_common.py 转发文件。
复用入口统一为 `aggregates.sum.sum_from_common`、`aggregates.mean.mean_from_common`。
相关测试已迁移。原扫描算法保存在 baselines/scan_min.py、scan_max.py、scan_median.py，
仅供对照；旧中位数接口不用于默认输出。

`test_median_protocol.py` 核对 1–6 行组的两个秩，以及奇偶组固定分母。
`test_aggregates.py` 使用独立 Python 整数/Fraction 参考，覆盖全部聚合。
测试允许模拟器公开合成中间量，实际使用时不能公开 ranks、边界或置换。
