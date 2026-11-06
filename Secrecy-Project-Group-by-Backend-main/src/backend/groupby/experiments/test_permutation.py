"""合成数据测试：仅此测试允许模拟器重构置换和输出。"""
import itertools
from pathlib import Path
import sys
import unittest

import jax.numpy as jnp
import numpy as np
import spu
from spu.utils.simulation import Simulator, sim_jax

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'src'))
from backend.groupby.algorithm.permutation import gen_perm, apply_perm, apply_inv


def expected_perm(columns):
    order = sorted(range(len(columns[0])), key=lambda i: tuple(int(c[i]) for c in columns))
    destination = [0] * len(order)
    for new, old in enumerate(order):
        destination[old] = new
    return np.array(destination, dtype=np.int32), order


class PermutationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = Simulator.simple(3, spu.ProtocolKind.ABY3, spu.FieldType.FM64)

    def test_generate_apply_inverse_mpc(self):
        def kernel(keys, secondary, values):
            perm = gen_perm((keys, secondary))
            moved = apply_perm(perm, (keys, secondary, values))
            return perm, moved, apply_inv(perm, moved)
        run = sim_jax(self.sim, kernel)
        rng = np.random.default_rng(20261103)
        cases = [([2,1,1], [0,0,0]), ([0], [0]),
                 ([1,1,1,1], [0,0,0,0]),
                 ([3,2,1,0,-1], [0]*5),
                 ([-2147483648,2147483647,0,-1], [0]*4)]
        for n in (3,8,17):
            cases.append((rng.integers(-3,4,n), rng.integers(-2,3,n)))
        for a,b in cases:
            with self.subTest(keys=a):
                k,s = np.array(a,np.int32),np.array(b,np.int32)
                v = np.arange(len(a),dtype=np.int32)*11-20
                want, order = expected_perm((k,s))
                perm, moved, restored = run(k,s,v)
                np.testing.assert_array_equal(perm,want)
                for source,out,back in zip((k,s,v),moved,restored):
                    np.testing.assert_array_equal(out,source[order])
                    np.testing.assert_array_equal(back,source)
                    self.assertEqual(out.dtype,np.int32)

    def test_arbitrary_secret_permutations(self):
        def kernel(p,v):
            moved = apply_perm(p,v)
            return moved,apply_inv(p,moved),apply_inv(p,v)
        run = sim_jax(self.sim,kernel)
        values = np.array([71,-8,0],np.int32)
        for p in itertools.permutations(range(3)):
            p = np.array(p,np.int32)
            expected = np.zeros(3,np.int32)
            expected[p] = values  # 明文参考，不能放入 MPC 内核。
            moved,back,inverse = run(p,values)
            np.testing.assert_array_equal(moved,expected)
            np.testing.assert_array_equal(back,values)
            np.testing.assert_array_equal(inverse,values[p])

    def test_empty_and_public_validation(self):
        empty = jnp.array([],dtype=jnp.int32)
        for value in (gen_perm(empty),apply_perm(empty,empty),apply_inv(empty,empty)):
            self.assertEqual(value.shape,(0,))
            self.assertEqual(value.dtype,jnp.int32)
        with self.assertRaises(ValueError):
            gen_perm(())
        with self.assertRaises(ValueError):
            gen_perm(jnp.zeros((2,2),dtype=jnp.int32))
        with self.assertRaises(TypeError):
            gen_perm(jnp.array([1.0]))
        with self.assertRaises(ValueError):
            apply_perm(jnp.array([0],dtype=jnp.int32),empty)


if __name__ == '__main__':
    unittest.main()
