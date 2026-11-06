"""复用共同分组结果计算 SUM；不重构中间数据。"""
import jax
import jax.numpy as jnp
from ..primitives.apply_perm import apply_perm


def sum_from_common(common):
    if common.values_grouped.shape[0] == 0:
        return common.values_grouped
    prefix = jax.lax.associative_scan(jnp.add, common.values_grouped)
    selected = jnp.where(common.end_flags != 0, prefix, prefix[-1])
    cumulative = apply_perm(common.output_perm, selected)
    previous = jnp.concatenate((jnp.zeros((1,), dtype=jnp.int32), cumulative[:-1]))
    return jnp.where(common.valid_out != 0, cumulative - previous, 0)


def groupby_sum(keys, values, valid):
    from ..common import groupby_common
    c = groupby_common(keys, values, valid)
    return c.keys_out, sum_from_common(c), c.valid_out
