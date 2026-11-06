"""Protocol 4.10 适配：返回两倍中位数及固定分母 2，不公开组大小奇偶。

额外输入范围：每个值绝对值 <= 1073741823，保证奇数组中间值翻倍不溢出。
"""
import jax.numpy as jnp
from ..common import groupby_common
from .count import count_from_common
from ..protocols.ranks import ranks_from_common
from ..protocols.find_zero_or_one import find_zero_or_one


def groupby_median(keys, values, valid):
    c = groupby_common(keys, values, valid, sort_values=True)
    counts = count_from_common(c)
    a, d = ranks_from_common(c, counts)
    upper = find_zero_or_one(c, a - d)
    lower = find_zero_or_one(c, d - a)
    return c.keys_out, upper + lower, jnp.full_like(c.valid_out, 2), c.valid_out
