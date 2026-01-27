from types import NoneType
from typing import Set, Type

import pytest

from jmux.awaitable import (
    AwaitableValue,
    IAsyncSink,
    SinkType,
    StreamableValues,
)
from jmux.demux import JMux
from jmux.error import NothingEmittedError, SinkClosedError


class NestedObject(JMux):
    key: AwaitableValue[str]


@pytest.mark.parametrize(
    "TargetType,expected_set",
    [
        (AwaitableValue[int], {int}),
        (AwaitableValue[float], {float}),
        (AwaitableValue[str], {str}),
        (AwaitableValue[bool], {bool}),
        (AwaitableValue[NestedObject], {NestedObject}),
        (AwaitableValue[int | None], {int, NoneType}),
        (AwaitableValue[float | None], {float, NoneType}),
        (AwaitableValue[str | None], {str, NoneType}),
        (AwaitableValue[bool | None], {bool, NoneType}),
        (AwaitableValue[NestedObject | None], {NestedObject, NoneType}),
        (StreamableValues[int], {int}),
        (StreamableValues[float], {float}),
        (StreamableValues[str], {str}),
        (StreamableValues[bool], {bool}),
        (StreamableValues[NestedObject], {NestedObject}),
    ],
)
def test_underlying_generic_mixin__get_underlying_generic__expected_set(
    TargetType: Type[IAsyncSink], expected_set: Set[Type]
):
    target = TargetType()
    underlying_types = target.get_underlying_generics()

    assert underlying_types == expected_set


@pytest.mark.parametrize(
    "TargetType,MaybeExpectedError",
    [
        (AwaitableValue[int], None),
        (AwaitableValue[str], None),
        (AwaitableValue[float], None),
        (AwaitableValue[bool], None),
        (AwaitableValue[NoneType], None),
        (AwaitableValue[NestedObject | None], None),
        (AwaitableValue[int | NoneType], None),
        (AwaitableValue[str | NoneType], None),
        (AwaitableValue[float | NoneType], None),
        (AwaitableValue[bool | NoneType], None),
        (AwaitableValue[bool | str | NoneType], TypeError),
        (AwaitableValue[bool | str], TypeError),
        (AwaitableValue[NestedObject | str], TypeError),
        (StreamableValues[int | None], TypeError),
        (StreamableValues[float | None], TypeError),
        (StreamableValues[str | None], TypeError),
        (StreamableValues[bool | None], TypeError),
        (StreamableValues[NestedObject | None], TypeError),
    ],
)
def test_underlying_generic_mixin__get_underlying_generic__check_instantiation(
    TargetType: Type[IAsyncSink], MaybeExpectedError: Type[Exception] | None
):
    target = TargetType()
    if MaybeExpectedError:
        with pytest.raises(MaybeExpectedError):
            _ = target.get_underlying_generics()
    else:
        _ = target.get_underlying_generics()


@pytest.mark.anyio
async def test_awaitable_value__double_put_raises_value_error():
    av = AwaitableValue[int]()
    await av.put(42)
    with pytest.raises(ValueError, match="can only be set once"):
        await av.put(100)


@pytest.mark.anyio
async def test_awaitable_value__get_current_before_set_raises_value_error():
    av = AwaitableValue[int]()
    with pytest.raises(ValueError, match="has not been set yet"):
        av.get_current()


@pytest.mark.anyio
async def test_awaitable_value__close_without_value_non_optional_raises_nothing_emitted_error():
    av = AwaitableValue[int]()
    with pytest.raises(NothingEmittedError, match="without a value"):
        await av.close()


@pytest.mark.anyio
async def test_awaitable_value__close_without_value_optional_succeeds():
    av = AwaitableValue[int | None]()
    await av.close()
    assert av._is_closed is True


@pytest.mark.anyio
async def test_awaitable_value__double_close_raises_sink_closed_error():
    av = AwaitableValue[int]()
    await av.put(42)
    await av.close()
    with pytest.raises(SinkClosedError, match="already closed"):
        await av.close()


