"""SPU 秘密置换适配；目标位置为零基下标，输入置换须为双射。"""
import jax
import jax.numpy as jnp
from .._validation import _columns

def apply_perm(perm, values):
    """输出满足 out[perm[i]]=values[i]；列元组可共用一次排序。

    返回结构与 values 的单列/多列形式对应，多列统一返回元组。
    不使用宿主端秘密索引，也不重构 perm。
    """
    columns = _columns(values)
    _columns((perm,) + columns)
    if perm.shape[0] == 0:
        result = columns
    else:
        result = tuple(jax.lax.sort(
            (perm,) + columns, num_keys=1, is_stable=True)[1:])
    return result if isinstance(values, (tuple, list)) else result[0]
