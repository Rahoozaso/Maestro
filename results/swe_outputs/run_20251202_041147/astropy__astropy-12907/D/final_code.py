from __future__ import annotations

from typing import List

# NOTE:
# This placeholder file is being returned because the provided execution plan
# (REQUEST_ADDITIONAL_CONTEXT) did not include any concrete REFACTOR or
# REPLACE actions nor the actual contents of astropy/modeling/separable.py.
#
# According to the plan we are supposed to *request* the real source of
# astropy.modeling.separable.separability_matrix and related code before
# making any modifications. In this environment, however, we cannot
# perform interactive requests back to the repository or user; we can only
# return a single final_code string.
#
# To avoid fabricating an implementation and potentially misrepresenting
# Astropy's actual logic, this file merely documents that additional
# context is required to continue. No functional separability_matrix is
# defined here on purpose.


def __context_required__() -> List[str]:
    """Describe the additional context required to implement the fix.

    This helper exists only to communicate, in code form, what is needed
    next based on the Architect's plan. It is **not** part of Astropy's
    real public API.

    Returns
    -------
    List[str]
        A list of artifacts that must be supplied before the bug in
        ``separability_matrix`` for nested CompoundModels can be fixed.
    """

    return [
        "Full source of astropy/modeling/separable.py (or the module that\n"
        "defines `separability_matrix`).",
        "Definitions of CompoundModel and relevant model-composition logic\n"
        "that `separability_matrix` depends on.",
        "Existing unit tests (if any) that cover `separability_matrix` and\n"
        "CompoundModel compositions, especially nested & and | operators.",
    ]