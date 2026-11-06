# Group-by Backend Component

[中文](README.zh.md) | English

This directory is reserved for the server-side Group-by contribution to the MPC analytics project.

The component's responsibility is secure grouping and aggregation, integrated with the surrounding backend's data and execution flow. The library implements COUNT, SUM, MEAN, MIN, MAX, and MEDIAN; the subset exposed through the eventual service remains to be agreed.

The protocol to reproduce, MPC backend integration, input/output representation, API responsibilities, rules for revealing results, and deployment model are proposed in the design plan below and await team confirmation.

See the [workspace README](../../../README.md) for project context and contribution scope.

## Design and next steps

See the [implementation plan](../../../docs/groupby-plan.md) and [investigation record](../../../docs/research-notes.md). The proposed first increment is exact integer COUNT/SUM with secret keys and validity masks, fixed-capacity shared outputs, and an independent reference oracle. Integration and security requirements remain provisional.

Run the synthetic feasibility probe from the workspace root:

```sh
.venv311/bin/python src/backend/groupby/experiments/probe_spu.py
```

## Integer SUM baseline

`algorithm/g_sum.py` uses common grouping, global prefix sums, secret permutation
and adjacent differences. The former segmented-scan baseline is in `g_sum_baseline.py`. Inputs are equal-length int32 keys, values and
0/1 validity. Upstream must ensure the sum of absolute input values fits int32.
Invalid output payloads are zeroed; the kernel does not reconstruct results.
This adapts paper-level steps; sorting-based permutation and security assumptions differ.

Run `.venv311/bin/python src/backend/groupby/experiments/demo_sum.py`.
The synthetic simulator experiment uses `reference_only/expected_join.csv` as
an explicit JOIN handoff fixture padded to public right_capacity; JOIN is not
implemented. Simulator outputs are reconstructed for testing only. Independent
Python-integer reference, boundary/random checks and expected.json verify results.

## Secret permutation adapter

`algorithm/permutation.py` provides `gen_perm`, `apply_perm`, and `apply_inv`
using zero-based destination positions and reusable multi-column permutations.
Run `.venv311/bin/python src/backend/groupby/experiments/test_permutation.py`.
See the [Chinese interface and scope notes](../../../docs/permutation.zh.md).
This SPU-sort adapter does not reproduce the paper's specialized permutation
protocol or its communication guarantees. The original SUM baseline is preserved; aggregate implementations are in separate files.

## Common grouping

See [field mapping and implementation differences (Chinese)](../../../docs/groupby-common.zh.md).
Run `.venv311/bin/python src/backend/groupby/experiments/test_common.py`.

## Aggregate operators

All six aggregates are available through `backend.groupby.algorithm`. Implementations
are in `aggregates/`, permutations in `primitives/`, and the reference baseline in
`baselines/`. Legacy `g_*.py` and permutation imports remain supported. MEAN/MEDIAN return
`(keys, numerator, denominator, valid)`; other operators return three arrays.
Run `.venv311/bin/python src/backend/groupby/experiments/test_aggregates.py`.
These are SPU adaptations with documented differences, not full protocol reproductions.

COUNT follows Protocol 4.2 by differencing compacted group-end positions.
MEAN offers two shared outputs. `groupby_mean` preserves the sum and count,
while `groupby_mean_only` returns the exact fraction in lowest terms so equal
means have the same representation across different group sizes (§4.3).

MIN/MAX/MEDIAN now follow the documented paper-level construction; MEDIAN
returns twice the median with a constant denominator of 2. Its int32 input
absolute-value bound is 1073741823. Root-level sum_from_common.py and
mean_from_common.py forwarding modules were removed; import from aggregates instead.

## Full synthetic scenario checks

Run `.venv311/bin/python src/backend/groupby/experiments/test_scenarios.py`
from the workspace root. All 30 fixtures are checked against the data-use guide:
14 accepted cases run seven aggregate entry points in SPU ABY3/FM64 simulation;
16 rejected cases stop at harness input validation. The JOIN oracle is plaintext
and synthetic-only. This does not validate a deployed CSV service or secure JOIN.
See the [Chinese test report](../../../reports/scenario-test-report-2026-11-05.zh.md).
