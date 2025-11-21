import math


def poly(xs: list, x: float):
    """
    Evaluates polynomial with coefficients xs at point x.
    return xs[0] + xs[1] * x + xs[1] * x^2 + .... xs[n] * x^n
    """
    return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])


def find_zero(xs: list):
    """ xs are coefficients of a polynomial.
    find_zero find x such that poly(x) = 0.
    find_zero returns only only zero point, even if there are many.
    Moreover, find_zero only takes list xs having even number of coefficients
    and largest non zero coefficient as it guarantees
    a solution.
    >>> round(find_zero([1, 2]), 2) # f(x) = 1 + 2x
    -0.5
    >>> round(find_zero([-6, 11, -6, 1]), 2) # (x - 1) * (x - 2) * (x - 3) = -6 + 11x - 6x^2 + x^3
    1.0
    """
    # If constant term is zero, 0 is a root
    if xs and xs[0] == 0:
        return 0.0

    # Start with a symmetric interval around 0 and expand until a sign change is found
    a, b = -1.0, 1.0
    fa, fb = poly(xs, a), poly(xs, b)

    if fa == 0.0:
        return a
    if fb == 0.0:
        return b

    # Expand interval exponentially until a sign change is detected
    max_expand = 200
    for _ in range(max_expand):
        if fa * fb <= 0:
            break
        a *= 2.0
        b *= 2.0
        fa, fb = poly(xs, a), poly(xs, b)
        if fa == 0.0:
            return a
        if fb == 0.0:
            return b

    # At this point, we should have fa and fb of opposite signs
    # Use bisection to refine the root
    left, right = a, b
    fl, fr = fa, fb

    # Tolerances
    tol_f = 1e-12
    tol_x = 1e-12
    max_iter = 1000

    for _ in range(max_iter):
        mid = (left + right) / 2.0
        fm = poly(xs, mid)

        if abs(fm) <= tol_f or abs(right - left) <= tol_x:
            return mid

        # Decide which subinterval to keep: keep where sign changes
        if fl * fm <= 0:
            right, fr = mid, fm
        else:
            left, fl = mid, fm

    # If not converged within max_iter, return midpoint as best estimate
    return (left + right) / 2.0