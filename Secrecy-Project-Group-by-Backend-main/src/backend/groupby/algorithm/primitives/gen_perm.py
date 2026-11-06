"""SPU 秘密置换适配；目标位置为零基下标，输入置换须为双射。"""
import jax
import jax.numpy as jnp
from .._validation import _columns

def gen_perm(keys):
    """稳定升序排序的目标位置向量；多键按传入列顺序作字典序比较。

    示例：keys=[2,1,1] -> perm=[2,0,1]。
    显式追加原位置作为最后一个排序键，保证重复键稳定。
    两次排序：先得到来源位置，再恢复原行顺序以生成目标位置。
    """
    keys = _columns(keys)
    positions = jnp.arange(keys[0].shape[0], dtype=jnp.int32)
    if positions.shape[0] == 0:
        return positions
    sources = jax.lax.sort(
        keys + (positions,), num_keys=len(keys) + 1, is_stable=True)[-1]
    return jax.lax.sort((sources, positions), num_keys=1, is_stable=True)[1]
