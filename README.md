# SQLite Cache

Use [SQLite3](https://docs.python.org/3/library/sqlite3.html) as quick, persistent, thread-safe cache. 
Can store any picklable objects.

```python
from sqlite_cache import cache
```

###  Documentation:

Interface works similarly to [django's cache interface](https://docs.djangoproject.com/en/3.2/topics/cache/#basic-usage)
with a few additions.

---

#### *cache.add(...) → None*
- key: str — Cache key.
- value: Any — Picklable object to store.
- timeout: int = DEFAULT_TIMEOUT — How long the value is valid in the cache.

Add the value to the cache only if the key is not already in the cache, 
or the found value has expired.

---

#### *cache.get(...) → Any*
- key: str — Cache key.
- default: Any = None — Value to return if key not in the cache.

Get the value under some key. Return `default` if key not in the cache or expired.

---

#### *cache.set(...) → None*
- key: str — Cache key.
- value: Any — Picklable object to store.
- timeout: int = DEFAULT_TIMEOUT — How long the value is valid in the cache.

Set a value in cache under some key. Value stays in the cache unless even if timeout
is reached, and only gets deleted on the next call to `cache.get`.

---

#### *cache.update(...) → None*
- key: str — Cache key.
- value: Any — Picklable object to store.

Update value in the cache. Does nothing if key not in the cache or expired.

---

#### *cache.add_many(...) → None*
- dict_: dict — Cache keys with values to add.
- timeout: int = DEFAULT_TIMEOUT — How long the values are valid in the cache.

For all keys in the given dict, add the value to the cache only if the key is not 
already in the cache, or the found value has expired.

---

#### *cache.get_many(...) → dict*
- keys: str — List of cache keys.

Get all values that exist and aren't expired from the given cache keys, and return a dict.

---

#### *cache.set_many(...) → None*
- dict_: dict — Cache keys with values to set.
- timeout: int = DEFAULT_TIMEOUT — How long the values are valid in the cache.

Set values to the cache for all keys in the given dict.

---

#### *cache.delete_many(...) → None*
- keys: str — List of cache keys.

Remove all the values under the given keys from the cache.

---

#### *cache.update_many(...) → None*
- dict_: dict — Cache keys with values to update to.

Update values to the cache for all keys in the given dict. Does nothing if key not in cache or expired.

---

#### *cache.touch(...) → None*
- key: str — Cache key.
- timeout: int = DEFAULT_TIMEOUT — How long the value is valid in cache.

Extend the lifetime of an object in cache. Does nothing if key not in the cache or expired.

---

#### *cache.delete(...) → None*
- key: str — Cache key.

Remove the value under the given key from the cache.

---

#### *cache.clear() → None*

Clear the cache from all values.

---

#### *cache.incr() → None*
- key: str — Cache key.
- delta: int = 1 — How much to increment.

Increment the value in cache by the given delta.
Note that this is not an atomic transaction!

---

#### *cache.decr() → None*
- key: str — Cache key.
- delta: int = 1 — How much to decrement.

Decrement the value in cache by the given delta.
Note that this is not an atomic transaction!

---
