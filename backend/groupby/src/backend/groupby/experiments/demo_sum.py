"""仅用于合成数据的模拟实验；Simulator 会重构返回结果。"""
import csv
import json
from pathlib import Path
import sys
import numpy as np
import spu
from spu.utils.simulation import Simulator, sim_jax

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
from backend.groupby.algorithm.g_sum import groupby_sum


def reference(keys, values, valid):
    groups = {}
    for key, value, bit in zip(keys, values, valid):
        if bit:
            groups[int(key)] = groups.get(int(key), 0) + int(value)
    rows = sorted(groups.items())
    n = len(keys)
    return tuple(np.array(x, dtype=np.int32) for x in (
        [k for k, _ in rows] + [0] * (n-len(rows)),
        [v for _, v in rows] + [0] * (n-len(rows)),
        [1] * len(rows) + [0] * (n-len(rows))))


def main():
    run = sim_jax(Simulator.simple(3, spu.ProtocolKind.ABY3, spu.FieldType.FM64), groupby_sum)
    def check(k, v, b):
        if any(bit not in (0, 1) for bit in b):
            raise ValueError('valid 必须为比特')
        if sum(abs(int(x)) for x in v) > np.iinfo(np.int32).max:
            raise ValueError('数值超出安全累加范围')
        arrays = tuple(np.asarray(x, dtype=np.int32) for x in (k, v, b))
        # 公开的空形状无需启动 MPC。
        actual = run(*arrays) if len(k) else groupby_sum(*arrays)
        for a, e in zip(actual, reference(*arrays)):
            np.testing.assert_array_equal(a, e)
            assert a.dtype == np.int32
        return actual
    cases = [([], [], []), ([0], [0], [1]), ([1,1], [5,6], [0,0]),
             ([0,-1,0,2], [5,-3,-5,9], [1,1,1,1]),
             ([1,1,2], [10,999,-2], [1,0,1]),
             ([1,1], [2147483646,1], [1,1])]
    for case in cases:
        check(*case)
    rng = np.random.default_rng(20261103)
    for n in (1,3,8,17):
        for _ in range(3):
            check(rng.integers(-3,4,n), rng.integers(-100,101,n), rng.integers(0,2,n))
    folder = ROOT / 'test/medical_insurance/demo'
    config = json.loads((folder / 'public_config.json').read_text())
    with (folder / 'reference_only/expected_join.csv').open() as f:
        rows = list(csv.DictReader(f))
    n = config['right_capacity']
    assert len(rows) <= n
    k = [int(r['group_code']) for r in rows] + [0]*(n-len(rows))
    v = [int(r['amount_cent']) for r in rows] + [0]*(n-len(rows))
    result = check(k, v, [1]*len(rows)+[0]*(n-len(rows)))
    obtained = {int(k): int(s) for k,s,b in zip(*result) if b}
    expected = json.loads((folder / 'reference_only/expected.json').read_text())
    assert obtained == {g['group']: g['sum_cent'] for g in expected['groups']}
    print('18 个边界/随机测试及医疗保险示例通过；SPU ABY3/FM64。')
    print('合成数据模拟结果（分）：', obtained)


if __name__ == '__main__':
    main()
