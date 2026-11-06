# Group-by implementation plan

Status: research goal confirmed, implementation details proposed, 2026-11-03.
Evidence: [research notes](research-notes.md).

## Confirmed direction and working assumptions

- Confirmed: reproduce the algorithms with documented differences; reproducing
  malicious-security guarantees is not a required deliverable.
- Confirmed: the team selected SPU. Another teammate owns JOIN. The integrated
  demonstration will present JOIN and Group-by, sharing dataset features from A
  to B through computing providers.
- Confirmed: this is a small simulation demonstration; no exact row limit or
  deadline has been supplied.
- Provisional: three computing providers, using ABY3/FM64 for the initial local
  experiments. The final party count and protocol configuration need agreement.
- Proposed: B receives final group keys and requested aggregates. Whether B also
  receives row-level features or a standalone JOIN result is still unspecified.
  A and B are data/recipient roles, not automatically two of the compute parties.

Use a synthetic JOIN-shaped fixture to develop Group-by independently. Agree the
handoff before either component develops its own incompatible runtime wrapper;
see [the integration draft](join-groupby-contract.md).

## Recommended next increment

Build a small library implementing exact COUNT(*) and SUM over secret keys,
values, and validity bits. Run it through SPU ABY3 locally first. Deliver a
plaintext oracle, a secret-key sorting baseline, fixed-capacity shared outputs,
and correctness tests before building an HTTP service.

Retain the public-domain equality example only as a smoke/comparison baseline.
It costs O(NG) comparisons for G public candidate keys and cannot discover arbitrary
secret keys. An unknown key must not silently disappear: require a complete domain
or compute a secret out-of-domain flag with an explicitly chosen release policy.

Use installed SPU Group-by as a comparison implementation, not the final research
contribution. Implement and explain our own operator steps using audited SPU
primitives, then separately map them to the selected paper version.

## Proposed operator contract

This is a logical interface, not a wire format for serializing shares.

```text
groupby(shared_table, public_spec) -> shared_grouped_table

shared_table:
  keys[N, K]          secret integer-encoded keys
  values[N, V]        secret bounded integer measures
  valid[N]           secret bits: 1 real row, 0 padding/unmatched row

public_spec:
  schema/version, N, K, V, selected key/value columns, aggregate list
  integer widths, value bounds, algorithm version, runtime identity

shared_grouped_table:
  keys[N, K], aggregates[N, A], valid[N]
  same public capacity N; unused payloads zeroed; validity disambiguates zero
```

Start with one key and one measure, COUNT(*) plus SUM. Reserve the shape convention
for multiple columns; implement those only after the first slice passes. No SQL
NULL, strings, floats, DISTINCT, MEDIAN, or arbitrary SQL in the first increment.
If JOIN needs outer-join NULL semantics, extend the contract with per-column
null bits; row validity and SQL NULL are different concepts.

COUNT(*) counts valid joined rows, including repeated matches, not distinct
people. SUM includes negative and zero values. The integration adapter must check
matching MPC protocol, party ordering, field, schema, encoding, and runtime/session.
An object reference from an unrelated runtime is not interchangeable with a share.
Never reconstruct a JOIN result merely to bridge incompatible runtimes.

## Functional sorting baseline (our proposal)

1. Obliviously sort by `(1-valid, key)` and carry values/validity with the rows.
   Require bit-valued validity from the upstream contract. Invalid rows go last.
2. Compute secret group boundaries. For each row, mark an end only if the row is
   valid and the next row is invalid or has a different key; handle the last row
   explicitly. Invalid rows must never create a returned group.
3. Compute integer segmented prefix sums of `valid` and `valid * value`, resetting
   at group starts. Use a parallel scan where supported; validate associativity
   and integer dtypes. Batch COUNT/SUM through the same sorting/boundary stage.
4. Keep only endpoints using secret selects; zero every other key/value payload.
5. Obliviously compact endpoint rows using `(1-end, key)` so real group summaries
   occupy the first slots in key order. Keep the output length N and the validity
   vector secret. This second sort is an explicit baseline cost, not free cleanup.
6. Return shared outputs. Do not return the un-compacted endpoint positions or
   sorted input keys to the caller in plaintext.

N=0 is a public-shape special case returning empty arrays. All-invalid N>0 returns
N invalid zeroed rows. A legitimate key zero or sum zero remains a valid result.
This baseline is a segmented-scan adaptation; its COUNT/SUM steps are not yet
claimed to be the paper's permutation/difference construction.

