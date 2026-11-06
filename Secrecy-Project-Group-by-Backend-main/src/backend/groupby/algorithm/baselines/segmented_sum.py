"""原始分段扫描基线，保留用于对照。"""
import jax
import jax.numpy as jnp

def groupby_sum(keys, values, valid):
    if keys.ndim != 1 or keys.shape != values.shape or keys.shape != valid.shape:
        raise ValueError('输入必须为等长一维向量')
    if any(x.dtype != jnp.int32 for x in (keys, values, valid)):
        raise TypeError('输入必须为 int32')
    if keys.shape[0] == 0:
        return keys, values, valid
    invalid, keys, values = jax.lax.sort(
        (1 - valid, keys, values), num_keys=2, is_stable=True)
    valid = 1 - invalid
    starts = jnp.concatenate((jnp.ones((1,), dtype=jnp.bool_),
                              (keys[1:] != keys[:-1]) | (valid[1:] != valid[:-1])))
    def combine(left, right):
        a, flag_a = left
        b, flag_b = right
        return jnp.where(flag_b, b, a + b), flag_a | flag_b
    sums, _ = jax.lax.associative_scan(
        combine, (jnp.where(valid != 0, values, 0), starts))
    ends = (valid != 0) & jnp.concatenate((
        (keys[:-1] != keys[1:]) | (valid[1:] == 0),
        jnp.ones((1,), dtype=jnp.bool_)))
    masked_keys = jnp.where(ends, keys, 0)
    masked_sums = jnp.where(ends, sums, 0)
    invalid, out_keys, out_sums = jax.lax.sort(
        ((~ends).astype(jnp.int32), masked_keys, masked_sums),
        num_keys=2, is_stable=True)
    return out_keys, out_sums, 1 - invalid
