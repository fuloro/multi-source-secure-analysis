"""SPU 秘密置换适配；目标位置为零基下标，输入置换须为双射。"""
import jax
import jax.numpy as jnp
from .._validation import _columns
from .apply_perm import apply_perm

def apply_inv(perm, values):
    """应用逆置换；apply_inv(p, apply_perm(p, x)) == x。

    先以同一秘密置换排列公开位置，得到逆置换的目标位置，再应用它。
    """
    _columns(perm)
    positions = jnp.arange(perm.shape[0], dtype=jnp.int32)
    inverse = apply_perm(perm, positions)
    return apply_perm(inverse, values)
