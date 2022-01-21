import pytest

from sqlite3_cache import Cache


@pytest.fixture(scope="session", autouse=True)
def cache_create():
    cache = Cache()
    yield cache
    cache.close()


@pytest.fixture
def cache(cache_create):
    yield cache_create
    cache_create.clear()


@pytest.fixture(autouse=True)
def clear_cache(cache):
    cache.clear()
