"""精确均值返回 (keys, numerator, denominator, valid)，无效分母为 1。"""
from jax import lax
import jax.numpy as jnp
from ..common import groupby_common
from .sum import sum_from_common
from .count import count_from_common


def mean_from_common(common):
    return (common.keys_out, sum_from_common(common),
            jnp.where(common.valid_out != 0, count_from_common(common), 1), common.valid_out)


def groupby_mean(keys, values, valid):
    return mean_from_common(groupby_common(keys, values, valid))


def _unsigned_divmod(dividend, divisor, bits):
    """Exact binary long division for nonnegative int32 lanes and divisor >= 1."""
    def step(i, state):
        quotient, remainder = state
        bit = (dividend >> (bits - 1 - i)) & 1
        # The partial remainder never exceeds the input prefix, which fits int32.
        partial = (remainder << 1) | bit
        take = partial >= divisor
        return (quotient << 1) | take.astype(jnp.int32), jnp.where(
            take, partial - divisor, partial)

    zero = jnp.zeros_like(dividend)
    return lax.fori_loop(0, bits, step, (zero, zero))


def groupby_mean_only(keys, values, valid):
    """Return the exact mean in lowest terms, including 0/1 for padding.

    The canonical pair depends only on the mean. All Euclidean steps execute
    on shared integers for a public number of iterations.
    """
    keys_out, numerator, denominator, valid_out = groupby_mean(keys, values, valid)
    n = keys.shape[0]
    if n == 0:
        return keys_out, numerator, denominator, valid_out

    count_bits = n.bit_length()

    def euclidean_step(_, pair):
        a, b = pair
        active = b != 0
        divisor = jnp.where(active, b, 1)
        _, remainder = _unsigned_divmod(a, divisor, count_bits)
        return jnp.where(active, b, a), remainder

    # After the first remainder, each two steps at least halve the larger
    # operand. The denominator is at most the public capacity.
    magnitude = jnp.abs(numerator)
    _, remainder = _unsigned_divmod(magnitude, denominator, 31)
    gcd, _ = lax.fori_loop(0, 2 * count_bits, euclidean_step,
                           (denominator, remainder))
    reduced, _ = _unsigned_divmod(magnitude, gcd, 31)
    reduced_denominator, _ = _unsigned_divmod(denominator, gcd, count_bits)
    return keys_out, jnp.where(numerator < 0, -reduced, reduced), reduced_denominator, valid_out
