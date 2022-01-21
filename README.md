# SQLite3 Cache

[![Coverage Status][coverage-badge]][coverage]
[![GitHub Workflow Status][status-badge]][status]
[![PyPI][pypi-badge]][pypi]
[![GitHub][licence-badge]][licence]
[![GitHub Last Commit][repo-badge]][repo]
[![GitHub Issues][issues-badge]][issues]
[![Python Version][version-badge]][pypi]

```shell
pip install sqlite3-cache
```

---

**Documentation**: [https://mrthearman.github.io/sqlite3-cache/](https://mrthearman.github.io/sqlite3-cache/)

**Source Code**: [https://github.com/MrThearMan/sqlite3-cache/](https://github.com/MrThearMan/sqlite3-cache/)

---

Use [SQLite3][sqlite] as quick, persistent, thread-safe cache.
Can store any [picklable][picklable] objects.

```python
from sqlite3_cache import Cache

cache = Cache()
```


[sqlite]: https://docs.python.org/3/library/sqlite3.html
[picklable]: https://docs.python.org/3/library/pickle.html

[coverage-badge]: https://coveralls.io/repos/github/MrThearMan/sqlite3-cache/badge.svg?branch=main
[status-badge]: https://img.shields.io/github/workflow/status/MrThearMan/sqlite3-cache/Tests
[pypi-badge]: https://img.shields.io/pypi/v/sqlite3-cache
[licence-badge]: https://img.shields.io/github/license/MrThearMan/sqlite3-cache
[repo-badge]: https://img.shields.io/github/last-commit/MrThearMan/sqlite3-cache
[issues-badge]: https://img.shields.io/github/issues-raw/MrThearMan/sqlite3-cache
[version-badge]: https://img.shields.io/pypi/pyversions/sqlite3-cache

[coverage]: https://coveralls.io/github/MrThearMan/sqlite3-cache?branch=main
[status]: https://github.com/MrThearMan/sqlite3-cache/actions/workflows/main.yml
[pypi]: https://pypi.org/project/sqlite3-cache
[licence]: https://github.com/MrThearMan/sqlite3-cache/blob/main/LICENSE
[repo]: https://github.com/MrThearMan/sqlite3-cache/commits/main
[issues]: https://github.com/MrThearMan/sqlite3-cache/issues
