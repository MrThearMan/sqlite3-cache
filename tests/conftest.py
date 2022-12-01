import pytest

from sqlite3_cache import Cache


@pytest.fixture(scope="session", autouse=True)
def cache_create():
    cache = Cache()
    try:
        yield cache
    finally:
        cache.close()


@pytest.fixture
def cache(cache_create):
    try:
        yield cache_create
    finally:
        cache_create.clear()


@pytest.fixture(autouse=True)
def clear_cache(cache):
    cache.clear()
