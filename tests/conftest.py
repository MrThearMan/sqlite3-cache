import os

import pytest
from sqlite_cache.sqlite_cache import Cache


@pytest.fixture(scope="session", autouse=True)
def cache():
    if os.path.exists(".cache"):
        os.remove(".cache")

    cache = Cache()
    yield cache
    cache.close()

    if os.path.exists(".cache"):
        os.remove(".cache")


@pytest.fixture(autouse=True)
def clear_cache(cache):
    cache.clear()
