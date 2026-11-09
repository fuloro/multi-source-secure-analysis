# Secure Group-by Backend

[中文](README.zh.md) | English

Workspace for the **Group-by portion of a secure multi-party analytics project**. This contribution covers the server-side backend component that performs grouping and aggregation as part of a larger MPC application.

The overall project aims to reproduce research protocols using an existing MPC library and demonstrate them through an application with separate frontend and backend services. This workspace focuses on Group-by; frontend development, JOIN implementation, and ownership of the complete query system are outside this contribution's scope.

## Research context

Previous discussion connects two research directions:

- *Secure Statistical Analysis on Multiple Datasets: Join and Group-By* (CCS 2023): secure relational operator protocols.
- *SECRECY* (NSDI 2023): secure query execution and optimization across operators.

SPU is the current technical starting point. The [implementation plan](docs/groupby-plan.md) proposes a COUNT/SUM baseline followed by explicit paper-protocol mapping and backend integration. Security and integration decisions awaiting team input are recorded there.

## Contribution scope

The intended component groups protected records and computes requested aggregates within the server-side MPC execution flow. It should eventually integrate with the project's other backend components and its authorized result delivery flow.

The implementation must distinguish between a functional aggregation baseline and reproduction of a specific paper protocol. Likewise, local MPC experiments do not establish the security or deployment readiness of the complete application.

## Workspace

| Location | Purpose |
| --- | --- |
| `src/backend/groupby/` | Reserved home for the Group-by backend contribution. |
| `requirements-py311-tested.txt` | Existing pinned Python dependency list, preserved as supplied. |
| `.venv311/` | Existing local Python environment; excluded from version control. |

## Current status

Implemented SPU permutation adapters, common grouping, and integer SUM using
prefix sums, permutation and differences. The segmented-scan baseline is retained
for comparison. COUNT/MEAN/MIN/MAX/MEDIAN are implemented; MEAN and MEDIAN return exact integer numerator/denominator pairs.
This is an algorithm adaptation with documented differences, not a malicious-security
reproduction or a deployed backend service. JOIN belongs to a teammate.

## Run the synthetic checks

```sh
python3.11 -m venv .venv311
.venv311/bin/python -m pip install -r requirements-py311-tested.txt
.venv311/bin/python src/backend/groupby/experiments/test_permutation.py
.venv311/bin/python src/backend/groupby/experiments/test_common.py
.venv311/bin/python src/backend/groupby/experiments/demo_sum.py
```

The version list describes the tested local environment; fresh installation has
not been verified here. The demo deliberately uses a synthetic reference JOIN
fixture and reconstructs simulator outputs. It does not implement secure JOIN.
All 30 fixtures under `test/` have now been checked: 14 successful cases through
SPU simulation and 16 rejected by the synthetic harness before MPC. Run
`.venv311/bin/python src/backend/groupby/experiments/test_scenarios.py`.
See the [Chinese test report](reports/scenario-test-report-2026-11-05.zh.md).
The harness uses a plaintext reference JOIN and is not a production input service
or a secure JOIN-to-Group-by integration test.

See [implementation plan](docs/groupby-plan.md), [research notes](docs/research-notes.md),
and [common grouping mapping (Chinese)](docs/groupby-common.zh.md).

## Aggregate operators

All six aggregates are available through `backend.groupby.algorithm`. Implementations
are in `aggregates/`, permutations in `primitives/`, and the reference baseline in
`baselines/`. Legacy `g_*.py` and permutation imports remain supported. MEAN/MEDIAN return
`(keys, numerator, denominator, valid)`; other operators return three arrays.
Run `.venv311/bin/python src/backend/groupby/experiments/test_aggregates.py`.
These are SPU adaptations with documented differences, not full protocol reproductions.

Import `sum_from_common` and `mean_from_common` from their respective aggregate modules.

### Section 4 coverage

The following mapping uses the six aggregates enumerated in the [extended paper, §4](https://www.eprint.mirror.cypherpunks.su/2024/141/1706767899.pdf).

| Paper | Implementation under `src/backend/groupby/algorithm/` |
| --- | --- |
| 4.1, common | `common.py` sorts valid rows first and compacts group ends. Secret validity distinguishes a real zero key from padding. |
| 4.2, COUNT | `aggregates/count.py` permutes one-based endpoint positions and differences adjacent positions. It masks padding because the last valid position may be smaller than capacity. |
| 4.4, SUM | `aggregates/sum.py` permutes endpoint prefix sums and differences them. |
| §4.3, MEAN | `aggregates/mean.py` provides the shared sum/count pair via `groupby_mean`. For a mean-only result, `groupby_mean_only` reduces that pair inside MPC using fixed-step Euclidean GCD and integer long division. Equal means always have the same representation. |
| 4.6 / 4.8, MAX / MIN | `aggregates/max.py` and `aggregates/min.py` select the last or first row after sorting each group by value. |
| 4.10, MEDIAN | `aggregates/median.py` combines two selections using forward and reverse ranks (4.12 / 4.14 in `protocols/ranks.py`). Protocol 4.16 in `protocols/find_zero_or_one.py` clears the low bit before testing for zero. The result has a constant denominator of 2 and requires absolute input values at most 1073741823. |

The kernels use bounded int32 arithmetic, fixed-capacity outputs, SPU sorting for permutations, and semi-honest ABY3 in local simulation. The paper's malicious-security proof and communication bounds apply to its own protocols.