@pytest.mark.anyio
async def test_awaitable_value__put_after_close_raises_value_error():
    av = AwaitableValue[int]()
    await av.put(42)
    await av.close()
    with pytest.raises(ValueError, match="can only be set once"):
        await av.put(100)


@pytest.mark.anyio
async def test_awaitable_value__get_sink_type_returns_awaitable_value():
    av = AwaitableValue[int]()
    assert av.get_sink_type() == SinkType.AWAITABLE_VALUE


@pytest.mark.anyio
async def test_awaitable_value__ensure_closed_is_idempotent():
    av = AwaitableValue[int]()
    await av.put(42)
    await av.ensure_closed()
    await av.ensure_closed()
    await av.ensure_closed()
    assert av._is_closed is True


@pytest.mark.anyio
async def test_awaitable_value__ensure_closed_without_value_non_optional_raises():
    av = AwaitableValue[str]()
    with pytest.raises(NothingEmittedError):
        await av.ensure_closed()


@pytest.mark.anyio
async def test_awaitable_value__await_returns_correct_value():
    av = AwaitableValue[str]()
    await av.put("hello")
    result = await av
    assert result == "hello"


@pytest.mark.anyio
async def test_awaitable_value__await_optional_none_value():
    av = AwaitableValue[str | None]()
    await av.close()
    result = await av
    assert result is None


@pytest.mark.anyio
async def test_awaitable_value__get_current_after_put():
    av = AwaitableValue[float]()
    await av.put(3.14)
    assert av.get_current() == 3.14


@pytest.mark.anyio
async def test_awaitable_value__get_underlying_main_generic_single_type():
    av = AwaitableValue[int]()
    assert av.get_underlying_main_generic() is int


@pytest.mark.anyio
async def test_awaitable_value__get_underlying_main_generic_optional():
    av = AwaitableValue[str | None]()
    assert av.get_underlying_main_generic() is str


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        999999999,
        -999999999,
    ],
)
@pytest.mark.anyio
async def test_awaitable_value__various_int_values(value: int):
    av = AwaitableValue[int]()
    await av.put(value)
    assert av.get_current() == value
    assert await av == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "hello",
        "hello world",
        "unicode: こんにちは",
        "emoji: 🎉",
        "a" * 10000,
    ],
)
@pytest.mark.anyio
async def test_awaitable_value__various_string_values(value: str):
    av = AwaitableValue[str]()
    await av.put(value)
    assert av.get_current() == value
    assert await av == value


@pytest.mark.anyio
async def test_awaitable_value__bool_true():
    av = AwaitableValue[bool]()
    await av.put(True)
    assert av.get_current() is True


@pytest.mark.anyio
async def test_awaitable_value__bool_false():
    av = AwaitableValue[bool]()
    await av.put(False)
    assert av.get_current() is False


@pytest.mark.anyio
async def test_awaitable_value__nested_object():
    av = AwaitableValue[NestedObject]()
    nested = NestedObject()
    await av.put(nested)
    assert av.get_current() is nested


@pytest.mark.anyio
async def test_streamable_values__put_after_close_raises_value_error():
    sv = StreamableValues[int]()
    await sv.close()
    with pytest.raises(ValueError, match="closed sink"):
        await sv.put(42)


@pytest.mark.anyio
async def test_streamable_values__get_current_before_items_raises_value_error():
    sv = StreamableValues[int]()
    with pytest.raises(ValueError, match="not received any items"):
        sv.get_current()


@pytest.mark.anyio
async def test_streamable_values__double_close_raises_sink_closed_error():
    sv = StreamableValues[int]()
    await sv.close()
    with pytest.raises(SinkClosedError, match="already closed"):
        await sv.close()


@pytest.mark.anyio
async def test_streamable_values__get_sink_type_returns_streamable_values():
    sv = StreamableValues[int]()
    assert sv.get_sink_type() == SinkType.STREAMABLE_VALUES


@pytest.mark.anyio
async def test_streamable_values__ensure_closed_is_idempotent():
    sv = StreamableValues[str]()
    await sv.put("a")
    await sv.ensure_closed()
    await sv.ensure_closed()
    await sv.ensure_closed()
    assert sv._closed is True


