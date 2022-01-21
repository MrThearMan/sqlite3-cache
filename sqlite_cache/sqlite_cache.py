import pickle
import sqlite3
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from threading import local
from typing import Any, Optional


__all__ = ["Cache"]


class Cache:

    DEFAULT_TIMEOUT = 300
    DEFAULT_PRAGMA = {
        "mmap_size": 2 ** 26,  # https://www.sqlite.org/pragma.html#pragma_mmap_size
        "cache_size": 8192,  # https://www.sqlite.org/pragma.html#pragma_cache_size
        "wal_autocheckpoint": 1000,  # https://www.sqlite.org/pragma.html#pragma_wal_autocheckpoint
        "auto_vacuum": "none",  # https://www.sqlite.org/pragma.html#pragma_auto_vacuum
        "synchronous": "off",  # https://www.sqlite.org/pragma.html#pragma_synchronous
        "journal_mode": "wal",  # https://www.sqlite.org/pragma.html#pragma_journal_mode
        "temp_store": "memory",  # https://www.sqlite.org/pragma.html#pragma_temp_store
    }

    _create_sql = "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value BLOB, exp FLOAT)"
    _create_index_sql = "CREATE UNIQUE INDEX IF NOT EXISTS cache_key ON cache(key)"
    _set_pragma = "PRAGMA {}"
    _set_pragma_equal = "PRAGMA {}={}"

    _add_sql = (
        "INSERT INTO cache (key, value, exp) VALUES (:key, :value, :exp) "
        "ON CONFLICT(key) DO UPDATE SET value = :value, exp = :exp "
        "WHERE DATETIME(exp, 'unixepoch') <= DATETIME('now')"
    )
    _get_sql = "SELECT value, exp FROM cache WHERE key = :key"
    _set_sql = (
        "INSERT INTO cache (key, value, exp) VALUES (:key, :value, :exp) "
        "ON CONFLICT(key) DO UPDATE SET value = :value, exp = :exp"
    )
    _check_sql = "SELECT value, exp FROM cache WHERE key = :key AND DATETIME(exp, 'unixepoch') > DATETIME('now')"
    _update_sql = "UPDATE cache SET value = :value WHERE key = :key AND DATETIME(exp, 'unixepoch') > DATETIME('now')"

    # TODO: add 'RETURNING COUNT(*)!=0' to these when sqlite3 version >=3.35.0
    _delete_sql = "DELETE FROM cache WHERE key = :key"
    _touch_sql = "UPDATE cache SET exp = :exp WHERE key = :key AND DATETIME(exp, 'unixepoch') > DATETIME('now')"
    _clear_sql = "DELETE FROM cache"

    _add_many_sql = (
        "INSERT INTO cache (key, value, exp) VALUES {}"
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, exp = excluded.exp "
        "WHERE DATETIME(exp, 'unixepoch') <= DATETIME('now')"
    )
    _get_many_sql = "SELECT key, value, exp FROM cache WHERE key IN ({})"
    _set_many_sql = (
        "INSERT INTO cache (key, value, exp) VALUES {}"
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, exp = excluded.exp"
    )
    _delete_many_sql = "DELETE FROM cache WHERE key IN ({})"

    def __init__(
        self,
        *,
        filename: str = ".cache",
        path: str = None,
        in_memory: bool = True,
        timeout: int = 5,
        **kwargs,
    ):
        """Create a cache using sqlite3.

        :param filename: Cache file name.
        :param path: Path string to the wanted db location. If None, use current directory.
        :param in_memory: Create database in-memory only. A file is still created, but nothing is stored in it.
        :param timeout: Cache connection timeout.
        :param kwargs: Pragma settings. https://www.sqlite.org/pragma.html
        """

        filepath = filename if path is None else str(Path(path) / filename)
        suffix = ":?mode=memory&cache=shared" if in_memory else ""
        self.connection_string = f"{filepath}{suffix}"
        self.pragma = {**kwargs, **self.DEFAULT_PRAGMA}
        self.timeout = timeout
        self.local = local()
        self.local.instances = getattr(self.local, "instances", 0) + 1

        self._con.execute(self._create_sql)
        self._con.execute(self._create_index_sql)
        self._con.commit()

    @property
    def _con(self) -> sqlite3.Connection:
        try:
            return self.local.con
        except AttributeError:
            self.local.con = sqlite3.connect(self.connection_string, timeout=self.timeout)
            self._apply_pragma()
            return self.local.con

    def __getitem__(self, item: str) -> Any:
        value = self.get(item)
        if value is None:
            raise KeyError("Key not in cache.")
        return value

    def __setitem__(self, item: str, value: Any) -> None:
        self.set(item, value)

    def __delitem__(self, key):
        self.delete(key)

    def __contains__(self, key):
        return self._con.execute(self._check_sql, {"key": key}).fetchone() is not None

    def __enter__(self):
        self._con  # noqa pylint: disable=W0104
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.local.instances = getattr(self.local, "instances", 0) - 1
        if self.local.instances <= 0:
            self.close()

    def close(self) -> None:
        self._con.execute(self._set_pragma.format("optimize"))
        self._con.close()
        with suppress(AttributeError):
            delattr(self.local, "con")

    def _apply_pragma(self):
        for key, value in self.pragma.items():
            self._con.execute(self._set_pragma_equal.format(key, value))

    @staticmethod
    def _exp_timestamp(timeout: int = DEFAULT_TIMEOUT) -> float:
        return (datetime.now(timezone.utc) + timedelta(seconds=timeout)).timestamp()

    @staticmethod
    def _stream(value: Any) -> bytes:
        return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def _unstream(value: bytes) -> Any:
        return pickle.loads(value)

    def add(self, key: str, value: Any, timeout: int = DEFAULT_TIMEOUT) -> None:
        data = {"key": key, "value": self._stream(value), "exp": self._exp_timestamp(timeout)}
        self._con.execute(self._add_sql, data)
        self._con.commit()

    def get(self, key: str, default: Any = None) -> Any:
        result: Optional[tuple] = self._con.execute(self._get_sql, {"key": key}).fetchone()

        if result is None:
            return default

        exp = datetime.utcfromtimestamp(result[1])

        if datetime.utcnow() >= exp:
            self._con.execute(self._delete_sql, {"key": key})
            self._con.commit()
            return default

        return self._unstream(result[0])

    def set(self, key: str, value: Any, timeout: int = DEFAULT_TIMEOUT) -> None:
        data = {"key": key, "value": self._stream(value), "exp": self._exp_timestamp(timeout)}
        self._con.execute(self._set_sql, data)
        self._con.commit()

    def update(self, key: str, value: Any) -> None:
        data = {"key": key, "value": self._stream(value)}
        self._con.execute(self._update_sql, data)
        self._con.commit()

    def touch(self, key: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        data = {"exp": self._exp_timestamp(timeout), "key": key}
        self._con.execute(self._touch_sql, data)
        self._con.commit()

    def delete(self, key: str) -> None:
        self._con.execute(self._delete_sql, {"key": key})
        self._con.commit()

    def add_many(self, dict_: dict, timeout: int = DEFAULT_TIMEOUT) -> None:
        command = self._add_many_sql.format(", ".join([f"(:key{n}, :value{n}, :exp{n})" for n in range(len(dict_))]))

        data = {}
        exp = self._exp_timestamp(timeout)
        for i, (key, value) in enumerate(dict_.items()):
            data[f"key{i}"] = key
            data[f"value{i}"] = self._stream(value)
            data[f"exp{i}"] = exp

        self._con.execute(command, data)
        self._con.commit()

    def get_many(self, keys: list) -> dict:
        seq = ", ".join([f"'{value}'" for value in keys])
        fetched: list = self._con.execute(self._get_many_sql.format(seq)).fetchall()

        if not fetched:
            return {}

        results = {}
        to_delete = []
        for key, value, exp in fetched:
            exp = datetime.utcfromtimestamp(exp)

            if datetime.utcnow() >= exp:
                to_delete.append(key)
                continue

            results[key] = self._unstream(value)

        if to_delete:
            self._con.execute(self._delete_many_sql.format(", ".join([f"'{value}'" for value in to_delete])))
            self._con.commit()

        return results

    def set_many(self, dict_: dict, timeout: int = DEFAULT_TIMEOUT) -> None:
        command = self._set_many_sql.format(", ".join([f"(:key{n}, :value{n}, :exp{n})" for n in range(len(dict_))]))

        data = {}
        exp = self._exp_timestamp(timeout)
        for i, (key, value) in enumerate(dict_.items()):
            data[f"key{i}"] = key
            data[f"value{i}"] = self._stream(value)
            data[f"exp{i}"] = exp

        self._con.execute(command, data)
        self._con.commit()

    def update_many(self, dict_: dict) -> None:
        seq = [{"key": key, "value": self._stream(value)} for key, value in dict_.items()]
        self._con.executemany(self._update_sql, seq)
        self._con.commit()

    def touch_many(self, keys: list, timeout: int = DEFAULT_TIMEOUT) -> None:
        exp = self._exp_timestamp(timeout)
        seq = [{"key": key, "exp": exp} for key in keys]
        self._con.executemany(self._touch_sql, seq)
        self._con.commit()

    def delete_many(self, keys: list) -> None:
        self._con.execute(self._delete_many_sql.format(", ".join([f"'{value}'" for value in keys])))
        self._con.commit()

    def get_or_set(self, key: str, default: Any, timeout: int = DEFAULT_TIMEOUT) -> Any:
        result: Optional[tuple] = self._con.execute(self._get_sql, {"key": key}).fetchone()

        if result is not None:
            exp = datetime.utcfromtimestamp(result[1])

            if datetime.utcnow() >= exp:
                self._con.execute(self._delete_sql, {"key": key})
            else:
                return self._unstream(result[0])

        data = {"key": key, "value": self._stream(default), "exp": self._exp_timestamp(timeout)}
        self._con.execute(self._set_sql, data)
        self._con.commit()
        return default

    def clear(self) -> None:
        self._con.execute(self._clear_sql)
        self._con.commit()

    def incr(self, key: str, delta: int = 1) -> None:
        result: Optional[tuple] = self._con.execute(self._check_sql, {"key": key}).fetchone()

        if result is None:
            raise ValueError("Nonexistent or expired cache key.")

        value = self._unstream(result[0])
        if not isinstance(value, int):
            raise ValueError("Value is not a number.")

        self._con.execute(self._update_sql, {"key": key, "value": self._stream(value + delta)})
        self._con.commit()

    def decr(self, key: str, delta: int = 1) -> None:
        result: Optional[tuple] = self._con.execute(self._check_sql, {"key": key}).fetchone()

        if result is None:
            raise ValueError("Nonexistent or expired cache key.")

        value = self._unstream(result[0])
        if not isinstance(value, int):
            raise ValueError("Value is not a number.")

        self._con.execute(self._update_sql, {"key": key, "value": self._stream(value - delta)})
        self._con.commit()

    def memorize(self, timeout: int = DEFAULT_TIMEOUT):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                result = self.get(f"{func}-{args}-{kwargs}", obj)
                if result == obj:
                    result = func(*args, **kwargs)
                    self.set(f"{func}-{args}-{kwargs}", result, timeout)
                return result

            return wrapper

        obj = object()
        return decorator
