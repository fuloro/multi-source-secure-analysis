# 聚合接口与目录结构

本文记录聚合接口、目录结构及已知实现差异。

```text
algorithm/
  common.py                 共用的秘密分组预处理
  aggregates/               sum/count/mean/min/max/median，各自独立文件
    _scan.py                分段扫描辅助函数
  primitives/               gen_perm/apply_perm/apply_inv
  baselines/segmented_sum.py 原始 SUM 对照基线
  g_*.py、permutation.py     兼容旧导入路径
```

统一入口：`from backend.groupby.algorithm import groupby_sum, groupby_count, groupby_mean, groupby_min, groupby_max, groupby_median`。
各函数输入均为 `(keys, values, valid)` 的等长 int32 向量。
COUNT(*) 保留 values 参数以统一入口，但只计有效行。

| 操作 | 返回值 | 计算方式 |
| --- | --- | --- |
| SUM | keys, sums, valid | 前缀和、输出置换、差分 |
| COUNT | keys, counts, valid | 协议 4.2：取有效组末的一基位置，否则取公开容量 N；稳定压紧、相邻作差后用 valid_out 清零填充 |
| MIN / MAX | keys, extrema, valid | 按键和值排序，选择组首/组尾，应用相应输出置换 |
| MEAN | keys, numerator, denominator, valid | 精确 SUM/COUNT，不作除法或约分 |
| MEDIAN | keys, numerator, denominator, valid | 按论文秩协议及 FindZeroOrOne 选择两个中间值 |

MEDIAN 统一返回两倍中位数及分母 2，不公开奇偶性。
groupby_mean 的分母为组大小。若只需均值，§4.3 的适配入口 groupby_mean_only 在共享状态下以固定轮数求最大公约数并用整数二进制长除法约分，输出精确最简分数；零为 0/1。两种入口均不公开结果。填充分子为 0；MEAN 填充分母为 1，MEDIAN 所有分母恒为 2；有效位为 0。
所有输出保持输入容量。小数转换只能在结果授权公开后进行。

`sum_from_common`、`count_from_common`、`mean_from_common`、`min_from_common`、
`max_from_common` 可复用按键和值排序的 common；MIN/MAX 要求 sort_values=True。
根目录的 mean_from_common.py 和 sum_from_common.py 已删除，统一使用 aggregates 下的复用函数。

输入前提：valid 为 0/1，所有输入数值绝对值总和不超过 2147483647。
这是输入方必须保证的范围，不是内核的秘密范围证明。扫描、选值和位置运算保持整数，
不使用秘密宿主索引。直接在 JAX 调用是明文计算，须通过 SPU 执行才能获得 MPC 保护。

当前论文步骤映射、MEDIAN 额外数值界限和所有差异见[次序统计协议说明](order-statistics.zh.md)。

验证命令：`.venv311/bin/python src/backend/groupby/experiments/test_aggregates.py`。
21 组固定与随机案例使用独立 Python 整数/Fraction 参考答案，非空案例在三方 SPU 上执行；
覆盖奇偶中位数、负数、零键、零和、重复键、填充、全部无效、空输入和 int32 边界。
同时保留原置换、common 和医疗保险 SUM 回归测试。
