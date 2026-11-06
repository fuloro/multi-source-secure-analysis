# 秘密置换接口与聚合方法分工

## 本次实现

代码：`src/backend/groupby/algorithm/permutation.py`。
在 SPU 编译后的内核中调用这些函数，不能先在宿主 Python 中计算秘密键的置换。
接口均使用 int32 一维列；多列通过公开长度的元组传入。

```python
perm = gen_perm((1 - valid, keys))
sorted_keys, sorted_values, sorted_valid = apply_perm(perm, (keys, values, valid))
original_values = apply_inv(perm, sorted_values)
```

这是可在同一 MPC 内核中执行的调用示意，不会自动启动运行时，也不会公开结果。
列长度 N 公开，输入键和置换保持秘密共享。空输入依据公开形状直接返回。
`perm[i]` 是原行 i 的目标位置，使用零基下标；例如 `[2,1,1]` 的置换为 `[2,0,1]`。
调用方必须保证传入的置换是 `0..N-1` 的双射；本接口不通过公开秘密置换来验证这一点。
由 `gen_perm` 产生的置换满足该前提。无效或恶意构造的置换不在接口保证范围内。

## 来源与实现差异

来源：[论文 Functionality 2.1](https://eprint.iacr.org/2024/141.pdf)。
本次通过论文搜索索引核对功能定义，未重新获取完整 PDF。

| 论文接口 | 本地接口 | 实现方法 |
| --- | --- | --- |
| GenPerm | `gen_perm` | 按键及原位置排序得到来源位置，再按来源位置排序生成目标位置 |
| ApplyPerm | `apply_perm` | 将秘密目标位置作为排序键，携带各载荷列一起排序 |
| ApplyInv | `apply_inv` | 先排列位置向量构造逆映射，再应用逆映射 |

原位置被显式作为最终排序键，确保重复键的稳定顺序。
`gen_perm` 调用两次 `lax.sort`，`apply_perm` 一次，`apply_inv` 两次。
这些是源码调用次数，不是通信轮数。具体执行成本取决于 SPU 编译与底层排序实现。
本方案只适配论文的接口语义，不复现其引用的专用置换协议，
不能声称 ApplyPerm 为常数通信轮，也不能继承恶意安全证明。
当前使用 ABY3 半诚实运行环境。复用置换并不保证比直接携带多列排序更快。

原分段扫描实现保留在 `g_sum_baseline.py`。各聚合方法已拆到独立文件；
`g_common.py` 使用我们的置换接口，`g_sum.py` 通过 `sum_from_common.py`
执行前缀和、置换和差分。详见 [共同分组与 SUM 映射](groupby-common.zh.md)。

## 对新增方法的评估

| 方法 | 建议优先级 | 语义或接口要点 |
| --- | --- | --- |
| `groupby_count` | 当前阶段 | COUNT(*) 只计有效行，实际不需要 values；若保留参数，应说明统一接口用途 |
| `groupby_mean` | 后续扩展 | 需要 SUM/COUNT；先决定返回精确分子分母还是定点数，不应静默转为浮点数 |
| `groupby_max` / `groupby_min` | 后续扩展 | 必须用有效位处理填充，不能以零替代所有无效候选值 |
| `groupby_median` | 后续扩展 | 需组内数值排序及奇偶组大小约定，不能直接套用 SUM 内核 |
| `groupby_common` | 已实现的共享模块 | 提供排序数据、组末尾标志、输出置换和固定容量键/有效位，避免各聚合重复分组 |

这些聚合种类与论文讨论方向一致，但不等于每个方法都是当前必需交付。
建议把聚合、共享分组预处理、置换分成模块；无需把所有原语写在 `g_sum.py` 中。

## 验证

```sh
.venv311/bin/python src/backend/groupby/experiments/test_permutation.py
.venv311/bin/python src/backend/groupby/experiments/demo_sum.py
```

置换测试包含多键、重复键稳定性、负值及 int32 极值、单行、空输入、
固定种子随机数据，以及三元素全部六种置换的正向和逆向验证。
非空测试通过 SPU ABY3/FM64 执行；空形状和参数检查在宿主端完成。
测试中的明文排序/索引仅用于独立参考答案。
模拟器有意重构合成数据的置换供验证，不代表实际服务允许公开置换。
