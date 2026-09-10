"""Shared pytest setup.

The one thing here is throttle isolation. DRF's ScopedRateThrottle counts
requests in Django's cache, which is a single in-process LocMemCache for the
whole test run — so login/register attempts accumulate across tests and the
"auth" scope (10/min) starts returning 429 to whichever test happens to run
once the budget is spent. That makes failures depend on how many tests ran
before, not on the code under test.
"""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()