Prefer deterministic secure compaction for this baseline over introducing a
home-made shuffle. At authorized final release, compact validity reveals the
number of output groups, but not their original endpoint positions. If even the
number of groups must remain hidden from the recipient, define a different
release contract before enabling output. COUNT intentionally reveals group sizes;
SUM-only must not accidentally reveal them through positional layout.

## Numeric and disclosure contract

- Initial int32 input/accumulator prototype: declare public capacity N and absolute
  value bound B such that N and N*B fit signed int32, including intermediate sums.
  Enforce bounds at data-owner ingestion; this is an assumption under semi-honest
  inputs, not a malicious-input range proof. Test with an unbounded Python oracle.
- If larger data needs int64, enable and verify JAX x64 plus SPU compilation first.
  FM64 alone does not widen an int32 JAX computation. No silent modular overflow
  or floating-point fallback is acceptable.
- Public metadata: padded capacities, schema, query columns/aggregates, dtype,
  selected algorithm, and runtime settings. Timing/resource leakage is not proved
  absent by functional testing. Actual row counts remain hidden only if ingestion
  also pads without revealing them.
- Computing parties keep input values, boundaries, and intermediate group counts
  shared. The coordinator receives job metadata and handles, not plaintext tables.
- The authorized recipient may receive only final keys/requested aggregates and
  the output validity needed to interpret them. Recipient, group-count disclosure,
  and retention rules remain open decisions. No service release is enabled yet.

## Work sequence and completion criteria

| Stage | Work | Completion criterion |
| --- | --- | --- |
| 0: feasibility | Check current environment and bundled primitive behavior | Done: two synthetic smoke checks; see notes |
| 1: semantics | Implement types/spec validation, Python oracle, bounded fixtures | Exact expected results for empty, single/all-equal/all-distinct, negative/zero keys, zero sums, padding, and numeric limits |
| 2: MPC baseline | Implement the six steps above with a simulator adapter | Oracle parity on deterministic and seeded random fixtures; inspect compiler output for secret input visibility, static shapes, and absence of unintended reveals |
| 3: reproduction | Obtain full target paper/version; map protocols to code; implement selected common/count/sum construction | Step/primitive/assumption map complete, deviations explicit, parity against oracle and baseline; security claims match runtime |
| 4: integration | Agree JOIN contract; create runtime adapter and a shared JOIN-shaped fixture | No reconstruction between operators; all-invalid/padded JOIN output works; incompatible runtime/schema rejected |
| 5: service/demo | Add the team's chosen job API and authorized release adapter; run separate workers | End-to-end synthetic demo with agreed recipient; errors/cancellation coordinated across parties; no private intermediates logged |
| 6: evaluation | Compare public-domain, sorting baseline, and reproduced variant | Reproducible correctness/performance report, including sorting, aggregation, compaction and release costs |

Malicious-security reproduction is outside the confirmed deliverable. Keep the
ABY3 semi-honest assumption and all substituted primitives explicit in the report.
If the goal changes, reassess backend support and proof assumptions separately.

Suggested future layout (create files when their stage begins):

```text
backend/groupby/
  contract.py             public schema and supported semantics
  reference.py            independent plaintext oracle
  kernels/               JAX kernels; baseline and paper adaptation separated
  runtime/               simulation and later distributed adapters
  tests/                 semantic, MPC, and integration fixtures
  benchmarks/            synthetic generators and measurement harness
  experiments/           clearly labeled feasibility probes
```

For benchmarks start at N=16,64,256,1024 and increase only after measuring memory
and runtime. Vary group cardinality, skew, padding fraction, and numeric magnitude.
Use public experimental parameters; do not select a production algorithm from
secret observed cardinality. Record versions, hardware, protocol/field, compile
time and execution time separately; report communication bytes/rounds only when
instrumented. Local simulation results are not LAN/WAN benchmarks. Set a latency
target after dataset size and deployment constraints are known.

## Decisions to discuss

1. What does JOIN produce: runtime/session, party count, padded capacity, secret
   validity, key encoding, and duplicate/NULL semantics?
2. What exactly may B receive: final aggregates only, row-level features, or a
   standalone JOIN result as well? May B learn distinct keys and group count?
3. What are the first demo's row count, value bounds, deadline, and required
   aggregates? Recommend COUNT/SUM first; MEDIAN after protocol mapping.

These questions do not block the oracle or synthetic baseline. They do block
finalizing deployment, security claims, and real result-release behavior.
