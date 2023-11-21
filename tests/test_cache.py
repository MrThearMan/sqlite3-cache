import sqlite3
from time import perf_counter_ns, sleep
from datetime import datetime, timezone, timedelta

import pytest
from freezegun import freeze_time

from sqlite3_cache import Cache


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_creation(cache):
    assert cache.connection_string == ".cache:?mode=memory&cache=shared"


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_method_failed(cache):
    try:
        cache.set(object(), object())
    except sqlite3.Error:
        pass
    else:
        pytest.fail("Setting to key object() did not raise an error.")


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_set_and_get(cache):
    cache.set("foo", "bar", timeout=1)
    assert cache.get("foo") == "bar"


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_getitem_and_setitem(cache):
    cache["foo"] = "bar"
    assert cache["foo"] == "bar"


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_getitem_key_error(cache):
    try:
        cache["foo"]
    except KeyError as e:
        assert str(e) == "'Key not in cache.'"
    else:
        pytest.fail("Accessing a key not in cache did not raise a KeyError.")


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_delitem(cache):
    cache["foo"] = "bar"
    del cache["foo"]
    assert cache.get("foo") is None


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_context_manager(cache):
    cache["foo"] = "bar"
    cache.close()
    with Cache() as cache:
        value = cache["foo"]
    assert value == "bar"


def test_cache_contains(cache):
    cache["foo"] = "bar"
    assert ("foo" in cache) is True


