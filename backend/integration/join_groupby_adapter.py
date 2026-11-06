"""Synthetic-only integration of the submitted plaintext JOIN and SPU Group-by.

The driver sees both CSVs and plaintext JOIN. This is NOT secure JOIN integration.
Run from WSL using the project's existing Python 3.11/SPU environment.
"""
from pathlib import Path
from typing import NamedTuple
import argparse
import importlib.util
import json
from fractions import Fraction
import sys

ROOT = Path(__file__).resolve().parents[2]
GROUP_ROOT = ROOT / 'Secrecy-Project-Group-by-Backend-main'
sys.path.insert(0, str(GROUP_ROOT / 'src'))

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

join_module = load_module('submitted_join', ROOT / '第一周A/join_core.py')
# Reuse the submitted synthetic validator/oracle; this is not a production service.
fixtures = load_module('submitted_fixtures', GROUP_ROOT / 'src/backend/groupby/experiments/test_scenarios.py')

import numpy as np
import jax
import jax.numpy as jnp
import spu
from spu.utils import frontend
from spu.utils.simulation import Simulator
from backend.groupby.algorithm.common import groupby_common
from backend.groupby.algorithm.aggregates.count import count_from_common
from backend.groupby.algorithm.aggregates.sum import sum_from_common

class JoinBatch(NamedTuple):
    """MPC boundary: secret int32 columns [K], K is public; valid must be 0/1."""
    group_key: object
    amount_cent: object
    valid: object

class AggregateBatch(NamedTuple):
    group_key: object
    count: object
    sum_cent: object
    mean_numerator: object
    mean_denominator: object
    valid: object

def aggregate_kernel(keys, amounts, valid):
    """Runs inside SPU. Reuses one grouping for COUNT/SUM/exact MEAN."""
    common = groupby_common(keys, amounts, valid)
    count = count_from_common(common)
    total = sum_from_common(common)
    return AggregateBatch(common.keys_out, count, total, total,
                          jnp.where(common.valid_out != 0, count, 1), common.valid_out)

def secure_join_kernel(left_ids, left_groups, left_valid, right_ids, right_amounts, right_valid):
    """REPLACEMENT POINT: JOIN owner implements this inside the same SPU plan.

    Return JoinBatch with K=N*M secret slots, no reconstruction/host filtering.
    match = left_valid[i] & right_valid[j] & (left_ids[i] == right_ids[j]).
    Preserve each matching pair. No plaintext fallback is permitted.
    """
    raise NotImplementedError('Secure JOIN has not been delivered; use synthetic demo explicitly')

def secure_pipeline_kernel(*secret_inputs):
    batch = secure_join_kernel(*secret_inputs)
    return aggregate_kernel(*batch)

def plaintext_join_adapter(left, right, scenario, capacity):
    """Normalize both scenarios to the unchanged submitted medical JOIN schema."""
    _, _, subject, group, record, amount, _, _ = fixtures.SCHEMAS[scenario]
    a = [dict(person_id=r[subject], product_code=r[group]) for r in left]
    b = [dict(person_id=r[subject], settlement_id=r[record], total_expense_cent=r[amount]) for r in right]
    joined = join_module.inner_join(a, b)
    canonical = sorted((r['person_id'], r['product_code'], r['settlement_id'], r['total_expense_cent']) for r in joined)
    # Check the actual submitted JOIN against an independent oracle, not just counts.
    if canonical != fixtures.reference_join(left, right, scenario):
        raise AssertionError('Submitted JOIN differs from independent reference')
    if len(joined) > capacity:
        raise ValueError('JOIN_CAPACITY_EXCEEDED')
    padding = capacity - len(joined)
    return canonical, JoinBatch(*(np.asarray(x, np.int32) for x in (
        [r['product_code'] for r in joined] + [0]*padding,
        [r['total_expense_cent'] for r in joined] + [0]*padding,
        [1]*len(joined) + [0]*padding)))

