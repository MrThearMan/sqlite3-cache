# API Reference


#### *Cache(...) → Cache*
- filename: str = ".cache" - Cache file name.
- path: str = None - Path string to the wanted db location. If None, use current directory.
- in_memory: bool = True - Create database in-memory only. File is still created, but
  nothing is stored in it.
- timeout: int - How long to wait for another connection to finnish executing before throwing an exception.
- kwargs: Pragma settings. https://www.sqlite.org/pragma.html

Create a new cache in the specified location. The class itself is not a singleton, but cache
intances with the same filename and path will share the same cache, and the latter instance
will not clear the cache on instantiation.

---

#### *cache.add(...) → None*
- key: str — Cache key.
- value: Any — Picklable object to store.
- timeout: int = DEFAULT_TIMEOUT — How long the value is valid in the cache.

Set the value to the cache only if the key is not already in the cache,
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

Set a value in cache under some key.

---

#### *cache.update(...) → None*
- key: str — Cache key.
- value: Any — Picklable object to store.

Update value in the cache. Does nothing if key not in the cache or expired.

---

#### *cache.touch(...) → None*
- key: str — Cache key.
- timeout: int = DEFAULT_TIMEOUT — How long the value is valid in cache.

Extend the lifetime of an object in cache. Does nothing if key is not in the cache or is expired.

---

#### *cache.delete(...) → None*
- key: str — Cache key.

Remove the value under the given key from the cache.

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

#### *cache.update_many(...) → None*
- dict_: dict — Cache keys with values to update to.

Update values to the cache for all keys in the given dict. Does nothing if key not in cache or expired.

---

#### *cache.touch_many(...) → None*
- keys: str — List of cache keys.
- timeout: int = DEFAULT_TIMEOUT — How long the value is valid in cache.

Extend the lifetime for all objects under the given keys in cache.
Does nothing if a key is not in the cache or is expired.

---

#### *cache.delete_many(...) → None*
- keys: str — List of cache keys.

Remove all the values under the given keys from the cache.

---

#### *cache.get_or_set(...) → Any*
- key: str — Cache key.
- default: Any — Picklable object to store if key is not in cache.
- timeout: int = DEFAULT_TIMEOUT — How long the value is valid in the cache.

Get a value under some key, or set the default if key is not in cache.

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

#### *@cache.memorize()*
- timeout: int = DEFAULT_TIMEOUT — How long the value is valid in the cache.

Save the result of the decorated function in cache. Calls with different
arguments are saved under different keys.

---
