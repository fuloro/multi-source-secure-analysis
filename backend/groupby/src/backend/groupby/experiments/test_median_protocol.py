"""合成数据中显式验证秩与固定分母，防止数值相同掩盖奇偶泄露。"""
import sys
from pathlib import Path
import unittest
import numpy as np
import spu
from spu.utils.simulation import Simulator, sim_jax
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'src'))
from backend.groupby.algorithm.common import groupby_common
from backend.groupby.algorithm.aggregates.count import count_from_common
from backend.groupby.algorithm.aggregates.median import groupby_median
from backend.groupby.algorithm.protocols.ranks import ranks_from_common


class MedianProtocolTest(unittest.TestCase):
    def test_ranks_and_constant_scale(self):
        def kernel(k,v,b):
            c=groupby_common(k,v,b,sort_values=True)
            return c,ranks_from_common(c,count_from_common(c)),groupby_median(k,v,b)
        run=sim_jax(Simulator.simple(3,spu.ProtocolKind.ABY3,spu.FieldType.FM64),kernel)
        keys=[key for key in range(6) for _ in range(key+1)]+[0,4]
        vals=[(i%7)-3 for i in range(21)]+[99,99]
        bits=[1]*21+[0,0]
        c,(a,d),out=run(*(np.array(x,np.int32) for x in (keys,vals,bits)))
        np.testing.assert_array_equal(a,[i for n in range(1,7) for i in range(n)]+[0,0])
        np.testing.assert_array_equal(d,[i for n in range(1,7) for i in reversed(range(n))]+[0,0])
        np.testing.assert_array_equal(out[2],np.full(23,2,np.int32))
        # 相同中位数的奇数组和偶数组都返回相同分子与分母。
        same=sim_jax(Simulator.simple(3,spu.ProtocolKind.ABY3,spu.FieldType.FM64),groupby_median)
        k=np.array([1,2,2],np.int32);v=np.array([5,4,6],np.int32)
        result=same(k,v,np.ones(3,np.int32))
        np.testing.assert_array_equal(result[1],[10,10,0])
        np.testing.assert_array_equal(result[2],[2,2,2])

if __name__=='__main__': unittest.main()
