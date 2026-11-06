"""Protocols 4.12/4.14：COUNT、逆置换、前缀/后缀和构造组内秩。"""
import jax
import jax.numpy as jnp
from ..primitives.apply_inv import apply_inv


def ranks_from_common(c, counts):
    n = c.keys_grouped.shape[0]
    if n == 0:
        return counts, counts
    endpoints = apply_inv(c.output_perm, counts)
    prefix = jax.lax.associative_scan(jnp.add, endpoints)
    before = jnp.concatenate((jnp.zeros((1,), dtype=jnp.int32), prefix[:-1]))
    positions = jnp.arange(n, dtype=jnp.int32)
    ascending = positions - before
    next_counts = jnp.concatenate((counts[1:], jnp.zeros((1,), dtype=jnp.int32)))
    shifted = apply_inv(c.output_perm, next_counts)
    suffix = jax.lax.associative_scan(jnp.add, shifted, reverse=True)
    # 论文 m 为真实行数；本项目有秘密填充，使用秘密有效行数。
    total = jnp.sum(c.valid_grouped, dtype=jnp.int32)
    descending = total - 1 - positions - suffix
    return (jnp.where(c.valid_grouped != 0, ascending, 0),
            jnp.where(c.valid_grouped != 0, descending, 0))
