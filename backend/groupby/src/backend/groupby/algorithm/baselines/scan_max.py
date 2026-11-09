"""MAX：分段最大值，不以零作哨兵；属于扫描式适配。"""
import jax.numpy as jnp
from ..common import groupby_common
from ..primitives.apply_perm import apply_perm
from ..aggregates._scan import segmented, starts


def max_from_common(c):
    if c.values_grouped.shape[0] == 0:
        return c.values_grouped
    running = segmented(c.values_grouped, starts(c), jnp.maximum)
    return apply_perm(c.output_perm, jnp.where(c.end_flags != 0, running, 0))


def groupby_max(keys, values, valid):
    c = groupby_common(keys, values, valid)
    return c.keys_out, max_from_common(c), c.valid_out
