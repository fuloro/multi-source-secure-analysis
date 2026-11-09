"""合成输入专用：重构共同分组状态以验证论文步骤映射。"""
from pathlib import Path
import sys
import unittest
import numpy as np
import spu
from spu.utils.simulation import Simulator, sim_jax
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'src'))
from backend.groupby.algorithm.g_common import groupby_common
from backend.groupby.algorithm.aggregates.sum import sum_from_common
from backend.groupby.algorithm.g_sum import groupby_sum
from backend.groupby.algorithm.g_sum_baseline import groupby_sum as baseline


class CommonTest(unittest.TestCase):
    def test_common_fields_and_reuse(self):
        sim = Simulator.simple(3,spu.ProtocolKind.ABY3,spu.FieldType.FM64)
        for sort_values in (False,True):
            def kernel(k,v,b):
                c=groupby_common(k,v,b,sort_values=sort_values)
                return c,sum_from_common(c),baseline(k,v,b)
            run=sim_jax(sim,kernel)
            for k,v,b in [([2,0,2,-1,0],[3,9,-3,7,5],[1,0,1,1,1]),
                          ([1,1],[5,-5],[1,1]),([0,0],[7,8],[0,0]),
                          ([0],[0],[1])]:
                arrays=[np.array(x,np.int32) for x in (k,v,b)]
                c,s,old=run(*arrays)
                order=sorted(range(len(k)),key=lambda i:(1-b[i],k[i],v[i]) if sort_values else (1-b[i],k[i]))
                kg=[k[i] for i in order];active=[b[i] for i in order]
                vg=[v[i] if b[i] else 0 for i in order]
                ends=[int(active[i] and (i==len(k)-1 or not active[i+1] or kg[i]!=kg[i+1])) for i in range(len(k))]
                out_order=sorted(range(len(k)),key=lambda i:1-ends[i])
                dest=[0]*len(k)
                for new,original in enumerate(out_order): dest[original]=new
                masked=[key if end else 0 for key,end in zip(kg,ends)]
                expected=(kg,vg,ends,masked,dest,[masked[i] for i in out_order],active,[ends[i] for i in out_order])
                for a,e in zip(c,expected): np.testing.assert_array_equal(a,e)
                for a,e in zip((c.keys_out,s,c.valid_out),old): np.testing.assert_array_equal(a,e)

    def test_empty(self):
        x=np.array([],np.int32)
        c=groupby_common(x,x,x)
        for a in c: self.assertEqual(a.shape,(0,))
        for a in groupby_sum(x,x,x): self.assertEqual(a.shape,(0,))


if __name__=='__main__': unittest.main()
