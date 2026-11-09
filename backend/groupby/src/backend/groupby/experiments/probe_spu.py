"""Synthetic-only feasibility checks; simulator reconstructs all outputs.

Run from the workspace: .venv311/bin/python backend/groupby/experiments/probe_spu.py
This is not a backend service or paper-protocol implementation.
"""

import importlib.metadata

import jax.numpy as jnp
import numpy as np
import spu
from spu.ops.groupby.aggregation import groupby_sum
from spu.ops.groupby.segmentation import groupby
from spu.utils.simulation import Simulator, sim_jax


def public_domain(keys, values):
    groups = jnp.array([1, 2, 3], dtype=jnp.int32)
    mask = (keys[:, None] == groups[None, :]).astype(jnp.int32)
    return jnp.sum(mask, axis=0), jnp.sum(mask * values[:, None], axis=0)


def bundled_sorted(keys, values):
    sorted_keys, sorted_values, _, ends = groupby([keys], [values])
    return sorted_keys[0], ends, groupby_sum(sorted_values, ends)


def main():
    for package in ("spu", "jax", "jaxlib", "numpy"):
        print(package, importlib.metadata.version(package))
    sim = Simulator.simple(3, spu.ProtocolKind.ABY3, spu.FieldType.FM64)
    counts, sums = sim_jax(sim, public_domain)(
        np.array([1, 2, 1, 3, 2], dtype=np.int32),
        np.array([100, 200, 300, 400, 500], dtype=np.int32),
    )
    np.testing.assert_array_equal(counts, [2, 2, 1])
    np.testing.assert_array_equal(sums, [400, 700, 400])
    print("Public-domain COUNT/SUM passed:", counts, sums)

    keys, ends, sums = sim_jax(sim, bundled_sorted)(
        np.array([2, 0, 2, -1, 0], dtype=np.int32),
        np.array([10, 0, -10, 7, 4], dtype=np.int32),
    )
    np.testing.assert_array_equal(keys, [-1, 0, 0, 2, 2])
    np.testing.assert_array_equal(ends, [1, 0, 1, 0, 1])
    np.testing.assert_array_equal(sums, [[7], [0], [4], [0], [0]])
    print("Bundled sorting/aggregation passed; sum dtype:", sums.dtype)
    print("Synthetic simulation only; no deployment/security claim.")


if __name__ == "__main__":
    main()
