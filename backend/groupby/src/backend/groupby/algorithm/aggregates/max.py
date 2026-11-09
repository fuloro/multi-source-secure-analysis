"""MAX：Protocol 4.6 组尾选择与置换；from_common 要求组内数值升序。"""
import jax.numpy as jnp
from ..common import groupby_common
from ..primitives.apply_perm import apply_perm
from ..primitives.gen_perm import gen_perm


def max_from_common(c):
    if c.values_grouped.shape[0] == 0:
        return c.values_grouped
    running = c.values_grouped  # Protocol 4.6：组内升序后，末尾即最大值。
    return apply_perm(c.output_perm, jnp.where(c.end_flags != 0, running, 0))


def groupby_max(keys, values, valid):
    c = groupby_common(keys, values, valid, sort_values=True)
    return c.keys_out, max_from_common(c), c.valid_out
