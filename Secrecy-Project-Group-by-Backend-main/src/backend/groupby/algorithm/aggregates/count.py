"""COUNT(*)：只统计有效行，保留 values 参数以兼容统一入口。"""
import jax.numpy as jnp
from ..common import groupby_common
from ..primitives.apply_perm import apply_perm


def count_from_common(common):
    """Protocol 4.2. Valid rows sort first, so endpoint positions count real rows."""
    n = common.end_flags.shape[0]
    if n == 0:
        return common.end_flags
    positions = jnp.arange(n, dtype=jnp.int32) + 1
    selected = jnp.where(common.end_flags != 0, positions, n)
    endpoints = apply_perm(common.output_perm, selected)
    # With padded input the last real endpoint can be smaller than n.
    counts = jnp.diff(endpoints, prepend=jnp.zeros((1,), dtype=jnp.int32))
    return jnp.where(common.valid_out != 0, counts, 0)


def groupby_count(keys, values, valid):
    c = groupby_common(keys, values, valid)
    return c.keys_out, count_from_common(c), c.valid_out