def test_cache_value_is_available(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set("foo", "bar", timeout=2)
    with freeze_time("2022-01-01T00:00:01+00:00"):
        assert cache.get("foo") == "bar"


def test_cache_value_not_available(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set("foo", "bar", timeout=1)
    with freeze_time("2022-01-01T00:00:01+00:00"):
        assert cache.get("foo") is None


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_value_not_set(cache):
    assert cache.get("foo") is None


def test_cache_value_does_not_expire(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set("foo", "bar", timeout=-1)
    with freeze_time("9999-01-01T00:00:00+00:00"):
        assert cache.get("foo") == "bar"


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_add_and_get(cache):
    cache.add("foo", "bar", timeout=1)
    assert cache.get("foo") == "bar"


def test_cache_add_same_twice_and_get(cache):
    cache.add("foo", "bar", timeout=1)
    cache.add("foo", "baz", timeout=1)
    assert cache.get("foo") == "bar"


def test_cache_add_same_twice_and_get__has_expired(cache):
    cache.add("foo", "bar", timeout=1)
    cache.add("foo", "baz", timeout=1)
    assert cache.get("foo") == "bar"
    sleep(1.1)
    cache.add("foo", "baz", timeout=1)
    assert cache.get("foo") == "baz"


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_add_same_twice_and_get__non_expiring(cache):
    cache.add("foo", "bar", timeout=-1)
    cache.add("foo", "baz", timeout=-1)
    assert cache.get("foo") == "bar"


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_get_default_if_not_exists(cache):
    assert cache.get("foo", "bar") == "bar"


def test_cache_update(cache):
    cache.set("foo", "bar", timeout=10)
    cache.update("foo", "baz")
    assert cache.get("foo") == "baz"


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_update__non_expiring(cache):
    cache.set("foo", "bar", timeout=-1)
    cache.update("foo", "baz")
    assert cache.get("foo") == "baz"


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_update__does_not_exist(cache):
    cache.update("foo", "baz")
    assert cache.get("foo") is None


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_delete(cache):
    cache.set("foo", "bar", timeout=1)
    cache.delete("foo")
    assert cache.get("foo") is None


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_delete__nothing(cache):
    cache.delete("foo")
    assert cache.get("foo") is None


def test_cache_get_or_set(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set("foo", "bar", timeout=2)
    with freeze_time("2022-01-01T00:00:01+00:00"):
        assert cache.get_or_set("foo", None) == "bar"


def test_cache_get_or_set__expired(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set("foo", "bar", timeout=1)
    with freeze_time("2022-01-01T00:00:01+00:00"):
        assert cache.get_or_set("foo", None) is None


def test_cache_get_many(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set("foo", "bar", timeout=2)
        cache.set("one", "two", timeout=2)
    with freeze_time("2022-01-01T00:00:01+00:00"):
        assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


def test_cache_get_many__expired(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set("foo", "bar", timeout=1)
        cache.set("one", "two", timeout=1)
    with freeze_time("2022-01-01T00:00:01+00:00"):
        assert cache.get_many(["foo", "one"]) == {}


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_get_many__nothing(cache):
    cache.set("foo", "bar", timeout=1)
    cache.set("one", "two", timeout=1)
    assert cache.get_many(["three", "four"]) == {}


def test_cache_set_many(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set_many({"foo": "bar", "one": "two"}, timeout=2)
    with freeze_time("2022-01-01T00:00:01+00:00"):
        assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


def test_cache_set_many__expired(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set_many({"foo": "bar", "one": "two"}, timeout=1)
    with freeze_time("2022-01-01T00:00:01+00:00"):
        assert cache.get_many(["foo", "one"]) == {}


def test_cache_add_many(cache):
    cache.set("foo", "bar", timeout=10)
    cache.add_many({"foo": "baz", "one": "two"}, timeout=10)
    assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


def test_cache_add_many__expired(cache):
    cache.set("foo", "bar", timeout=1)
    sleep(1.1)
    cache.add_many({"foo": "baz", "one": "two"}, timeout=1)
    assert cache.get_many(["foo", "one"]) == {"foo": "baz", "one": "two"}


def test_cache_update_many(cache):
    cache.set_many({"foo": "bar", "one": "two"}, timeout=10)
    cache.update_many({"foo": "baz", "three": "four"})
    assert cache.get_many(["foo", "one"]) == {"foo": "baz", "one": "two"}
    assert cache.get("three") is None


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_delete_many(cache):
    cache.set_many({"foo": "bar", "one": "two"}, timeout=1)
    cache.delete_many(["foo", "one"])
    assert cache.get_many(["foo", "one"]) == {}


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_delete_many__nothing(cache):
    cache.delete_many(["foo", "one"])
    assert cache.get_many(["foo", "one"]) == {}


def test_cache_touch(cache):
    cache.set("foo", "bar", timeout=1)
    cache.touch("foo", timeout=3)
    sleep(1.1)
    assert cache.get("foo") == "bar"


def test_cache_touch__make_expiring(cache):
    cache.set("foo", "bar", timeout=-10)
    cache.touch("foo", timeout=1)
    sleep(1.1)
    assert cache.get("foo") is None


def test_cache_touch__non_expiring(cache):
    cache.set("foo", "bar", timeout=1)
    cache.touch("foo", timeout=-1)
    sleep(1.1)
    assert cache.get("foo") == "bar"


def test_cache_touch_many(cache):
    cache.set_many({"foo": "bar", "one": "two"}, timeout=1)
    cache.touch_many(["foo", "one"], timeout=3)
    sleep(1.1)
    assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_clear(cache):
    cache.set("foo", "bar", timeout=1)
    cache.clear()
    assert cache.get("foo") is None


def test_cache_incr(cache):
    cache.set("foo", 1, timeout=10)
    assert cache.incr("foo") == 2


def test_cache_incr__not_exists(cache):
    try:
        cache.incr("foo")
    except ValueError as e:
        assert str(e) == "Nonexistent or expired cache key."
    else:
        pytest.fail("Incrementing a nonexistent key did not raise an error.")


def test_cache_incr__not_a_number(cache):
    cache.set("foo", "bar", timeout=10)
    try:
        cache.incr("foo")
    except ValueError as e:
        assert str(e) == "Value is not a number."
    else:
        pytest.fail("Incrementing a non-number key did not raise an error.")


def test_cache_decr(cache):
    cache.set("foo", 1, timeout=10)
    assert cache.decr("foo") == 0


def test_cache_decr__not_exists(cache):
    try:
        cache.decr("foo")
    except ValueError as e:
        assert str(e) == "Nonexistent or expired cache key."
    else:
        pytest.fail("Decrementing a nonexistent key did not raise an error.")


def test_cache_decr__not_a_number(cache):
    cache.set("foo", "bar", timeout=10)
    try:
        cache.decr("foo")
    except ValueError as e:
        assert str(e) == "Value is not a number."
    else:
        pytest.fail("Decrementing a non-number key did not raise an error.")


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_memoize(cache):

    @cache.memoize()
    def func(a: int, b: int) -> int:
        return a + b

    value1 = func(1, 2)
    value2 = func(1, 3)
    assert value1 != value2

    value3 = None
    try:
        value3 = func(1, 2)
    except Exception as e:
        pytest.fail(str(e))

    assert value1 == value3


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_ttl(cache):
    cache.set("foo", "bar", timeout=10)
    assert cache.ttl("foo") == 10


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_ttl__not_exists(cache):
    assert cache.ttl("foo") == -2


def test_cache_ttl__expired(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set("foo", "bar", timeout=1)
    with freeze_time("2022-01-01T00:00:01+00:00"):
        assert cache.ttl("foo") == -2


def test_cache_ttl__non_expiring(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set("foo", "bar", timeout=-1)
    with freeze_time("9999-01-01T00:00:00+00:00"):
        assert cache.ttl("foo") == -1


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_ttl_many(cache):
    cache.set("foo", "bar", timeout=1)
    cache.set("one", "two", timeout=2)
    assert cache.ttl_many(["foo", "one"]) == {"foo": 1, "one": 2}


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_ttl_many__not_exists(cache):
    assert cache.ttl_many(["foo", "one"]) == {"foo": -2, "one": -2}


@freeze_time("2022-01-01T00:00:00+00:00")
def test_cache_ttl_many__non_expiring(cache):
    cache.set("foo", "bar", timeout=-1)
    cache.set("one", "two", timeout=-2)
    assert cache.ttl_many(["foo", "one"]) == {"foo": -1, "one": -1}


def test_cache_ttl_many__expired(cache):
    with freeze_time("2022-01-01T00:00:00+00:00"):
        cache.set("foo", "bar", timeout=1)
        cache.set("one", "two", timeout=1)
    with freeze_time("2022-01-01T00:00:01+00:00"):
        assert cache.ttl_many(["foo", "one"]) == {"foo": -2, "one": -2}


def test_cache_get_all_keys(cache):
    # empty cache returns empty list
    assert cache.get_all_keys() == []

    # non-empty cache returns some items
    cache.set("foo", "bar", timeout=100)
    cache.set("one", "two", timeout=1)
    cache.set("three", "four", timeout=1)
    cache.set("biz", "buzz", timeout=100)
    # keys are sorted in order
    assert cache.get_all_keys() == ["biz", "foo", "one", "three"]
    sleep(1.1)
    # expired keys are not returned
    assert cache.get_all_keys() == ["biz", "foo"]


@freeze_time("2022-01-01T00:00:00+00:00")
def test__filter_key_result_list(cache):
    def mk_timestamp(delta_secs: int) -> float:
        return (datetime.now(tz=timezone.utc) + timedelta(seconds=delta_secs)).timestamp()

    unfiltered_results = [
        ("foo.bar", mk_timestamp(-2)),
        ("foo.biz", mk_timestamp(-1)),
        ("bar.bar", mk_timestamp(-0)),
        ("bar.foo", mk_timestamp(1)),
        ("biz.bar", mk_timestamp(2))
    ]

    assert cache._filter_key_result_list(unfiltered_results) == ["bar.foo", "biz.bar"]


def test_find_matching_keys(cache):
    # empty cache returns empty list
    assert cache.find_matching_keys("%foo%") == []

    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("foo.foo", "foobar", timeout=-1)
    cache.set("bar.foo", "barfoo", timeout=-1)
    cache.set("bar.bar", "barbar", timeout=-1)

    assert cache.find_matching_keys("foo%") == ["foo.bar", "foo.foo"]
    assert cache.find_matching_keys("%foo") == ["bar.foo", "foo.foo"]
    assert cache.find_matching_keys("%foo%") == ["bar.foo", "foo.bar", "foo.foo"]
    assert cache.find_matching_keys("%biz%") == []


def test_cache_find_keys_starting_with(cache):
    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("foo.foo", "foobar", timeout=-1)
    cache.set("bar.foo", "barfoo", timeout=-1)
    cache.set("bar.bar", "barbar", timeout=-1)
    # keys are returned sorted in order
    assert cache.find_keys_starting_with("foo") == ["foo.bar", "foo.foo"]
    assert cache.find_keys_starting_with("bar") == ["bar.bar", "bar.foo"]
    assert cache.find_keys_starting_with("biz") == []

    cache.clear()

    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("FOO.foo", "foobar", timeout=-1)
    cache.set("bar.bar", "bar", timeout=-1)
    cache.set("BAR.FOO", "foobar", timeout=-1)
    # case-insensitive matching for plain letters
    assert cache.find_keys_starting_with("foo") == ["FOO.foo", "foo.bar"]
    assert cache.find_keys_starting_with("bar") == ["BAR.FOO", "bar.bar"]

    cache.clear()

    cache.set("foo.bar", "bar", timeout=10)
    cache.set("foo.foo", "foobar", timeout=1)
    cache.set("bar.foo", "barfoo", timeout=10)

    sleep(1.1)

    # expired keys are not returned
    assert cache.find_keys_starting_with("foo") == ["foo.bar"]


def test_cache_find_keys_ending_with(cache):
    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("foo.foo", "foobar", timeout=-1)
    cache.set("bar.foo", "barfoo", timeout=-1)
    cache.set("bar.bar", "barbar", timeout=-1)
    # keys are returned sorted in order
    assert cache.find_keys_ending_with("foo") == ["bar.foo", "foo.foo"]
    assert cache.find_keys_ending_with("bar") == ["bar.bar", "foo.bar"]
    assert cache.find_keys_ending_with("biz") == []

    cache.clear()

    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("FOO.foo", "foobar", timeout=-1)
    cache.set("bar.bar", "bar", timeout=-1)
    cache.set("BAR.FOO", "foobar", timeout=-1)
    # case-insensitive matching for plain letters
    assert cache.find_keys_ending_with("foo") == ["BAR.FOO", "FOO.foo"]
    assert cache.find_keys_ending_with("bar") == ["bar.bar", "foo.bar"]

    cache.clear()

    cache.set("foo.bar", "bar", timeout=10)
    cache.set("foo.foo", "foobar", timeout=1)
    cache.set("bar.foo", "barfoo", timeout=10)

    sleep(1.1)

    # expired keys are not returned
    assert cache.find_keys_ending_with("foo") == ["bar.foo"]


def test_cache_find_keys_containing(cache):
    cache.set("foo.bar.biz", "bar", timeout=-1)
    cache.set("foo.foo.bar", "foobar", timeout=-1)
    cache.set("biz.bar.foo", "barfoo", timeout=-1)
    cache.set("bar.biz.bar", "barbar", timeout=-1)
    # keys are returned sorted in order
    assert cache.find_keys_containing("biz") == ["bar.biz.bar", "biz.bar.foo", "foo.bar.biz"]
    assert cache.find_keys_containing("foo") == ["biz.bar.foo", "foo.bar.biz", "foo.foo.bar"]
    assert cache.find_keys_containing("bazz") == []

    cache.clear()

    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("foo.foo", "foobar", timeout=-1)
    cache.set("FOO.bar", "bar", timeout=-1)
    cache.set("FOO.FOO", "foobar", timeout=-1)
    # case-insensitive matching for plain letters
    assert cache.find_keys_containing("foo") == ["FOO.FOO", "FOO.bar", "foo.bar", "foo.foo"]

    cache.clear()

    cache.set("foo.bar", "bar", timeout=10)
    cache.set("foo.foo", "foobar", timeout=1)
    cache.set("bar.foo", "barfoo", timeout=10)

    sleep(1.1)

    # expired keys are not returned
    assert cache.find_keys_containing("foo") == ["bar.foo", "foo.bar"]


def test_clear_matching_keys(cache):
    # empty cache should clear just fine
    assert cache.get_all_keys() == []

    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("foo.foo", "foobar", timeout=-1)
    cache.set("bar.foo", "barfoo", timeout=-1)
    cache.set("bar.bar", "barbar", timeout=-1)
    cache.clear_matching_keys("foo%")
    assert cache.get_all_keys() == ["bar.bar", "bar.foo"]
    cache.clear()

    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("foo.foo", "foobar", timeout=-1)
    cache.set("bar.foo", "barfoo", timeout=-1)
    cache.set("bar.bar", "barbar", timeout=-1)
    cache.clear_matching_keys("%foo")
    assert cache.get_all_keys() == ["bar.bar", "foo.bar"]
    cache.clear()

    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("foo.foo", "foobar", timeout=-1)
    cache.set("bar.foo", "barfoo", timeout=-1)
    cache.set("bar.bar", "barbar", timeout=-1)
    cache.clear_matching_keys("%foo%")
    assert cache.get_all_keys() == ["bar.bar"]
    cache.clear()

    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("foo.foo", "foobar", timeout=-1)
    cache.set("bar.foo", "barfoo", timeout=-1)
    cache.set("bar.bar", "barbar", timeout=-1)
    cache.clear_matching_keys("")
    assert cache.get_all_keys() == ["bar.bar", "bar.foo", "foo.bar", "foo.foo"]


def test_clear_keys_starting_with(cache):
    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("foo.foo", "foobar", timeout=-1)
    cache.set("bar.foo", "barfoo", timeout=-1)
    cache.set("bar.bar", "barbar", timeout=-1)
    cache.clear_keys_starting_with("bar")
    assert cache.get_all_keys() == ["foo.bar", "foo.foo"]


def test_clear_keys_ending_with(cache):
    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("foo.foo", "foobar", timeout=-1)
    cache.set("bar.foo", "barfoo", timeout=-1)
    cache.set("bar.bar", "barbar", timeout=-1)
    cache.clear_keys_ending_with("bar")
    assert cache.get_all_keys() == ["bar.foo", "foo.foo"]


def test_clear_keys_containing(cache):
    cache.set("foo.bar", "bar", timeout=-1)
    cache.set("foo.foo", "foobar", timeout=-1)
    cache.set("bar.foo", "barfoo", timeout=-1)
    cache.set("bar.bar", "barbar", timeout=-1)
    cache.clear_keys_containing("bar")
    assert cache.get_all_keys() == ["foo.foo"]


@pytest.mark.skip("this is a benchmark")
def test_speed():
    start = perf_counter_ns()
    cache = Cache()
    interval1 = perf_counter_ns()

    set_ = []
    get_ = []
    del_ = []

    times = 10_000
    for _ in range(times):
        interval2 = perf_counter_ns()
        cache.set("foo", "bar")
        interval3 = perf_counter_ns()
        value = cache.get("foo")  # noqa
        interval4 = perf_counter_ns()
        cache.delete("foo")
        interval5 = perf_counter_ns()

        set_.append(interval3 - interval2)
        get_.append(interval4 - interval3)
        del_.append(interval5 - interval4)

    set_min = min(set_) / 1000
    get_min = min(get_) / 1000
    del_min = min(del_) / 1000

    set_max = max(set_) / 1000
    get_max = max(get_) / 1000
    del_max = max(del_) / 1000

    creation = (interval1 - start) / 1000
    set_ = sum(set_) / len(set_) / 1000
    get_ = sum(get_) / len(get_) / 1000
    del_ = sum(del_) / len(del_) / 1000

    print(f"\n\n Cache creation: {creation} us\n")  # noqa
    print(f" Average of {times:_}:")  # noqa
    print("--------------------------------------------")  # noqa
    print(f" Set: {set_:.01f}us - Min: {set_min:.01f}us - Max: {set_max:.01f}us")  # noqa
    print(f" Get: {get_:.01f}us - Min: {get_min:.01f}us - Max: {get_max:.01f}us")  # noqa
    print(f" Del: {del_:.01f}us - Min: {del_min:.01f}us - Max: {del_max:.01f}us")  # noqa
    print("--------------------------------------------")  # noqa
