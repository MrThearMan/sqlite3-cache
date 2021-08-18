import sqlite3
import pickle
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from functools import wraps


__all__ = ["Cache"]


class Cache:

    DEFAULT_TIMEOUT = 300

    _create_sql = (
        "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value BLOB, exp FLOAT)"
    )
    _create_index_sql = (
        "CREATE UNIQUE INDEX IF NOT EXISTS cache_key ON cache(key)"
    )
    _set_mmap_size = (
        "PRAGMA mmap_size={};"
    )
    _set_to_wal_mode = (
        "PRAGMA journal_mode=WAL;"
    )
    _set_wal_autocheckpoint = (
        "PRAGMA wal_autocheckpoint={};"
    )
    _set_auto_vacuum = (
        "PRAGMA auto_vacuum=1;"  # Full
    )
    _set_synchronous = (
        "PRAGMA synchronous=1"  # Normal
    )
    _set_cache_size = (
        "PRAGMA cache_size={}"
    )

    _add_sql = (
        "INSERT INTO cache (key, value, exp) VALUES (:key, :value, :exp) "
        "ON CONFLICT(key) DO UPDATE SET value=:value, exp=:exp "
        "WHERE DATETIME(exp, 'unixepoch') <= DATETIME('now')"
    )
    _get_sql = (
        "SELECT value, exp FROM cache WHERE key=:key"
    )
    _set_sql = (
        "INSERT INTO cache (key, value, exp) VALUES (:key, :value, :exp) "
        "ON CONFLICT(key) DO UPDATE SET value=:value, exp=:exp"
    )
    _check_sql = (
        "SELECT value, exp FROM cache WHERE key=:key AND DATETIME(exp, 'unixepoch') > DATETIME('now')"
    )
    _update_sql = (
        "UPDATE cache SET value=:value WHERE key=:key AND DATETIME(exp, 'unixepoch') > DATETIME('now')"
    )

    # TODO: add 'RETURNING COUNT(*)!=0' to these when sqlite3 version >=3.35.0
    _delete_sql = (
        "DELETE FROM cache WHERE key=:key"
    )
    _touch_sql = (
        "UPDATE cache SET exp=:exp WHERE key=:key AND DATETIME(exp, 'unixepoch') > DATETIME('now')"
    )
    _clear_sql = (
        "DELETE FROM cache"
    )

    _add_many_sql = (
        "INSERT INTO cache (key, value, exp) VALUES {}"
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, exp=excluded.exp "
        "WHERE DATETIME(exp, 'unixepoch') <= DATETIME('now')"
    )
    _get_many_sql = (
        "SELECT key, value, exp FROM cache WHERE key IN ({})"
    )
    _set_many_sql = (
        "INSERT INTO cache (key, value, exp) VALUES {}"
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, exp=excluded.exp"
    )
    _delete_many_sql = (
        "DELETE FROM cache WHERE key IN ({})"
    )

    def __init__(
        self,
        *,
        filename: str = ".cache",
        path: str = None,
        in_memory: bool = True,
        memory_map_size: int = 2 ** 26,  # 64 MB
        cache_size: int = 2 ** 13,  # 8,192 pages
        wal_max_pages: int = 1000,
    ):
        """Create a cache with sqlite3.

        :param filename: Cache file name.
        :param path: Path string to the wanted db location. If None, use current directory.
        :param in_memory: Create database in-memory only. File is still created, but nothing is stored in it.
        :param memory_map_size: The maximum number of bytes that are set aside for memory-mapped
                                I/O on a single database.
        :param cache_size: The maximum number of database disk pages that SQLite will hold in
                           memory at once per open database file.
        :param wal_max_pages: A write-ahead log (WAL) checkpoint will be run automatically whenever
                              the WAL equals or exceeds this many pages in length. Setting the
                              auto-checkpoint size to zero or a negative value turns auto-checkpointing off.
        """

        self.filepath = filename if path is None else str(Path(path) / filename)
        self.suffix = ":?mode=memory&cache=shared" if in_memory else ""
        self.connection_string = f"{self.filepath}{self.suffix}"

        self.con = sqlite3.connect(self.connection_string)
        self.cur = self.con.cursor()
        self.cur.execute(self._create_sql)
        self.cur.execute(self._create_index_sql)
        self.cur.execute(self._set_mmap_size.format(memory_map_size))
        self.cur.execute(self._set_to_wal_mode)
        self.cur.execute(self._set_wal_autocheckpoint.format(wal_max_pages))
        self.cur.execute(self._set_cache_size.format(cache_size))
        self.cur.execute(self._set_synchronous)
        self.cur.execute(self._set_auto_vacuum)
        self.con.commit()

    def __del__(self):
        self.con.close()

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
        self.cur.execute(self._add_sql, data)
        self.con.commit()

    def get(self, key: str, default: Any = None) -> Any:
        self.cur.execute(self._get_sql, {"key": key})
        result: Optional[tuple] = self.cur.fetchone()

        if result is None:
            return default

        exp = datetime.utcfromtimestamp(result[1])

        if datetime.utcnow() >= exp:
            self.cur.execute(self._delete_sql, {"key": key})
            self.con.commit()
            return default

        return self._unstream(result[0])

    def set(self, key: str, value: Any, timeout: int = DEFAULT_TIMEOUT) -> None:
        data = {"key": key, "value": self._stream(value), "exp": self._exp_timestamp(timeout)}
        self.cur.execute(self._set_sql, data)
        self.con.commit()

    def update(self, key: str, value: Any) -> None:
        data = {"key": key, "value": self._stream(value)}
        self.cur.execute(self._update_sql, data)
        self.con.commit()

    def add_many(self, dict_: dict, timeout: int = DEFAULT_TIMEOUT) -> None:
        command = self._add_many_sql.format(
            ", ".join([f"(:key{n}, :value{n}, :exp{n})" for n in range(len(dict_))])
        )

        data = {}
        for i, (key, value) in enumerate(dict_.items()):
            data[f"key{i}"] = key
            data[f"value{i}"] = self._stream(value)
            data[f"exp{i}"] = self._exp_timestamp(timeout)

        self.cur.execute(command, data)
        self.con.commit()

    def get_or_set(self, key: str, default: Any, timeout: int = DEFAULT_TIMEOUT) -> Any:
        self.cur.execute(self._get_sql, {"key": key})
        result: Optional[tuple] = self.cur.fetchone()

        if result is not None:
            exp = datetime.utcfromtimestamp(result[1])

            if datetime.utcnow() >= exp:
                self.cur.execute(self._delete_sql, {"key": key})
            else:
                return self._unstream(result[0])

        data = {"key": key, "value": self._stream(default), "exp": self._exp_timestamp(timeout)}
        self.cur.execute(self._set_sql, data)
        self.con.commit()
        return default

    def get_many(self, keys: list) -> dict:
        self.cur.execute(self._get_many_sql.format(", ".join([f"'{value}'" for value in keys])))
        fetched: list = self.cur.fetchall()

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
            self.cur.execute(self._delete_many_sql.format(", ".join([f"'{value}'" for value in to_delete])))
            self.con.commit()

        return results

    def set_many(self, dict_: dict, timeout: int = DEFAULT_TIMEOUT) -> None:
        command = self._set_many_sql.format(
            ", ".join([f"(:key{n}, :value{n}, :exp{n})" for n in range(len(dict_))])
        )

        data = {}
        for i, (key, value) in enumerate(dict_.items()):
            data[f"key{i}"] = key
            data[f"value{i}"] = self._stream(value)
            data[f"exp{i}"] = self._exp_timestamp(timeout)

        self.cur.execute(command, data)
        self.con.commit()

    def delete_many(self, keys: list) -> None:
        self.cur.execute(self._delete_many_sql.format(", ".join([f"'{value}'" for value in keys])))
        self.con.commit()

    def update_many(self, dict_: dict):
        for key, value in dict_.items():
            data = {"key": key, "value": self._stream(value)}
            self.cur.execute(self._update_sql, data)
        self.con.commit()

    def touch(self, key: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        data = {"exp": self._exp_timestamp(timeout), "key": key}
        self.cur.execute(self._touch_sql, data)
        self.con.commit()

    def delete(self, key: str) -> None:
        self.cur.execute(self._delete_sql, {"key": key})
        self.con.commit()

    def clear(self) -> None:
        self.cur.execute(self._clear_sql)
        self.con.commit()

    def incr(self, key: str, delta: int = 1) -> None:
        self.cur.execute(self._check_sql, {"key": key})
        result: Optional[tuple] = self.cur.fetchone()

        if result is None:
            raise ValueError("Nonexistent or expired cache key.")

        value = self._unstream(result[0])
        if not isinstance(value, int):
            raise ValueError("Value is not a number.")

        data = {"key": key, "value": self._stream(value + delta)}
        self.cur.execute(self._update_sql, data)
        self.con.commit()

    def decr(self, key: str, delta: int = 1) -> None:
        self.cur.execute(self._check_sql, {"key": key})
        result: Optional[tuple] = self.cur.fetchone()

        if result is None:
            raise ValueError("Nonexistent or expired cache key.")

        value = self._unstream(result[0])
        if not isinstance(value, int):
            raise ValueError("Value is not a number.")

        data = {"key": key, "value": self._stream(value - delta)}
        self.cur.execute(self._update_sql, data)
        self.con.commit()