@pytest.mark.anyio
async def test_streamable_values__aiter_yields_all_items():
    sv = StreamableValues[int]()
    await sv.put(1)
    await sv.put(2)
    await sv.put(3)
    await sv.close()

    items = []
    async for item in sv:
        items.append(item)

    assert items == [1, 2, 3]


@pytest.mark.anyio
async def test_streamable_values__empty_stream_iteration():
    sv = StreamableValues[int]()
    await sv.close()

    items = []
    async for item in sv:
        items.append(item)

    assert items == []


@pytest.mark.anyio
async def test_streamable_values__large_number_of_items():
    sv = StreamableValues[int]()
    count = 1000
    for i in range(count):
        await sv.put(i)
    await sv.close()

    items = []
    async for item in sv:
        items.append(item)

    assert items == list(range(count))


@pytest.mark.anyio
async def test_streamable_values__get_current_returns_last_item():
    sv = StreamableValues[str]()
    await sv.put("first")
    assert sv.get_current() == "first"
    await sv.put("second")
    assert sv.get_current() == "second"
    await sv.put("third")
    assert sv.get_current() == "third"


@pytest.mark.anyio
async def test_streamable_values__get_underlying_main_generic():
    sv = StreamableValues[float]()
    assert sv.get_underlying_main_generic() is float


@pytest.mark.parametrize(
    "values",
    [
        [1],
        [1, 2],
        [1, 2, 3, 4, 5],
        list(range(100)),
    ],
)
@pytest.mark.anyio
async def test_streamable_values__various_list_lengths(values: list):
    sv = StreamableValues[int]()
    for v in values:
        await sv.put(v)
    await sv.close()

    items = []
    async for item in sv:
        items.append(item)

    assert items == values


@pytest.mark.parametrize(
    "value",
    [
        "",
        "hello",
        "unicode: 日本語",
        "emoji: 🚀🎉",
    ],
)
@pytest.mark.anyio
async def test_streamable_values__various_string_values(value: str):
    sv = StreamableValues[str]()
    await sv.put(value)
    assert sv.get_current() == value


@pytest.mark.anyio
async def test_streamable_values__float_values():
    sv = StreamableValues[float]()
    await sv.put(1.5)
    await sv.put(2.5)
    await sv.put(3.5)
    await sv.close()

    items = []
    async for item in sv:
        items.append(item)

    assert items == [1.5, 2.5, 3.5]


@pytest.mark.anyio
async def test_streamable_values__bool_values():
    sv = StreamableValues[bool]()
    await sv.put(True)
    await sv.put(False)
    await sv.put(True)
    await sv.close()

    items = []
    async for item in sv:
        items.append(item)

    assert items == [True, False, True]


@pytest.mark.anyio
async def test_streamable_values__nested_objects():
    sv = StreamableValues[NestedObject]()
    obj1 = NestedObject()
    obj2 = NestedObject()
    await sv.put(obj1)
    await sv.put(obj2)
    await sv.close()

    items = []
    async for item in sv:
        items.append(item)

    assert items == [obj1, obj2]


@pytest.mark.anyio
async def test_streamable_values__get_current_after_close():
    sv = StreamableValues[int]()
    await sv.put(42)
    await sv.close()
    assert sv.get_current() == 42


@pytest.mark.anyio
async def test_awaitable_value__close_after_put_succeeds():
    av = AwaitableValue[int]()
    await av.put(42)
    await av.close()
    result = await av
    assert result == 42


@pytest.mark.anyio
async def test_awaitable_value__get_underlying_main_generic_nested_object():
    av = AwaitableValue[NestedObject]()
    assert av.get_underlying_main_generic() is NestedObject


@pytest.mark.anyio
async def test_streamable_values__aiter_string_values():
    sv = StreamableValues[str]()
    await sv.put("hello")
    await sv.put("world")
    await sv.close()

    items = []
    async for item in sv:
        items.append(item)

    assert items == ["hello", "world"]


@pytest.mark.anyio
async def test_streamable_values__get_underlying_main_generic_string_type():
    sv = StreamableValues[str]()
    assert sv.get_underlying_main_generic() is str
