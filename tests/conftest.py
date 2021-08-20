import os

import pytest


@pytest.fixture(autouse=True)
def delete_cache():
    if os.path.exists(".cache"):
        os.remove(".cache")

    if os.path.exists(".cache2"):
        os.remove(".cache2")
