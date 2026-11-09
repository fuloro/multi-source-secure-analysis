"""Protocol 4.1 的 SPU 功能适配，增加秘密有效位以支持 JOIN 填充。

所有返回字段均为 MPC 内部数据，不能直接作为授权公开结果。
sort_values 是公开的编译期选项；SUM/COUNT 无需按数值排序。
"""
from typing import NamedTuple
import jax.numpy as jnp
from ._validation import _columns
from .primitives.gen_perm import gen_perm
from .primitives.apply_perm import apply_perm


class GroupByCommon(NamedTuple):
    keys_grouped: object
    values_grouped: object
    end_flags: object
    keys_masked: object
    output_perm: object
    keys_out: object
    valid_grouped: object
    valid_out: object


def groupby_common(keys, values, valid, *, sort_values=False):
    _columns((keys, values, valid))
    if keys.shape[0] == 0:
        return GroupByCommon(keys, values, valid, keys, valid, keys, valid, valid)
    order_keys = (1 - valid, keys, values) if sort_values else (1 - valid, keys)
    perm = gen_perm(order_keys)
    kg, vg, active = apply_perm(perm, (keys, values, valid))
    # 无效输入行不参与聚合；不能把合法键 0 当成 NULL。
    vg = jnp.where(active != 0, vg, 0)
    ends = ((active != 0) & jnp.concatenate((
        (kg[:-1] != kg[1:]) | (active[1:] == 0),
        jnp.ones((1,), dtype=jnp.bool_)))).astype(jnp.int32)
    masked = jnp.where(ends != 0, kg, 0)
    # 稳定地将 e=1 移到前部，保留组键顺序。
    output_perm = gen_perm(1 - ends)
    keys_out, valid_out = apply_perm(output_perm, (masked, ends))
    return GroupByCommon(kg, vg, ends, masked, output_perm, keys_out, active, valid_out)
