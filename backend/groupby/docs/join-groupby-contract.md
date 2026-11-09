# JOIN → Group-by integration draft

Proposed for team discussion, 2026-11-03. SPU and separate JOIN ownership are
confirmed; the interface below is not yet agreed with the JOIN implementer.

## First demonstration

Use synthetic data with A owning an identifier-to-category table and B owning
identifier-to-measure records. Proposed first query: JOIN by identifier, then
COUNT(*) and SUM(measure) by A's category. Prefer a unique identifier in A and
allow repeated identifiers in B for this first fixture; the teammate must confirm
the supported JOIN variant. COUNT means matched records, not unique identifiers.

```text
A: (id, category)       B: (id, measure)
           \             /
          SPU computing providers (provisionally three)
                         |
                   teammate's JOIN
                         |
          shared category, measure, valid — capacity N
                         |
                  our Group-by
                         |
          shared group keys, counts, sums, valid — capacity N
                         |
            agreed final-result release to B
```

This is a proposed aggregate-only flow. Showing both algorithms in the UI can
mean showing public stages, timings, and final results; it does not require
opening the intermediate joined table. Row-level feature delivery would be a
separate output policy, not an implicit consequence of demonstrating JOIN.

## Handoff to agree

| Item | Proposed initial agreement |
| --- | --- |
| Execution | Same SPU runtime/session, protocol, field, and ordered computing parties |
| Payload | Secret integer `category[N]`, `measure[N]`, bit `valid[N]` |
| Capacity | Public padded N agreed before execution; actual matched count remains shared |
| Padding | `valid=0` excludes a row; zero category/measure is legitimate data |
| Multiplicity | One row per match; repeated matches count separately |
| NULLs | First fixture is an inner JOIN; outer JOIN needs a separate column-null contract |
| Numeric bounds | Public N and measure bound B selected to prevent accumulator overflow |
| Ownership | JOIN teammate supplies shared output; Group-by consumes it without reconstruction |
| Release | Final recipient B proposed; exact permitted fields and metadata still to be confirmed |

Do not standardize raw share serialization yet. Start by composing kernels in
one SPU execution or retaining values in one shared runtime. Two independent
simulator calls would reconstruct their boundary outputs and do not demonstrate
a secret-shared JOIN → Group-by pipeline.

## Shared synthetic acceptance fixture

```text
A = [(101, 1), (102, 2), (103, 1)]
B = [(101, 200), (101, 300), (103, 400), (999, 50)]
```

For the proposed inner JOIN, three rows are valid and identifier 999 contributes
nothing. A capacity-four handoff can use category `[1,1,1,0]`, measure
`[200,300,400,0]`, valid `[1,1,1,0]`; JOIN may emit another order. The expected
Group-by result is one valid group: category 1, count 3, sum 900. Remaining
output rows are invalid with zeroed payloads. These plaintext values are test
expectations only; the eventual pipeline keeps the handoff shared.

Also test no matches, repeated matches, category zero, negative measures, and
padding whose category equals a real category. Use this contract fixture while
JOIN is under development, then run it through the actual composed pipeline.
