"""SPU 秘密置换适配；目标位置为零基下标，输入置换须为双射。"""
import jax
import jax.numpy as jnp

def _columns(columns):
    """接受单列或公开长度的列元组；不检查秘密数值。"""
    result = tuple(columns) if isinstance(columns, (tuple, list)) else (columns,)
    if not result:
        raise ValueError('至少需要一列')
    shape = result[0].shape
    if len(shape) != 1 or any(c.shape != shape for c in result):
        raise ValueError('所有列必须为等长一维向量')
    if any(c.dtype != jnp.int32 for c in result):
        raise TypeError('当前置换接口只支持 int32')
    if shape[0] > 2147483647:
        raise ValueError('行数超出 int32 位置范围')
    return result