class Runtime:
    def __init__(self):
        self.sim = Simulator.simple(3, spu.ProtocolKind.ABY3, spu.FieldType.FM64)
        self.cache = {}

    def run(self, batch):
        k = len(batch.valid)
        if k not in self.cache:
            dummy = tuple(np.zeros(k, np.int32) for _ in range(3))
            executable, output = frontend.compile(frontend.Kind.JAX, aggregate_kernel, dummy,
                {}, ['group_key','amount_cent','valid'], [spu.Visibility.VIS_SECRET]*3,
                lambda flat: [f'out{i}' for i in range(len(flat))])
            self.cache[k] = executable, jax.tree_util.tree_structure(output)
        executable, tree = self.cache[k]
        return jax.tree_util.tree_unflatten(tree, self.sim(executable, *batch))

def check_and_decode(output, groups, capacity):
    # Synthetic recipient only. Production must enforce designated-recipient release.
    expected_keys = [g[0] for g in groups] + [0]*(capacity-len(groups))
    expected_counts = [g[1] for g in groups] + [0]*(capacity-len(groups))
    expected_sums = [g[2] for g in groups] + [0]*(capacity-len(groups))
    expected_valid = [1]*len(groups) + [0]*(capacity-len(groups))
    for actual, want in zip(output, (expected_keys, expected_counts, expected_sums,
            expected_sums, [g[1] for g in groups]+[1]*(capacity-len(groups)), expected_valid)):
        assert actual.shape == (capacity,) and actual.dtype == np.int32
        np.testing.assert_array_equal(actual, want)
    return [dict(group_code=g[0], count=g[1], sum_cent=g[2],
                 mean_numerator=g[2], mean_denominator=g[1],
                 mean_yuan_display=fixtures.yuan_display(Fraction(g[2],g[1]))) for g in groups]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=fixtures.SCHEMAS)
    parser.add_argument('--case', default='demo')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.all and not args.scenario:
        parser.error('Choose --all or --scenario')
    runtime = Runtime()
    records = []
    scenarios = fixtures.SCHEMAS if args.all else [args.scenario]
    for scenario in scenarios:
        base = GROUP_ROOT/'test'/scenario
        cases = fixtures.load_json(base/'reference_only/case_index.json')['cases'] if args.all else [dict(case=args.case)]
        for entry in cases:
            folder = base/entry['case']
            expected = fixtures.load_json(folder/'reference_only/expected.json')
            result = dict(scenario=scenario, case=entry['case'], mpc_executed=False)
            try:
                try:
                    config,left,right = fixtures.validate_inputs(folder,scenario)
                    status,code='SUCCESS',None
                except fixtures.Rejected as exc:
                    status,code='REJECT',str(exc)
                assert (status,code)==(expected['expected_status'],expected['error_code'])
                result.update(status=status,error_code=code)
                if status=='SUCCESS':
                    capacity=config['left_capacity']*config['right_capacity']
                    assert capacity*100_000_000 <= 2_147_483_647
                    joined,batch=plaintext_join_adapter(left,right,scenario,capacity)
                    groups=fixtures.oracle(joined)
                    fixtures.check_reference_files(folder,scenario,expected,left,right,joined,groups)
                    output=runtime.run(batch)
                    result.update(mpc_executed=True,public_join_capacity=capacity,
                                  rows=check_and_decode(output,groups,capacity))
                result['passed']=True
            except Exception as exc:
                result.update(passed=False,error=f'{type(exc).__name__}: {exc}')
            records.append(result)
            print(scenario,entry['case'],'PASS' if result['passed'] else 'FAIL',flush=True)
    report=dict(mode='SYNTHETIC_PLAINTEXT_JOIN_THEN_SPU_GROUPBY',secure_join_implemented=False,
                total=len(records),passed=sum(r['passed'] for r in records),cases=records)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0 if report['total']==report['passed'] else 1

if __name__=='__main__':
    sys.exit(main())
