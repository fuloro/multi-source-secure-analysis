"""MIN：Protocol 4.8 组首选择与置换；from_common 要求组内数值升序。"""
import jax.numpy as jnp
from ..common import groupby_common
from ..primitives.apply_perm import apply_perm
from ..primitives.gen_perm import gen_perm


def min_from_common(c):
    if c.values_grouped.shape[0] == 0:
        return c.values_grouped
    first = (c.valid_grouped != 0) & jnp.concatenate((
        jnp.ones((1,), dtype=jnp.bool_), c.end_flags[:-1] != 0))
    perm = gen_perm(1 - first.astype(jnp.int32))
    return apply_perm(perm, jnp.where(first, c.values_grouped, 0))


def groupby_min(keys, values, valid):
    c = groupby_common(keys, values, valid, sort_values=True)
    return c.keys_out, min_from_common(c), c.valid_out
