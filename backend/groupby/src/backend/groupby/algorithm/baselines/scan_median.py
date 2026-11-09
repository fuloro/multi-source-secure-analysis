"""排序/双向扫描中位数适配，非论文专用 MEDIAN 协议的逐步复现。

偶数组返回两个中间值之和 / 2，奇数组返回中间值 / 1；不约分。
"""
import jax.numpy as jnp
from ..common import groupby_common
from ..primitives.apply_perm import apply_perm
from ..aggregates._scan import segmented, starts
from ..aggregates.sum import sum_from_common


def groupby_median(keys, values, valid):
    c = groupby_common(keys, values, valid, sort_values=True)
    if keys.shape[0] == 0:
        return c.keys_out, c.values_grouped, c.valid_out, c.valid_out
    ones = jnp.ones_like(c.valid_grouped)
    rank = segmented(ones, starts(c), jnp.add) - 1
    # 反向扫描从原分组末尾开始；最后一个填充段也必须有起点。
    reverse_starts = jnp.concatenate((jnp.ones((1,), dtype=jnp.bool_), starts(c)[1:][::-1]))
    remaining = segmented(ones, reverse_starts, jnp.add)[::-1]
    size = rank + remaining
    lower, upper = (size - 1) // 2, size // 2
    selected = (c.valid_grouped != 0) & ((rank == lower) | (rank == upper))
    numerator = sum_from_common(c._replace(values_grouped=jnp.where(selected, c.values_grouped, 0)))
    denominators = jnp.where(c.end_flags != 0, jnp.where(size % 2 == 0, 2, 1), 1)
    return c.keys_out, numerator, apply_perm(c.output_perm, denominators), c.valid_out
