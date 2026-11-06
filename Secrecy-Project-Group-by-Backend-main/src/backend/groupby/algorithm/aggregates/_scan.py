"""分组顺序上的扫描；只按公开形状分支。"""
import jax
import jax.numpy as jnp


def segmented(values, starts, op):
    def combine(left, right):
        a, fa = left
        b, fb = right
        return jnp.where(fb, b, op(a, b)), fa | fb
    return jax.lax.associative_scan(combine, (values, starts))[0]


def starts(common):
    return jnp.concatenate((jnp.ones((1,), dtype=jnp.bool_),
        (common.keys_grouped[1:] != common.keys_grouped[:-1]) |
        (common.valid_grouped[1:] != common.valid_grouped[:-1])))
