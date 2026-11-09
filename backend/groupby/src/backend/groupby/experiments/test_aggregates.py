"""合成测试：以 Python 整数和 Fraction 独立核对所有聚合。"""
import sys
from pathlib import Path
from fractions import Fraction
import unittest
import numpy as np
import spu
from spu.utils.simulation import Simulator, sim_jax
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'src'))
from backend.groupby.algorithm import (groupby_count,groupby_sum,groupby_mean,groupby_min,groupby_max,groupby_median)
from backend.groupby.algorithm import groupby_mean_only
from backend.groupby.algorithm.common import groupby_common
from backend.groupby.algorithm.aggregates.mean import mean_from_common


class AggregatesTest(unittest.TestCase):
    def test_against_python(self):
        functions=(groupby_count,groupby_sum,groupby_mean,groupby_min,groupby_max,groupby_median)
        def kernel(k,v,b):return tuple(fn(k,v,b) for fn in functions)
        run=sim_jax(Simulator.simple(3,spu.ProtocolKind.ABY3,spu.FieldType.FM64),kernel)
        cases=[([],[],[]),([0],[0],[1]),([1,1],[3,4],[1,1]),
               ([1,1],[-4,-3],[1,1]),([1,1,1],[5,-5,0],[1,1,1]),
               ([0,0,2,-1],[10,999,-2,7],[1,0,1,1]),
               ([1,1],[5,8],[0,0]),([1,1],[1073741823,1],[1,1]),
               ([-2147483648,2147483647],[-1073741823,0],[1,1])]
        rng=np.random.default_rng(20261104)
        for n in (2,5,9,16):
            for _ in range(3):cases.append((rng.integers(-3,4,n),rng.integers(-100,101,n),rng.integers(0,2,n)))
        for k,v,b in cases:
            arrays=tuple(np.array(x,np.int32) for x in (k,v,b))
            outputs=run(*arrays) if len(k) else kernel(*arrays)
            groups={}
            for key,val,bit in zip(k,v,b):
                if bit:groups.setdefault(int(key),[]).append(int(val))
            expected=[[] for _ in functions]
            for key in sorted(groups):
                a=sorted(groups[key]);n=len(a)
                med=Fraction(a[n//2],1) if n%2 else Fraction(a[n//2-1]+a[n//2],2)
                for dest,val in zip(expected,(n,sum(a),Fraction(sum(a),n),min(a),max(a),med)):dest.append(val)
            for fn,out,want in zip(functions,outputs,expected):
                with self.subTest(function=fn.__name__,keys=k):
                    np.testing.assert_array_equal(out[0],sorted(groups)+[0]*(len(k)-len(groups)))
                    np.testing.assert_array_equal(out[-1],[1]*len(groups)+[0]*(len(k)-len(groups)))
                    for x in out:self.assertEqual(x.dtype,np.int32)
                    if len(out)==4:
                        self.assertTrue(np.all(out[2]>0))
                        actual=[Fraction(int(a),int(d)) for a,d in zip(out[1],out[2])]
                    else:actual=list(map(int,out[1]))
                    self.assertEqual(actual,want+[0]*(len(k)-len(groups)))

    def test_mean_only_canonical_pairs(self):
        simulator = Simulator.simple(3, spu.ProtocolKind.ABY3, spu.FieldType.FM64)
        run = sim_jax(simulator, groupby_mean_only)
        cases = [
            ([], [], []),
            ([0, 0], [8, -2], [0, 0]),
            ([-1, 2, 2, 2, 2, -1, 2], [-3, -3, -3, 0, 0, 0, 99], [1]*6 + [0]),
            ([0, 0, 1], [-2147483647, 0, 0], [1, 1, 1]),
            ([1]*3, [2147483646, 0, 0], [1]*3),
            ([0]*26, [-42] + [0]*25, [1]*26),
        ]
        for keys, values, valid in cases:
            arrays = tuple(np.array(x, np.int32) for x in (keys, values, valid))
            out = run(*arrays) if keys else groupby_mean_only(*arrays)
            groups = {}
            for k, v, bit in zip(keys, values, valid):
                if bit:
                    groups.setdefault(k, []).append(v)
            means = [Fraction(sum(groups[k]), len(groups[k])) for k in sorted(groups)]
            padding = len(keys) - len(groups)
            np.testing.assert_array_equal(out[0], sorted(groups) + [0]*padding)
            np.testing.assert_array_equal(out[1], [m.numerator for m in means] + [0]*padding)
            np.testing.assert_array_equal(out[2], [m.denominator for m in means] + [1]*padding)
            np.testing.assert_array_equal(out[3], [1]*len(groups) + [0]*padding)

    def test_common_mean_compatibility(self):
        from backend.groupby.algorithm.aggregates.mean import groupby_mean as direct
        a=np.array([1,1],np.int32);v=np.array([2,3],np.int32)
        c=groupby_common(a,v,a)
        for x,y in zip(direct(a,v,a),mean_from_common(c)):np.testing.assert_array_equal(x,y)

if __name__=='__main__':unittest.main()
