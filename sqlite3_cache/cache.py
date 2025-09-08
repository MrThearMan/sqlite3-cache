from __future__ import annotations

import datetime
import pickle
import sqlite3
from contextlib import suppress
from functools import wraps
from pathlib import Path
from threading import local
from typing import TYPE_CHECKING, Any, ClassVar, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

try:
    from typing import Self
except ImportError:
    from typing import Self


__all__ = ["Cache"]


class Cache:
    """Simple SQLite Cache."""

    PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL
    DEFAULT_TIMEOUT = 300
    DEFAULT_PRAGMA: ClassVar[dict[str, int | str]] = {
        "mmap_size": 2**26,  # https://www.sqlite.org/pragma.html#pragma_mmap_size
        "cache_size": 8192,  # https://www.sqlite.org/pragma.html#pragma_cache_size
        "wal_autocheckpoint": 1000,  # https://www.sqlite.org/pragma.html#pragma_wal_autocheckpoint
        "auto_vacuum": "none",  # https://www.sqlite.org/pragma.html#pragma_auto_vacuum
        "synchronous": "off",  # https://www.sqlite.org/pragma.html#pragma_synchronous
        "journal_mode": "wal",  # https://www.sqlite.org/pragma.html#pragma_journal_mode
        "temp_store": "memory",  # https://www.sqlite.org/pragma.html#pragma_temp_store
    }

    _transaction_sql = "BEGIN EXCLUSIVE TRANSACTION; {} COMMIT TRANSACTION;"

    _create_sql = "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value BLOB, exp FLOAT);"
    _create_index_sql = "CREATE UNIQUE INDEX IF NOT EXISTS cache_key ON cache(key);"
    _set_pragma = "PRAGMA {};"
    _set_pragma_equal = "PRAGMA {}={};"

    _add_sql = (
        "INSERT INTO cache (key, value, exp) VALUES (:key, :value, :exp) "
        "ON CONFLICT(key) DO UPDATE SET value = :value, exp = :exp "
        "WHERE (exp <> -1.0 AND DATETIME(exp, 'unixepoch') <= DATETIME('now'));"
    )
    _get_sql = "SELECT value, exp FROM cache WHERE key = :key;"
    _set_sql = (
        "INSERT INTO cache (key, value, exp) VALUES (:key, :value, :exp) "
        "ON CONFLICT(key) DO UPDATE SET value = :value, exp = :exp;"
    )
    _check_sql = (
        "SELECT value, exp FROM cache WHERE key = :key "
        "AND (exp = -1.0 OR DATETIME(exp, 'unixepoch') > DATETIME('now'));"
    )
    _update_sql = (
        "UPDATE cache SET value = :value WHERE key = :key "
        "AND (exp = -1.0 OR DATETIME(exp, 'unixepoch') > DATETIME('now'));"
    )

    # TODO: add 'RETURNING COUNT(*)!=0' to these when sqlite3 version >=3.35.0
    _delete_sql = "DELETE FROM cache WHERE key = :key;"
    _touch_sql = (
        "UPDATE cache SET exp = :exp WHERE key = :key AND (exp = -1.0 OR DATETIME(exp, 'unixepoch') > DATETIME('now'));"
    )
    _clear_sql = "DELETE FROM cache;"

    _add_many_sql = (
        "INSERT INTO cache (key, value, exp) VALUES {}"
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, exp = excluded.exp "
        "WHERE (exp <> -1.0 AND DATETIME(exp, 'unixepoch') <= DATETIME('now'));"
    )
    _get_many_sql = "SELECT key, value, exp FROM cache WHERE key IN ({});"
    _set_many_sql = (
        "INSERT INTO cache (key, value, exp) VALUES {}"
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, exp = excluded.exp;"
    )
    _delete_many_sql = "DELETE FROM cache WHERE key IN ({});"
    _get_keys_sql = "SELECT key, exp FROM cache ORDER BY key ASC;"
    _find_matching_keys_sql = "SELECT key, exp FROM cache WHERE key LIKE :pattern ORDER BY key ASC;"
    _clear_keys_matching_sql = "DELETE FROM cache WHERE key LIKE :pattern;"

    def __init__(
        self,
        *,
        filename: str = ".cache",
        path: str | None = None,
        in_memory: bool = True,
        timeout: int = 5,
        isolation_level: Literal["DEFERRED", "IMMEDIATE", "EXCLUSIVE"] | None = "DEFERRED",
        **kwargs: Any,
    ) -> None:
        """
        Create a cache using sqlite3.

        :param filename: Cache file name.
        :param path: Path string to the wanted db location. If None, use current directory.
        :param in_memory: Create database in-memory only. A file is still created, but nothing is stored in it.
        :param timeout: Cache connection timeout.
        :param isolation_level: Controls the transaction handling performed by sqlite3.
                                If set to None, transactions are never implicitly opened.
                                https://www.sqlite.org/lang_transaction.html
        :param kwargs: Pragma settings. https://www.sqlite.org/pragma.html
        """
        filepath = filename if path is None else str(Path(path) / filename)
        suffix = ":?mode=memory&cache=shared" if in_memory else ""
        self.connection_string = f"{filepath}{suffix}"
        self.pragma = {**kwargs, **self.DEFAULT_PRAGMA}
        self.timeout = timeout
        self.isolation_level = isolation_level
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
            self.local.con = sqlite3.connect(
                self.connection_string,
                timeout=self.timeout,
                isolation_level=self.isolation_level,
            )
            self._apply_pragma()
            return self.local.con

    def __getitem__(self, item: str) -> Any:
        value = self.get(item)
        if value is None:
            msg = "Key not in cache."
            raise KeyError(msg)
        return value

    def __setitem__(self, item: str, value: Any) -> None:
        self.set(item, value)

    def __delitem__(self, key: str) -> None:
        self.delete(key)

    def __contains__(self, key: str) -> bool:
        return self._con.execute(self._check_sql, {"key": key}).fetchone() is not None

    def __enter__(self) -> Self:
        self._con  # noqa: B018
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def __del__(self) -> None:
        self.local.instances = getattr(self.local, "instances", 0) - 1
        if self.local.instances <= 0:
            self.close()

    def close(self) -> None:
        """Closes the cache."""
        self._con.execute(self._set_pragma.format("optimize"))  # https://www.sqlite.org/pragma.html#pragma_optimize
        self._con.close()
        with suppress(AttributeError):
            delattr(self.local, "con")

    def _apply_pragma(self) -> None:
        for key, value in self.pragma.items():
            self._con.execute(self._set_pragma_equal.format(key, value))

    @staticmethod
    def _exp_timestamp(timeout: int = DEFAULT_TIMEOUT) -> float:
        if timeout < 0:
            return -1.0
        return (datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=timeout)).timestamp()

    @staticmethod
    def _exp_datetime(exp: float) -> datetime.datetime | None:
        if exp == -1.0:
            return None
        return datetime.datetime.fromtimestamp(exp, tz=datetime.UTC)

    def _stream(self, value: Any) -> bytes:
        return pickle.dumps(value, protocol=self.PICKLE_PROTOCOL)

    def _unstream(self, value: bytes) -> Any:
        return pickle.loads(value)  # noqa: S301

    def add(self, key: str, value: Any, timeout: int = DEFAULT_TIMEOUT) -> None:
        """
        Set the value to the cache only if the key is not already in the cache,
        or the found value has expired.

        :param key: Cache key.
        :param value: Picklable object to store.
        :param timeout: How long the value is valid in the cache.
                        Negative numbers will keep the key in cache until manually removed.
        """
        data = {"key": key, "value": self._stream(value), "exp": self._exp_timestamp(timeout)}
        self._con.execute(self._add_sql, data)
        self._con.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get the value under some key. Return `default` if key not in the cache or expired.

        :param key: Cache key.
        :param default: Value to return if key not in the cache.
        """
        result: tuple[bytes, float] | None = self._con.execute(self._get_sql, {"key": key}).fetchone()

        if result is None:
            return default

        exp = self._exp_datetime(result[1])
        if exp is not None and datetime.datetime.now(tz=datetime.UTC) >= exp:
            self._con.execute(self._delete_sql, {"key": key})
            self._con.commit()
            return default

        return self._unstream(result[0])

    def set(self, key: str, value: Any, timeout: int = DEFAULT_TIMEOUT) -> None:
        """
        Set a value in cache under some key.

        :param key: Cache key.
        :param value: Picklable object to store.
        :param timeout: How long the value is valid in the cache.
                        Negative numbers will keep the key in cache until manually removed.
        """
        data = {"key": key, "value": self._stream(value), "exp": self._exp_timestamp(timeout)}
        self._con.execute(self._set_sql, data)
        self._con.commit()

    def update(self, key: str, value: Any) -> None:
        """
        Update value in the cache. Does nothing if key not in the cache or expired.

        :param key: Cache key.
        :param value: Picklable object to store.
        """
        data = {"key": key, "value": self._stream(value)}
        self._con.execute(self._update_sql, data)
        self._con.commit()

    def touch(self, key: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        """
        Extend the lifetime of an object in cache. Does nothing if key is not in the cache or is expired.

        :param key: Cache key.
        :param timeout: How long the value is valid in the cache.
                        Negative numbers will keep the key in cache until manually removed.
        """
        data = {"exp": self._exp_timestamp(timeout), "key": key}
        self._con.execute(self._touch_sql, data)
        self._con.commit()

    def delete(self, key: str) -> None:
        """
        Remove the value under the given key from the cache. Does nothing if key is not in the cache.

        :param key: Cache key.
        """
        self._con.execute(self._delete_sql, {"key": key})
        self._con.commit()

    def add_many(self, dict_: dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> None:
        """
        For all keys in the given dict, add the value to the cache only if the key is not
        already in the cache, or the found value has expired.

        :param dict_: Cache keys with values to add.
        :param timeout: How long the value is valid in the cache.
                        Negative numbers will keep the key in cache until manually removed.
        """
        command = self._add_many_sql.format(", ".join([f"(:key{n}, :value{n}, :exp{n})" for n in range(len(dict_))]))

        data = {}
        exp = self._exp_timestamp(timeout)
        for i, (key, value) in enumerate(dict_.items()):
            data[f"key{i}"] = key
            data[f"value{i}"] = self._stream(value)
            data[f"exp{i}"] = exp

        self._con.execute(command, data)
        self._con.commit()

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """
        Get all values that exist and aren't expired from the given cache keys, and return a dict.

        :param keys: List of cache keys.
        """
        seq = ", ".join([f"'{value}'" for value in keys])
        fetched: list[tuple[str, Any, float]] = self._con.execute(self._get_many_sql.format(seq)).fetchall()

        if not fetched:
            return {}

        results: dict[str, Any] = {}
        to_delete: list[str] = []
        for key, value, exp in fetched:
            exp = self._exp_datetime(exp)  # noqa: PLW2901
            if exp is not None and datetime.datetime.now(tz=datetime.UTC) >= exp:
                to_delete.append(key)
                continue

            results[key] = self._unstream(value)

        if to_delete:
            self._con.execute(self._delete_many_sql.format(", ".join([f"'{value}'" for value in to_delete])))
            self._con.commit()

        return results

    def set_many(self, dict_: dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> None:
        """
        Set values to the cache for all keys in the given dict.

        :param dict_: Cache keys with values to set.
        :param timeout: How long the value is valid in the cache.
                        Negative numbers will keep the key in cache until manually removed.
        """
        command = self._set_many_sql.format(", ".join([f"(:key{n}, :value{n}, :exp{n})" for n in range(len(dict_))]))

        data = {}
        exp = self._exp_timestamp(timeout)
        for i, (key, value) in enumerate(dict_.items()):
            data[f"key{i}"] = key
            data[f"value{i}"] = self._stream(value)
            data[f"exp{i}"] = exp

        self._con.execute(command, data)
        self._con.commit()

    def update_many(self, dict_: dict[str, Any]) -> None:
        """
        Update values to the cache for all keys in the given dict. Does nothing if key not in cache or expired.

        :param dict_:Cache keys with values to update to.
        """
        seq = [{"key": key, "value": self._stream(value)} for key, value in dict_.items()]
        self._con.executemany(self._update_sql, seq)
        self._con.commit()

    def touch_many(self, keys: list[str], timeout: int = DEFAULT_TIMEOUT) -> None:
        """
        Extend the lifetime for all objects under the given keys in cache.
        Does nothing if a key is not in the cache or is expired.

        :param keys: List of cache keys.
        :param timeout: How long the value is valid in the cache.
                        Negative numbers will keep the key in cache until manually removed.
        """
        exp = self._exp_timestamp(timeout)
        seq = [{"key": key, "exp": exp} for key in keys]
        self._con.executemany(self._touch_sql, seq)
        self._con.commit()

    def delete_many(self, keys: list[str]) -> None:
        """
        Remove all the values under the given keys from the cache.

        :param keys: List of cache keys.
        """
        self._con.execute(self._delete_many_sql.format(", ".join([f"'{value}'" for value in keys])))
        self._con.commit()

    def get_or_set(self, key: str, default: Any, timeout: int = DEFAULT_TIMEOUT) -> Any:
        """
        Get a value under some key, or set the default if key is not in cache.

        :param key: Cache key.
        :param default: Picklable object to store if key is not in cache.
        :param timeout: How long the value is valid in the cache.
                        Negative numbers will keep the key in cache until manually removed.
        """
        result: tuple[bytes, float] | None = self._con.execute(self._get_sql, {"key": key}).fetchone()

        if result is not None:
            exp = self._exp_datetime(result[1])
            if exp is not None and datetime.datetime.now(tz=datetime.UTC) >= exp:
                self._con.execute(self._delete_sql, {"key": key})
            else:
                return self._unstream(result[0])

        data = {"key": key, "value": self._stream(default), "exp": self._exp_timestamp(timeout)}
        self._con.execute(self._set_sql, data)
        self._con.commit()
        return default

    def clear(self) -> None:
        """Clear the cache from all values."""
        self._con.execute(self._clear_sql)
        self._con.commit()

    def incr(self, key: str, delta: int = 1) -> int:
        """
        Increment the value in cache by the given delta.
        Note that this is not an atomic transaction!

        :param key: Cache key.
        :param delta: How much to increment.
        :raises ValueError: Value cannot be incremented.
        """
        result: tuple[bytes, float] | None = self._con.execute(self._check_sql, {"key": key}).fetchone()

        if result is None:
            msg = "Nonexistent or expired cache key."
            raise ValueError(msg)

        value = self._unstream(result[0])
        if not isinstance(value, int):
            msg = "Value is not a number."
            raise ValueError(msg)  # noqa: TRY004

        new_value = value + delta
        self._con.execute(self._update_sql, {"key": key, "value": self._stream(new_value)})
        self._con.commit()
        return new_value

    def decr(self, key: str, delta: int = 1) -> int:
        """
        Decrement the value in cache by the given delta.
        Note that this is not an atomic transaction!

        :param key: Cache key.
        :param delta: How much to decrement.
        :raises ValueError: Value cannot be decremented.
        """
        result: tuple[bytes, float] | None = self._con.execute(self._check_sql, {"key": key}).fetchone()

        if result is None:
            msg = "Nonexistent or expired cache key."
            raise ValueError(msg)

        value = self._unstream(result[0])
        if not isinstance(value, int):
            msg = "Value is not a number."
            raise ValueError(msg)  # noqa: TRY004

        new_value = value - delta
        self._con.execute(self._update_sql, {"key": key, "value": self._stream(new_value)})
        self._con.commit()
        return new_value

    def memoize(self, timeout: int = DEFAULT_TIMEOUT) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Save the result of the decorated function in cache. Calls with different
        arguments are saved under different keys.

        :param timeout: How long the value is valid in the cache.
                        Negative numbers will keep the key in cache until manually removed.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Callable[..., Any]:
                result = self.get(f"{func}-{args}-{kwargs}", obj)
                if result == obj:
                    result = func(*args, **kwargs)
                    self.set(f"{func}-{args}-{kwargs}", result, timeout)
                return result

            return wrapper

        obj = object()
        return decorator

    memorize = memoize  # for backwards compatibility

    def ttl(self, key: str) -> int:
        """
        How long the key is still valid in the cache in seconds.
        Returns `-1` if the value for the key does not expire.
        Returns `-2` if the value for the key has expired, or has not been set.

        :param key: Cache key.
        """
        result: tuple[bytes, float] | None = self._con.execute(self._get_sql, {"key": key}).fetchone()

        if result is None:
            return -2

        exp = self._exp_datetime(result[1])
        if exp is None:
            return -1

        ttl = int((exp - datetime.datetime.now(tz=datetime.UTC)).total_seconds())
        if ttl <= 0:
            self._con.execute(self._delete_sql, {"key": key})
            self._con.commit()
            return -2

        return ttl

    def ttl_many(self, keys: list[str]) -> dict[str, int]:
        """
        How long the given keys are still valid in the cache in seconds.
        Returns `-1` if a value for the key does not expire.
        Returns `-2` if a value for the key has expired, or has not been set.

        :param keys: List of cache keys.
        """
        seq = ", ".join([f"'{value}'" for value in keys])
        fetched: list[tuple[str, Any, float]] = self._con.execute(self._get_many_sql.format(seq)).fetchall()
        exp_by_key: dict[str, float] = {key: exp for key, _, exp in fetched}

        results: dict[str, int] = {}
        to_delete: list[str] = []
        for key in keys:
            exp_ = exp_by_key.get(key)
            if exp_ is None:
                results[key] = -2
                continue

            exp = self._exp_datetime(exp_)
            if exp is None:
                results[key] = -1
                continue

            if datetime.datetime.now(tz=datetime.UTC) >= exp:
                to_delete.append(key)
                results[key] = -2
                continue

            results[key] = int((exp - datetime.datetime.now(tz=datetime.UTC)).total_seconds())

        if to_delete:
            self._con.execute(self._delete_many_sql.format(", ".join([f"'{value}'" for value in to_delete])))
            self._con.commit()

        return results

    def _filter_key_result_list(self, unfiltered: list[tuple[str, Any]]) -> list[str]:
        """
        Filters key result list to only those keys for cache items that are still alive,
        and purges expired items from the cache.

        :param unfiltered: A list of key and expiration tuples
        :return: A filtered list of keys
        """
        results: list[str] = []
        to_delete: list[str] = []
        for key, exp in unfiltered:
            exp = self._exp_datetime(exp)  # noqa: PLW2901
            if exp is not None and datetime.datetime.now(tz=datetime.UTC) >= exp:
                to_delete.append(key)
                continue

            results.append(key)

        if to_delete:
            self._con.execute(self._delete_many_sql.format(", ".join([f"'{key}'" for key in to_delete])))
            self._con.commit()

        return results

    def get_all_keys(self) -> list[str]:
        """
        Get all keys that exist in the cache for currently valid cache items.

        :return: List of cache keys in sort order.
        """
        fetched: list[tuple[str, Any]] = self._con.execute(self._get_keys_sql).fetchall()

        if not fetched:
            return []

        return self._filter_key_result_list(fetched)

    def find_matching_keys(self, like_match_pattern: str) -> list[str]:
        """
        Find keys that match a SQL `LIKE` pattern.

        :param like_match_pattern: A string formatted for SQL `LIKE` operator comparison.
        :return: A list of matching keys.
        """
        # Any custom pattern can be used here
        data = {"pattern": like_match_pattern}
        fetched: list[tuple[str, Any]] = self._con.execute(self._find_matching_keys_sql, data).fetchall()
        if not fetched:
            return []

        return self._filter_key_result_list(fetched)

    def find_keys_starting_with(self, pattern: str) -> list[str]:
        """
        Find keys that start with the given pattern.
        Matching follows the SQLite specification for the LIKE operator, so
        it will match 'A' to 'a', but not 'Ä' to 'ä'.
        Will only return keys that exist in the cache for currently valid cache items.

        :param pattern: The pattern to match at the start of the key.
        :return: List of matching cache keys in sort order.
        """
        return self.find_matching_keys(f"{pattern}%")

    def find_keys_ending_with(self, pattern: str) -> list[str]:
        """
        Find keys that end with the given pattern.
        Matching follows the SQLite specification for the LIKE operator, so
        it will match 'A' to 'a', but not 'Ä' to 'ä'.
        Will only return keys that exist in the cache for currently valid cache items.

        :param pattern: The pattern to match at the end of the key.
        :return: List of matching cache keys in sort order.
        """
        return self.find_matching_keys(f"%{pattern}")

    def find_keys_containing(self, pattern: str) -> list[str]:
        """
        Find keys that contain the given pattern anywhere in the string.
        Matching follows the SQLite specification for the LIKE operator, so
        it will match 'A' to 'a', but not 'Ä' to 'ä'.
        Will only return keys that exist in the cache for currently valid cache items.

        :param pattern: The pattern to find in matching keys.
        :return: List of matching cache keys in sort order.
        """
        return self.find_matching_keys(f"%{pattern}%")

    def clear_matching_keys(self, like_match_pattern: str) -> None:
        """
        Clear keys that match a SQL `LIKE` pattern.
        Matching follows the SQLite specification for the LIKE operator, so
        it will match 'A' to 'a', but not 'Ä' to 'ä'.

        :param like_match_pattern: A string formatted for SQL `LIKE` operator comparison.
        """
        data = {"pattern": like_match_pattern}
        self._con.execute(self._clear_keys_matching_sql, data)
        self._con.commit()

    def clear_keys_starting_with(self, pattern: str) -> None:
        """
        Clear keys that start with the given pattern.
        Matching follows the SQLite specification for the LIKE operator, so
        it will match 'A' to 'a', but not 'Ä' to 'ä'.

        :param pattern: The pattern to match at the start of the key.
        """
        return self.clear_matching_keys(f"{pattern}%")

    def clear_keys_ending_with(self, pattern: str) -> None:
        """
        Clear keys that end with the given pattern.
        Matching follows the SQLite specification for the LIKE operator, so
        it will match 'A' to 'a', but not 'Ä' to 'ä'.

        :param pattern: The pattern to match at the end of the key.
        """
        return self.clear_matching_keys(f"%{pattern}")

    def clear_keys_containing(self, pattern: str) -> None:
        """
        Clear keys that contain the given pattern anywhere in the string.
        Matching follows the SQLite specification for the LIKE operator, so
        it will match 'A' to 'a', but not 'Ä' to 'ä'.

        :param pattern: The pattern to find in matching keys.
        """
        return self.clear_matching_keys(f"%{pattern}%")
