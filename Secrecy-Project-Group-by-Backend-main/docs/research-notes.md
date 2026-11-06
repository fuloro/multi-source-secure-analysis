# Investigation record — 2026-11-03

## User clarification after investigation

The user confirmed algorithm reproduction with documented differences, SPU as
the team's framework, JOIN ownership by another teammate, and a small simulation
demonstration involving dataset features from A to B through computing providers.
Approximately three computing parties are expected but not settled. Exact output
disclosure, JOIN handoff, dataset bounds, and deadline remain unspecified.
The plan now reflects these confirmations; prior assistant proposals remain
proposals unless explicitly confirmed.

## Materials actually inspected

- Root and component READMEs (both languages), `r.txt`, and installed SPU sources.
- Relevant available ChatGPT chat: [论文分段总结](https://chatgpt.com/c/6ae32fbf-7e08-83ea-b398-2ae11d2515e6).
  The connector returned five turns with no further page. The README's shared
  link identifies the earlier discussion; this investigation read the account
  chat through the connector. Earlier attachments were not retrieved.
- The user's stated objective in that chat is protocol reproduction using an
  existing MPC library plus a frontend/backend demonstration. Healthcare examples,
  React/FastAPI, and particular implementation stages were assistant suggestions,
  not independently confirmed team decisions.

## Research interpretation

[CCS 2023 / extended paper](https://eprint.iacr.org/2024/141.pdf) targets
honest-majority secure relational protocols, including malicious security.
Search-indexed Protocol 4.1 describes sorting, secret group-end markers, and
moving representative rows before padding. COUNT/SUM do not require sorting by
the value as well as the key. This supports examining a shared grouping stage
before implementing individual aggregates. Direct PDF retrieval returned 403;
the complete algorithms and version must still be checked before asserting a
step-by-step reproduction. In particular, do not invent missing SUM steps and
attribute them to the paper.

[SECRECY, NSDI 2023](https://www.usenix.org/system/files/nsdi23-liagouris.pdf)
provides operator composition and optimization context. Its appendices discuss
validity bits for composing selection/JOIN with Group-by, and its evaluation
separates sorting and final shuffling costs. For this contribution, use that as
motivation to preserve shared intermediate tables and measure complete pipelines;
do not expand into implementing its query optimizer.

[SPU protocol documentation](https://secret-flow.antgroup.com/docs/spu/en/reference/mpc_status.html)
identifies its ABY3 implementation as semi-honest three-party computation.
The proposed baseline assumes at most one corrupt computing party. Independent
administration of computing parties matters; three local threads are not three
independent trust domains. An ABY3 adaptation cannot inherit the CCS malicious
security claim.

## Local evidence

Python 3.11.18; SPU 0.9.5; JAX/JAXLIB 0.4.34; NumPy 1.26.4.
The full `secretflow` Python package is not installed. No dependency changes made.
The directory is not currently a Git repository; `rg` is unavailable.

Inspected installed sources under
`.venv311/lib/python3.11/site-packages/spu/`:

| Source | Finding | Consequence |
| --- | --- | --- |
| `ops/groupby/segmentation.py` | Uses `jax.lax.sort`, adjacent comparisons, and a scan | Useful baseline and primitive feasibility check; not proof of CCS protocol equivalence |
| `ops/groupby/aggregation.py` | Segmented scans; default `jnp.ones` introduces floating point; warns about opening group-end output positions | Audit exact arithmetic and keep intermediates shared |
| `ops/groupby/postprocess.py` | Explicit plaintext postprocessing; key processing uses uniqueness/zero-padding assumptions | Do not use as the internal secure operator or treat zero as missing |
| `ops/groupby/shuffle.py` | Sorts by supplied `secret_random_order` | Randomness provenance, collisions, and what each party knows need a protocol-level decision |
| `utils/simulation.py` | Secret-shares dynamic inputs across in-memory runtimes, then reconstructs returned values | Valid execution smoke test, not deployment or release-policy validation |

Two synthetic ABY3/FM64 smoke checks passed:

1. Public keys {1,2,3}, inputs from the previous chat: counts [2,2,1], sums
   [400,700,400], both int32.
2. Bundled sorted Group-by: keys [2,0,2,-1,0], values [10,0,-10,7,4].
   Sorted keys [-1,0,0,2,2], end flags [1,0,1,0,1], endpoint sums
   [7,0,4,0,0]. Sums were float32 despite int32 inputs.

Reproduce with `.venv311/bin/python backend/groupby/experiments/probe_spu.py`. This script deliberately opens synthetic intermediates.
These checks establish small-input feasibility only; they do not establish
overflow safety, padding correctness, performance, or protocol security.
