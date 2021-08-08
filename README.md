# SQLite Cache

Use [SQLite3](https://docs.python.org/3/library/sqlite3.html) as quick, persistent, thread-safe cache. 
Can store any picklable objects.

```python
from sqlite_cache import cache
```

###  Documentation:

Interface works similarly to [django's cache interface](https://docs.djangoproject.com/en/3.2/topics/cache/#basic-usage) 
(Not all methods have been implemented).

#### *cache.add(...) → None*
- key: str — Cache key.
- value: Any — Picklable object to store.
- timeout: int = DEFAULT_TIMEOUT — How long the value is valid in cache.

Add the value to cache only if key not already in cache, 
or the found value has expired.

---

#### *cache.get(...) → Any*
- key: str — Cache key.
- default: Any = None — Value to return if key not in cache.

Get the value under some key. Return `default` if key not in cache or expired.

---

#### *cache.set(...) → None*
- key: str — Cache key.
- value: Any — Picklable object to store.
- timeout: int = DEFAULT_TIMEOUT — How long the value is valid in cache.

Set a value in cache under some key. Value stays in cache unless even if timeout
is reached, and only gets deleted on the next call to `cache.get`.


---

#### *cache.touch(...) → None*
- key: str — Cache key.
- timeout: int = DEFAULT_TIMEOUT — How long the value is valid in cache.

Extend the lifetime of an object in cache. Does nothing if key not in cache or expired.

---

#### *cache.delete(...) → None*
- key: str — Cache key.

Delete value under key from cache.

---

#### *cache.clear() → None*

Clear cache from all items.

---
