# SQLite Cache

[![Coverage Status][coverage-badge]][coverage]
[![GitHub Workflow Status][status-badge]][status]
[![PyPI][pypi-badge]][pypi]
[![GitHub][licence-badge]][licence]
[![GitHub Last Commit][repo-badge]][repo]
[![GitHub Issues][issues-badge]][issues]
[![Python Version][version-badge]][pypi]

```shell
pip install sqlite-cache
```

---

**Documentation**: [https://mrthearman.github.io/sqlite-cache/](https://mrthearman.github.io/sqlite-cache/)

**Source Code**: [https://github.com/MrThearMan/sqlite-cache/](https://github.com/MrThearMan/sqlite-cache/)

---

Use [SQLite3][sqlite] as quick, persistent, thread-safe cache.
Can store any [picklable][picklable] objects.

```python
from sqlite_cache import Cache

cache = Cache()
```

---

## Quickstart

Interface works similarly to [Django's cache interface][django-cache]
with a few additions. Values stay in the cache even if the given timeout is reached, and only gets deleted on the
next call to `clear`, or any of these methods: `get`, `get_or_set`, `get_many`, `delete`, or `delete_many` for that key.

Supports indexing:

- `cache["key"] = "value"`, `cache["key"]`, `del cache["key"]`

Supports membership test:

- `"key" in cache`

Can be used as a context manager:

- `with Cache() as cache: ...`


[sqlite]: https://docs.python.org/3/library/sqlite3.html
[picklable]: https://docs.python.org/3/library/pickle.html
[django-cache]: https://docs.djangoproject.com/en/3.2/topics/cache/#basic-usage

[coverage-badge]: https://coveralls.io/repos/github/MrThearMan/sqlite-cache/badge.svg?branch=main
[status-badge]: https://img.shields.io/github/workflow/status/MrThearMan/sqlite-cache/Tests
[pypi-badge]: https://img.shields.io/pypi/v/sqlite-cache
[licence-badge]: https://img.shields.io/github/license/MrThearMan/sqlite-cache
[repo-badge]: https://img.shields.io/github/last-commit/MrThearMan/sqlite-cache
[issues-badge]: https://img.shields.io/github/issues-raw/MrThearMan/sqlite-cache
[version-badge]: https://img.shields.io/pypi/pyversions/sqlite-cache

[coverage]: https://coveralls.io/github/MrThearMan/sqlite-cache?branch=main
[status]: https://github.com/MrThearMan/sqlite-cache/actions/workflows/main.yml
[pypi]: https://pypi.org/project/sqlite-cache
[licence]: https://github.com/MrThearMan/sqlite-cache/blob/main/LICENSE
[repo]: https://github.com/MrThearMan/sqlite-cache/commits/main
[issues]: https://github.com/MrThearMan/sqlite-cache/issues
