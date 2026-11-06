"""Synthetic-only scenario acceptance; NOT a CSV service or secure JOIN adapter.

Owners' CSVs and reconstructed simulator outputs are plaintext in this process.
Never use this harness with private inputs. reference_only is read for comparison,
not as MPC input. See docs/数据使用说明.docx and the Chinese result report.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, localcontext
from fractions import Fraction
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import sys
import time
import traceback
from zoneinfo import ZoneInfo

import jax
import numpy as np
import spu
from spu.utils import frontend
from spu.utils.simulation import Simulator

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
from backend.groupby.algorithm import (
    groupby_count, groupby_sum, groupby_mean, groupby_mean_only,
    groupby_min, groupby_max, groupby_median,
)

FUNCTIONS = (groupby_count, groupby_sum, groupby_mean, groupby_mean_only,
             groupby_min, groupby_max, groupby_median)
SCHEMAS = {
    'medical_insurance': ('insured_members.csv', 'medical_settlements.csv',
                          'person_id', 'product_code', 'settlement_id',
                          'total_expense_cent', 3,
                          ('product_code', 'record_count', 'sum_expense_cent', 'mean_expense_cent')),
    'consumer_analysis': ('customer_profiles.csv', 'purchase_records.csv',
                          'user_id', 'age_band', 'transaction_id', 'amount_cent', 4,
                          ('age_band', 'transaction_count', 'sum_amount_cent', 'mean_amount_cent')),
}


class Rejected(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def read_csv(path, columns, capacity, id_column, duplicate_code, group_column=None, max_group=0, amount_column=None):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, [])
        if len(header) != len(set(header)) or set(header) != set(columns):
            raise Rejected('CSV_SCHEMA')
        raw = list(reader)
    if len(raw) > capacity:
        raise Rejected('CAPACITY_EXCEEDED')
    rows, ids = [], set()
    for row in raw:
        if len(row) != len(header):
            raise Rejected('CSV_SCHEMA')
        values = {}
        for name, text in zip(header, row):
            if not text or not text.strip():
                raise Rejected('MISSING_VALUE')
            if re.fullmatch(r'-?[0-9]+', text) is None:
                raise Rejected('INTEGER_FORMAT')
            # Python integers first; do not truncate or convert through float.
            number = int(text)
            if name == amount_column:
                if not 0 <= number <= 100_000_000:
                    raise Rejected('AMOUNT_RANGE')
            elif name == group_column:
                if not 1 <= number <= max_group:
                    raise Rejected('GROUP_CODE')
            elif not 1 <= number <= 2_147_483_647:
                raise Rejected('ID_RANGE')
            values[name] = number
        if values[id_column] in ids:
            raise Rejected(duplicate_code)
        ids.add(values[id_column])
        rows.append(values)
    return rows


def validate_inputs(folder, scenario):
    config = load_json(folder / 'public_config.json')
    require(set(config) == {'scenario', 'period_start', 'period_end_exclusive', 'currency',
                            'amount_unit', 'left_capacity', 'right_capacity'}, 'public config schema')
    require(config['scenario'] == scenario, 'scenario mismatch')
    require((config['period_start'], config['period_end_exclusive'], config['currency'],
             config['amount_unit']) == ('2026-10-01', '2026-11-01', 'CNY', 'cent'), 'batch metadata')
    require(config['left_capacity'] == config['right_capacity'] == 4, 'fixture capacities')
    require(config['right_capacity'] * 100_000_000 <= 2_147_483_647, 'unsafe SUM bound')
    left_file, right_file, subject, group, record, amount, max_group, _ = SCHEMAS[scenario]
    left = read_csv(folder/'owner_a'/left_file, (subject, group), config['left_capacity'],
                    subject, 'DUPLICATE_LEFT_ID', group_column=group, max_group=max_group)
    right = read_csv(folder/'owner_b'/right_file, (record, subject, amount), config['right_capacity'],
                     record, 'DUPLICATE_RECORD_ID', amount_column=amount)
    return config, left, right


def reference_join(left, right, scenario):
    # Plaintext synthetic oracle only; no JOIN implementation is claimed.
    _, _, subject, group, record, amount, _, _ = SCHEMAS[scenario]
    return sorted((b[subject], a[group], b[record], b[amount])
                  for a in left for b in right if a[subject] == b[subject])


def oracle(joined):
    grouped = {}
    for _, key, _, value in joined:
        grouped.setdefault(key, []).append(value)
    results = []
    for key, values in sorted(grouped.items()):
        ordered = sorted(values)
        n = len(values)
        median = Fraction(ordered[n//2], 1) if n % 2 else Fraction(ordered[n//2-1]+ordered[n//2], 2)
        results.append((key, n, sum(values), Fraction(sum(values), n), min(values), max(values), median))
    return results


def yuan_display(mean):
    with localcontext() as context:
        context.prec = 60
        return format((Decimal(mean.numerator)/Decimal(mean.denominator)/100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP), '.2f')


def check_reference_files(folder, scenario, expected, left, right, joined, groups):
    require(expected['synthetic_only'] is True, 'fixture not marked synthetic')
    require((len(left), len(right), len(joined)) == (expected['actual_left_rows'],
            expected['actual_right_rows'], expected['matching_records']), 'reference cardinalities')
    summary = [dict(group=k, count=c, sum_cent=s, mean_cent_numerator=m.numerator,
                    mean_cent_denominator=m.denominator, mean_yuan_display=yuan_display(m))
               for k,c,s,m,*_ in groups]
    require(summary == expected['groups'], 'Python oracle differs from expected.json')
    with (folder/'reference_only/expected_join.csv').open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields = ['subject_id','group_code','record_id','amount_cent']
        require(reader.fieldnames == fields, 'expected_join schema')
        reference = [tuple(int(r[f]) for f in fields) for r in reader]
    require(Counter(reference) == Counter(joined), 'reference JOIN mismatch')
    with (folder/'reference_only/expected_result.csv').open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields = SCHEMAS[scenario][-1]
        require(reader.fieldnames == list(fields), 'expected_result schema')
        rows = list(reader)
    require(len(rows) == len(groups), 'display row count')
    for row, (key,count,total,mean,*_) in zip(rows, groups):
        require([int(row[f]) for f in fields[:3]] == [key,count,total], 'display integer fields')
        # CSV is a readable decimal approximation; exact values live in JSON.
        require(abs(Fraction(Decimal(row[fields[3]]))-mean) <= Fraction(1, 10**12), 'display mean precision')
    return summary


def kernel(keys, values, valid):
    return tuple(function(keys, values, valid) for function in FUNCTIONS)


class SyntheticRuntime:
    def __init__(self):
        self.sim = Simulator.simple(3, spu.ProtocolKind.ABY3, spu.FieldType.FM64)
        self.cache = {}
        self.compilations = []

    def run(self, arrays):
        capacity = len(arrays[0])
        if capacity not in self.cache:
            start = time.perf_counter()
            dummy = tuple(np.zeros(capacity, dtype=np.int32) for _ in range(3))
            executable, output = frontend.compile(
                frontend.Kind.JAX, kernel, dummy, {}, ['keys','values','valid'],
                [spu.Visibility.VIS_SECRET]*3,
                lambda flat: [f'out{i}' for i in range(len(flat))])
            self.compilations.append(dict(capacity=capacity, seconds=time.perf_counter()-start,
                                          input_visibility='VIS_SECRET', operators=len(FUNCTIONS)))
            self.cache[capacity] = executable, jax.tree_util.tree_structure(output)
        executable, tree = self.cache[capacity]
        start = time.perf_counter()
        flat = self.sim(executable, *arrays)
        seconds = time.perf_counter()-start
        return jax.tree_util.tree_unflatten(tree, flat), seconds


def check_mpc(outputs, groups, capacity):
    keys = [g[0] for g in groups] + [0]*(capacity-len(groups))
    bits = [1]*len(groups) + [0]*(capacity-len(groups))
    for function, out in zip(FUNCTIONS, outputs):
        require(all(x.shape == (capacity,) and x.dtype == np.int32 for x in out),
                f'{function.__name__}: capacity/dtype')
        np.testing.assert_array_equal(out[0], keys)
        np.testing.assert_array_equal(out[-1], bits)
        name = function.__name__
        index = {'groupby_count':1, 'groupby_sum':2, 'groupby_mean':3, 'groupby_mean_only':3,
                 'groupby_min':4, 'groupby_max':5, 'groupby_median':6}[name]
        actual = [Fraction(int(n), int(d)) for n,d in zip(out[1],out[2])] if len(out)==4 else list(map(int,out[1]))
        want = [g[index] for g in groups] + [0]*(capacity-len(groups))
        require(actual == want, f'{name}: oracle mismatch')
        if len(out)==4:
            require(all(int(d)>0 for d in out[2]), f'{name}: nonpositive denominator')
            if name == 'groupby_median':
                np.testing.assert_array_equal(out[2], [2]*capacity)
            elif name == 'groupby_mean_only':
                np.testing.assert_array_equal(out[1], [g[3].numerator for g in groups]+[0]*(capacity-len(groups)))
                np.testing.assert_array_equal(out[2], [g[3].denominator for g in groups]+[1]*(capacity-len(groups)))
            else:
                np.testing.assert_array_equal(out[1], [g[2] for g in groups]+[0]*(capacity-len(groups)))
                np.testing.assert_array_equal(out[2], [g[1] for g in groups]+[1]*(capacity-len(groups)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'reports/scenario-test-results-2026-11-05.json')
    args = parser.parse_args()
    report = dict(started_at=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(), synthetic_only=True,
                  environment={'python':platform.python_version(), 'platform':platform.platform(),
                               **{p:importlib.metadata.version(p) for p in ('spu','jax','jaxlib','numpy')}},
                  runtime={'protocol':'ABY3', 'field':'FM64', 'parties':3, 'mode':'in-memory simulation',
                           'communication_bytes':None, 'communication_rounds':None},
                  specification_sha256=hashlib.sha256((ROOT/'docs/数据使用说明.docx').read_bytes()).hexdigest(),
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  integrity=[], cases=[])
    runtime = SyntheticRuntime()
    for scenario in SCHEMAS:
        base = ROOT/'test'/scenario
        manifest = load_json(base/'SHA256SUMS.json')
        mismatches = [p for p,h in manifest.items() if not (base/p).is_file() or hashlib.sha256((base/p).read_bytes()).hexdigest()!=h]
        found = {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file() and p.name!='SHA256SUMS.json'}
        report['integrity'].append(dict(scenario=scenario, files=len(manifest), mismatches=mismatches,
                                         unlisted=sorted(found-set(manifest)), missing=sorted(set(manifest)-found)))
        index = load_json(base/'reference_only/case_index.json')
        require(index['synthetic_only'] is True, 'index not synthetic')
        require({p.parent.name for p in base.glob('*/public_config.json')} == {c['case'] for c in index['cases']}, 'case coverage')
        for case in index['cases']:
            result = dict(scenario=scenario, case=case['case'], expected_status=case['status'],
                          expected_error=case['error_code'], mpc_executed=False)
            folder = base/case['case']
            try:
                try:
                    config, left, right = validate_inputs(folder, scenario)
                    status, code = 'SUCCESS', None
                except Rejected as exc:
                    status, code = 'REJECT', str(exc)
                result.update(actual_status=status, actual_error=code)
                expected = load_json(folder/'reference_only/expected.json')
                require((status,code)==(case['status'],case['error_code'])==
                        (expected['expected_status'],expected['error_code']), 'status/error mismatch')
                if status == 'SUCCESS':
                    joined = reference_join(left, right, scenario)
                    groups = oracle(joined)
                    result['groups'] = check_reference_files(folder,scenario,expected,left,right,joined,groups)
                    capacity = config['right_capacity']
                    padding = capacity-len(joined)
                    arrays = tuple(np.asarray(x, np.int32) for x in (
                        [r[1] for r in joined]+[0]*padding,
                        [r[3] for r in joined]+[0]*padding,
                        [1]*len(joined)+[0]*padding))
                    outputs, seconds = runtime.run(arrays)
                    result.update(mpc_executed=True, execution_seconds=seconds,
                                  matching_records=len(joined), output_capacity=capacity)
                    check_mpc(outputs,groups,capacity)
                    result['operators_checked'] = [f.__name__ for f in FUNCTIONS]
                result['passed'] = True
            except Exception:
                result['passed'] = False
                result['failure'] = traceback.format_exc()
            report['cases'].append(result)
            print(f"{scenario}/{case['case']}: {'PASS' if result['passed'] else 'FAIL'} ({result.get('actual_status','ERROR')})", flush=True)
    report['compilations'] = runtime.compilations
    report['finished_at'] = datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    report['summary'] = dict(total=len(report['cases']), passed=sum(c['passed'] for c in report['cases']),
                             mpc_cases=sum(c['mpc_executed'] for c in report['cases']),
                             rejected=sum(c.get('actual_status')=='REJECT' for c in report['cases']),
                             integrity_passed=all(not (c['mismatches'] or c['missing'] or c['unlisted']) for c in report['integrity']))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['summary'],ensure_ascii=False),flush=True)
    return 0 if report['summary']['passed']==len(report['cases']) and report['summary']['integrity_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
