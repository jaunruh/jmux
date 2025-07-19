import asyncio
import json
import os
from asyncio import gather, wait_for
from enum import Enum
from types import NoneType
from typing import List, Optional, Type

import pytest

from jmux.awaitable import AwaitableValue, StreamableValues
from jmux.demux import JMux
from jmux.error import (
    NotAllObjectPropertiesSetError,
)


class AsyncStreamGenerator:
    stream: str

    def __init__(self, stream):
        self.stream = stream

    async def __anext__(self):
        raise Exception("This method is not implemented")

    async def __aiter__(self):
        for char in self.stream:
            yield char
            await asyncio.sleep(0)


LOG_EMITS = os.environ.get("LOG_EMITS", "0") == "1"


def log_emit(message: str):
    if LOG_EMITS:
        print(message)


@pytest.mark.parametrize(
    "stream,expected_operations",
    [
        (
            '{"city_name":"Paris","country":"France"}',
            [
                "[producer] sending: {",
                '[producer] sending: "',
                "[producer] sending: c",
                "[producer] sending: i",
                "[producer] sending: t",
                "[producer] sending: y",
                "[producer] sending: _",
                "[producer] sending: n",
                "[producer] sending: a",
                "[producer] sending: m",
                "[producer] sending: e",
                '[producer] sending: "',
                "[producer] sending: :",
                '[producer] sending: "',
                "[producer] sending: P",
                "[city] received: P",
                "[producer] sending: a",
                "[city] received: a",
                "[producer] sending: r",
                "[city] received: r",
                "[producer] sending: i",
                "[city] received: i",
                "[producer] sending: s",
                "[city] received: s",
                '[producer] sending: "',
                "[producer] sending: ,",
                '[producer] sending: "',
                "[producer] sending: c",
                "[producer] sending: o",
                "[producer] sending: u",
                "[producer] sending: n",
                "[producer] sending: t",
                "[producer] sending: r",
                "[producer] sending: y",
                '[producer] sending: "',
                "[producer] sending: :",
                '[producer] sending: "',
                "[producer] sending: F",
                "[country] received: F",
                "[producer] sending: r",
                "[country] received: r",
                "[producer] sending: a",
                "[country] received: a",
                "[producer] sending: n",
                "[country] received: n",
                "[producer] sending: c",
                "[country] received: c",
                "[producer] sending: e",
                "[country] received: e",
                '[producer] sending: "',
                "[producer] sending: }",
            ],
        ),
        (
            '{"city_name": "Paris", "country": "France"}',
            [
                "[producer] sending: {",
                '[producer] sending: "',
                "[producer] sending: c",
                "[producer] sending: i",
                "[producer] sending: t",
                "[producer] sending: y",
                "[producer] sending: _",
                "[producer] sending: n",
                "[producer] sending: a",
                "[producer] sending: m",
                "[producer] sending: e",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending:  ",
                '[producer] sending: "',
                "[producer] sending: P",
                "[city] received: P",
                "[producer] sending: a",
                "[city] received: a",
                "[producer] sending: r",
                "[city] received: r",
                "[producer] sending: i",
                "[city] received: i",
                "[producer] sending: s",
                "[city] received: s",
                '[producer] sending: "',
                "[producer] sending: ,",
                "[producer] sending:  ",
                '[producer] sending: "',
                "[producer] sending: c",
                "[producer] sending: o",
                "[producer] sending: u",
                "[producer] sending: n",
                "[producer] sending: t",
                "[producer] sending: r",
                "[producer] sending: y",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending:  ",
                '[producer] sending: "',
                "[producer] sending: F",
                "[country] received: F",
                "[producer] sending: r",
                "[country] received: r",
                "[producer] sending: a",
                "[country] received: a",
                "[producer] sending: n",
                "[country] received: n",
                "[producer] sending: c",
                "[country] received: c",
                "[producer] sending: e",
                "[country] received: e",
                '[producer] sending: "',
                "[producer] sending: }",
            ],
        ),
        (
            '{\n\t"city_name": "Paris",\n\t"country": "France"\n}',
            [
                "[producer] sending: {",
                "[producer] sending: \n",
                "[producer] sending: \t",
                '[producer] sending: "',
                "[producer] sending: c",
                "[producer] sending: i",
                "[producer] sending: t",
                "[producer] sending: y",
                "[producer] sending: _",
                "[producer] sending: n",
                "[producer] sending: a",
                "[producer] sending: m",
                "[producer] sending: e",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending:  ",
                '[producer] sending: "',
                "[producer] sending: P",
                "[city] received: P",
                "[producer] sending: a",
                "[city] received: a",
                "[producer] sending: r",
                "[city] received: r",
                "[producer] sending: i",
                "[city] received: i",
                "[producer] sending: s",
                "[city] received: s",
                '[producer] sending: "',
                "[producer] sending: ,",
                "[producer] sending: \n",
                "[producer] sending: \t",
                '[producer] sending: "',
                "[producer] sending: c",
                "[producer] sending: o",
                "[producer] sending: u",
                "[producer] sending: n",
                "[producer] sending: t",
                "[producer] sending: r",
                "[producer] sending: y",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending:  ",
                '[producer] sending: "',
                "[producer] sending: F",
                "[country] received: F",
                "[producer] sending: r",
                "[country] received: r",
                "[producer] sending: a",
                "[country] received: a",
                "[producer] sending: n",
                "[country] received: n",
                "[producer] sending: c",
                "[country] received: c",
                "[producer] sending: e",
                "[country] received: e",
                '[producer] sending: "',
                "[producer] sending: \n",
                "[producer] sending: }",
            ],
        ),
    ],
)
@pytest.mark.anyio
async def test_json_demux__simple_json(stream: str, expected_operations: List[str]):
    class SCityName(JMux):
        city_name: StreamableValues[str]
        country: StreamableValues[str]

    llm_stream = AsyncStreamGenerator(stream)
    s_city = SCityName()

    city_name = ""
    country = ""
    operation_list = []

    async def consume_city():
        nonlocal city_name
        async for ch in s_city.city_name:
            op = f"[city] received: {ch}"
            log_emit(op)
            operation_list.append(op)
            city_name += ch

    async def consume_country():
        nonlocal country
        async for ch in s_city.country:
            op = f"[country] received: {ch}"
            log_emit(op)
            operation_list.append(op)
            country += ch

    async def produce():
        async for ch in llm_stream:
            op = f"[producer] sending: {ch}"
            log_emit(op)
            operation_list.append(op)
            await s_city.feed_char(ch)
            # Yield control to allow other tasks to run
            # Necessary in the tests only, for API calls this is not needed
            await asyncio.sleep(0)

    await gather(
        produce(),
        consume_city(),
        consume_country(),
    )

    parsed_json = json.loads(stream)

    assert parsed_json["city_name"] == city_name
    assert parsed_json["country"] == country

    assert operation_list == expected_operations


@pytest.mark.parametrize(
    "stream,expected_operations",
    [
        (
            '{"emojis":"😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍😘🥰😗😙😚"}',
            [
                "[producer] sending: {",
                '[producer] sending: "',
                "[producer] sending: e",
                "[producer] sending: m",
                "[producer] sending: o",
                "[producer] sending: j",
                "[producer] sending: i",
                "[producer] sending: s",
                '[producer] sending: "',
                "[producer] sending: :",
                '[producer] sending: "',
                "[producer] sending: 😀",
                "[emojis] received: 😀",
                "[producer] sending: 😃",
                "[emojis] received: 😃",
                "[producer] sending: 😄",
                "[emojis] received: 😄",
                "[producer] sending: 😁",
                "[emojis] received: 😁",
                "[producer] sending: 😆",
                "[emojis] received: 😆",
                "[producer] sending: 😅",
                "[emojis] received: 😅",
                "[producer] sending: 😂",
                "[emojis] received: 😂",
                "[producer] sending: 🤣",
                "[emojis] received: 🤣",
                "[producer] sending: 😊",
                "[emojis] received: 😊",
                "[producer] sending: 😇",
                "[emojis] received: 😇",
                "[producer] sending: 🙂",
                "[emojis] received: 🙂",
                "[producer] sending: 🙃",
                "[emojis] received: 🙃",
                "[producer] sending: 😉",
                "[emojis] received: 😉",
                "[producer] sending: 😌",
                "[emojis] received: 😌",
                "[producer] sending: 😍",
                "[emojis] received: 😍",
                "[producer] sending: 😘",
                "[emojis] received: 😘",
                "[producer] sending: 🥰",
                "[emojis] received: 🥰",
                "[producer] sending: 😗",
                "[emojis] received: 😗",
                "[producer] sending: 😙",
                "[emojis] received: 😙",
                "[producer] sending: 😚",
                "[emojis] received: 😚",
                '[producer] sending: "',
                "[producer] sending: }",
            ],
        )
    ],
)
@pytest.mark.anyio
async def test_json_demux__utf8(stream: str, expected_operations: List[str]):
    class SEmojis(JMux):
        emojis: StreamableValues[str]

    llm_stream = AsyncStreamGenerator(stream)
    s_emoji = SEmojis()

    emojis = ""
    operation_list = []

    async def consume_emojis():
        nonlocal emojis
        async for ch in s_emoji.emojis:
            op = f"[emojis] received: {ch}"
            operation_list.append(op)
            emojis += ch

    async def produce():
        async for ch in llm_stream:
            op = f"[producer] sending: {ch}"
            operation_list.append(op)
            await s_emoji.feed_char(ch)
            # Yield control to allow other tasks to run
            # Necessary in the tests only, for API calls this is not needed
            await asyncio.sleep(0)

    await gather(
        produce(),
        consume_emojis(),
    )

    parsed_json = json.loads(stream)

    assert emojis == parsed_json["emojis"]
    assert operation_list == expected_operations


@pytest.mark.parametrize(
    "stream,expected_operations",
    [
        (
            '{"my_str":"foo","my_int":42,"my_float":3.14,"my_bool":true,"my_enum":"value1","my_none":null}',
            [
                "[producer] sending: {",
                '[producer] sending: "',
                "[producer] sending: m",
                "[producer] sending: y",
                "[producer] sending: _",
                "[producer] sending: s",
                "[producer] sending: t",
                "[producer] sending: r",
                '[producer] sending: "',
                "[producer] sending: :",
                '[producer] sending: "',
                "[producer] sending: f",
                "[producer] sending: o",
                "[producer] sending: o",
                '[producer] sending: "',
                "[str] received: foo",
                "[producer] sending: ,",
                '[producer] sending: "',
                "[producer] sending: m",
                "[producer] sending: y",
                "[producer] sending: _",
                "[producer] sending: i",
                "[producer] sending: n",
                "[producer] sending: t",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending: 4",
                "[producer] sending: 2",
                "[producer] sending: ,",
                "[int] received: 42",
                '[producer] sending: "',
                "[producer] sending: m",
                "[producer] sending: y",
                "[producer] sending: _",
                "[producer] sending: f",
                "[producer] sending: l",
                "[producer] sending: o",
                "[producer] sending: a",
                "[producer] sending: t",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending: 3",
                "[producer] sending: .",
                "[producer] sending: 1",
                "[producer] sending: 4",
                "[producer] sending: ,",
                "[float] received: 3.14",
                '[producer] sending: "',
                "[producer] sending: m",
                "[producer] sending: y",
                "[producer] sending: _",
                "[producer] sending: b",
                "[producer] sending: o",
                "[producer] sending: o",
                "[producer] sending: l",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending: t",
                "[producer] sending: r",
                "[producer] sending: u",
                "[producer] sending: e",
                "[producer] sending: ,",
                "[bool] received: True",
                '[producer] sending: "',
                "[producer] sending: m",
                "[producer] sending: y",
                "[producer] sending: _",
                "[producer] sending: e",
                "[producer] sending: n",
                "[producer] sending: u",
                "[producer] sending: m",
                '[producer] sending: "',
                "[producer] sending: :",
                '[producer] sending: "',
                "[producer] sending: v",
                "[producer] sending: a",
                "[producer] sending: l",
                "[producer] sending: u",
                "[producer] sending: e",
                "[producer] sending: 1",
                '[producer] sending: "',
                "[enum] received: SEnum.VALUE1",
                "[producer] sending: ,",
                '[producer] sending: "',
                "[producer] sending: m",
                "[producer] sending: y",
                "[producer] sending: _",
                "[producer] sending: n",
                "[producer] sending: o",
                "[producer] sending: n",
                "[producer] sending: e",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending: n",
                "[producer] sending: u",
                "[producer] sending: l",
                "[producer] sending: l",
                "[producer] sending: }",
                "[none] received: None",
            ],
        )
    ],
)
@pytest.mark.anyio
async def test_json_demux__primitives(stream: str, expected_operations: List[str]):
    class SPrimitives(JMux):
        class SEnum(Enum):
            VALUE1 = "value1"
            VALUE2 = "value2"

        my_str: AwaitableValue[str]
        my_int: AwaitableValue[int]
        my_float: AwaitableValue[float]
        my_bool: AwaitableValue[bool]
        my_enum: AwaitableValue[SEnum]
        my_none: AwaitableValue[NoneType]

    llm_stream = AsyncStreamGenerator(stream)
    s_primitives = SPrimitives()

    my_str: Optional[str] = None
    my_int: Optional[int] = None
    my_float: Optional[float] = None
    my_bool: Optional[bool] = None
    my_enum: Optional[SPrimitives.SEnum] = None
    my_none: Optional[NoneType] = None
    operation_list = []

    async def consume_str():
        nonlocal my_str
        my_str = await s_primitives.my_str
        op = f"[str] received: {my_str}"
        log_emit(op)
        operation_list.append(op)

    async def consume_int():
        nonlocal my_int
        my_int = await s_primitives.my_int
        op = f"[int] received: {my_int}"
        log_emit(op)
        operation_list.append(op)

    async def consume_float():
        nonlocal my_float
        my_float = await s_primitives.my_float
        op = f"[float] received: {my_float}"
        log_emit(op)
        operation_list.append(op)

    async def consume_bool():
        nonlocal my_bool
        my_bool = await s_primitives.my_bool
        op = f"[bool] received: {my_bool}"
        log_emit(op)
        operation_list.append(op)

    async def consume_enum():
        nonlocal my_enum
        my_enum = await s_primitives.my_enum
        op = f"[enum] received: {my_enum}"
        log_emit(op)
        operation_list.append(op)

    async def consume_none():
        nonlocal my_none
        my_none = await s_primitives.my_none
        op = f"[none] received: {my_none}"
        log_emit(op)
        operation_list.append(op)

    async def produce():
        async for ch in llm_stream:
            op = f"[producer] sending: {ch}"
            log_emit(op)
            operation_list.append(op)
            await s_primitives.feed_char(ch)
            # Yield control to allow other tasks to run
            # Necessary in the tests only, for API calls this is not needed
            await asyncio.sleep(0)

    await gather(
        produce(),
        consume_str(),
        consume_int(),
        consume_float(),
        consume_bool(),
        consume_enum(),
        consume_none(),
    )

    parsed_json = json.loads(stream)

    assert my_str == parsed_json["my_str"]
    assert my_int == parsed_json["my_int"]
    assert my_float == parsed_json["my_float"]
    assert my_bool == parsed_json["my_bool"]
    assert my_enum is not None and my_enum.value == parsed_json["my_enum"]
    assert my_none == parsed_json["my_none"]
    assert operation_list == expected_operations


class SPrimitivesPartial1(JMux):
    my_str: AwaitableValue[str]
    my_int: AwaitableValue[int | NoneType]
    my_float: AwaitableValue[float]
    my_bool: AwaitableValue[bool | NoneType]
    my_none: AwaitableValue[NoneType]


@pytest.mark.parametrize(
    "stream,MaybeExpectedError",
    [
        (
            '{"key_str":"foo","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"bar","key_nested":{"key_str":"nested_value"}}',
            None,
        ),
        (
            '{"key_str":"foo","key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"bar","key_nested":{"key_str":"nested_value"}}',
            None,
        ),
        (
            '{"key_str":"foo","key_float":3.14,"key_none":null,"key_stream":"bar","key_nested":{"key_str":"nested_value"}}',
            None,
        ),
        (
            '{"key_str":"foo","key_float":3.14,"key_stream":"bar","key_nested":{"key_str":"nested_value"}}',
            None,
        ),
        (
            '{"key_str":"foo","key_float":3.14,"key_stream":"bar","key_nested":null}',
            None,
        ),
        (
            '{"key_str":"foo","key_float":3.14,"key_stream":"bar"}',
            None,
        ),
        (
            '{"key_float":3.14}',
            NotAllObjectPropertiesSetError,
        ),
        (
            '{"key_str":"foo"}',
            NotAllObjectPropertiesSetError,
        ),
    ],
)
@pytest.mark.anyio
async def test_json_demux__primitives__partial_streams(
    stream: str,
    MaybeExpectedError: Type[Exception] | None,
):
    class SObject(JMux):
        class SNested(JMux):
            key_str: AwaitableValue[str]

        key_str: AwaitableValue[str]
        key_int: AwaitableValue[int | NoneType]
        key_float: AwaitableValue[float]
        key_bool: AwaitableValue[bool | NoneType]
        key_none: AwaitableValue[NoneType]
        key_stream: StreamableValues[str]
        key_nested: AwaitableValue[SNested | NoneType]

        arr_str: StreamableValues[str]
        arr_int: StreamableValues[int]
        arr_float: StreamableValues[float]
        arr_bool: StreamableValues[bool]
        arr_none: StreamableValues[NoneType]
        arr_nested: StreamableValues[SNested]

    llm_stream = AsyncStreamGenerator(stream)
    s_primitives = SObject()

    my_str: Optional[str] = None
    my_int: Optional[int] = None
    my_float: Optional[float] = None
    my_bool: Optional[bool] = None
    my_none: Optional[NoneType] = None
    operation_list = []

    async def consume_str():
        nonlocal my_str
        my_str = await s_primitives.key_str
        op = f"[str] received: {my_str}"
        log_emit(op)
        operation_list.append(op)

    async def consume_int():
        nonlocal my_int
        my_int = await s_primitives.key_int
        op = f"[int] received: {my_int}"
        log_emit(op)
        operation_list.append(op)

    async def consume_float():
        nonlocal my_float
        my_float = await s_primitives.key_float
        op = f"[float] received: {my_float}"
        log_emit(op)
        operation_list.append(op)

    async def consume_bool():
        nonlocal my_bool
        my_bool = await s_primitives.key_bool
        op = f"[bool] received: {my_bool}"
        log_emit(op)
        operation_list.append(op)

    async def consume_none():
        nonlocal my_none
        my_none = await s_primitives.key_none
        op = f"[none] received: {my_none}"
        log_emit(op)
        operation_list.append(op)

    async def produce():
        async for ch in llm_stream:
            op = f"[producer] sending: {ch}"
            log_emit(op)
            operation_list.append(op)
            await s_primitives.feed_char(ch)
            # Yield control to allow other tasks to run
            # Necessary in the tests only, for API calls this is not needed
            await asyncio.sleep(0)

    if MaybeExpectedError:
        with pytest.raises(MaybeExpectedError):
            await wait_for(
                fut=gather(
                    produce(),
                    consume_str(),
                    consume_int(),
                    consume_float(),
                    consume_bool(),
                    consume_none(),
                ),
                timeout=5,
            )
    else:
        await wait_for(
            fut=gather(
                produce(),
                consume_str(),
                consume_int(),
                consume_float(),
                consume_bool(),
                consume_none(),
            ),
            timeout=5,
        )
        parsed_json = json.loads(stream)

        assert my_str == parsed_json.get("key_str", None)
        assert my_int == parsed_json.get("key_int", None)
        assert my_float == parsed_json.get("key_float", None)
        assert my_bool == parsed_json.get("key_bool", None)
        assert my_none == parsed_json.get("key_none", None)


@pytest.mark.parametrize(
    "stream,expected_operations",
    [
        (
            '{"nested":{"child":"child_value"}}',
            [
                "[producer] sending: {",
                '[producer] sending: "',
                "[producer] sending: n",
                "[producer] sending: e",
                "[producer] sending: s",
                "[producer] sending: t",
                "[producer] sending: e",
                "[producer] sending: d",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending: {",
                "[nested] received: <SNestedChild>",
                '[producer] sending: "',
                "[producer] sending: c",
                "[producer] sending: h",
                "[producer] sending: i",
                "[producer] sending: l",
                "[producer] sending: d",
                '[producer] sending: "',
                "[producer] sending: :",
                '[producer] sending: "',
                "[producer] sending: c",
                "[producer] sending: h",
                "[producer] sending: i",
                "[producer] sending: l",
                "[producer] sending: d",
                "[producer] sending: _",
                "[producer] sending: v",
                "[producer] sending: a",
                "[producer] sending: l",
                "[producer] sending: u",
                "[producer] sending: e",
                '[producer] sending: "',
                "[child] received: child_value",
                "[producer] sending: }",
                "[producer] sending: }",
            ],
        )
    ],
)
@pytest.mark.anyio
async def test_json_demux__nested(stream: str, expected_operations: List[str]):
    class SParent(JMux):
        class SNested(JMux):
            child: AwaitableValue[str]

        nested: AwaitableValue[SNested]

    llm_stream = AsyncStreamGenerator(stream)
    s_parent = SParent()

    nested: Optional[SParent.SNested] = None
    child: Optional[str] = None
    operation_list = []

    async def consume_nested():
        nonlocal nested, child
        nested = await s_parent.nested
        op = "[nested] received: <SNestedChild>"
        log_emit(op)
        operation_list.append(op)

        child = await nested.child
        op = f"[child] received: {child}"
        log_emit(op)
        operation_list.append(op)

    async def produce():
        async for ch in llm_stream:
            op = f"[producer] sending: {ch}"
            log_emit(op)
            operation_list.append(op)
            await s_parent.feed_char(ch)
            # Yield control to allow other tasks to run
            # Necessary in the tests only, for API calls this is not needed
            await asyncio.sleep(0)

    await gather(
        produce(),
        consume_nested(),
    )

    parsed_json = json.loads(stream)
    assert nested is not None
    assert isinstance(nested, SParent.SNested)
    assert child == parsed_json["nested"]["child"]
    assert operation_list == expected_operations


@pytest.mark.parametrize(
    "stream,expected_operations",
    [
        (
            '{"arr":[{"key":"value1"},{"key":"value2"}]}',
            [
                "[producer] sending: {",
                '[producer] sending: "',
                "[producer] sending: a",
                "[producer] sending: r",
                "[producer] sending: r",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending: [",
                "[producer] sending: {",
                "[nested] received: <SArrayElement>",
                '[producer] sending: "',
                "[producer] sending: k",
                "[producer] sending: e",
                "[producer] sending: y",
                '[producer] sending: "',
                "[producer] sending: :",
                '[producer] sending: "',
                "[producer] sending: v",
                "[producer] sending: a",
                "[producer] sending: l",
                "[producer] sending: u",
                "[producer] sending: e",
                "[producer] sending: 1",
                '[producer] sending: "',
                "[child] received: value1",
                "[producer] sending: }",
                "[producer] sending: ,",
                "[producer] sending: {",
                "[nested] received: <SArrayElement>",
                '[producer] sending: "',
                "[producer] sending: k",
                "[producer] sending: e",
                "[producer] sending: y",
                '[producer] sending: "',
                "[producer] sending: :",
                '[producer] sending: "',
                "[producer] sending: v",
                "[producer] sending: a",
                "[producer] sending: l",
                "[producer] sending: u",
                "[producer] sending: e",
                "[producer] sending: 2",
                '[producer] sending: "',
                "[child] received: value2",
                "[producer] sending: }",
                "[producer] sending: ]",
                "[producer] sending: }",
            ],
        )
    ],
)
@pytest.mark.anyio
async def test_json_demux__object_with_array_of_objects(
    stream: str, expected_operations: List[str]
):
    class SParent(JMux):
        class SArrayElement(JMux):
            key: AwaitableValue[str]

        arr: StreamableValues[SArrayElement]

    llm_stream = AsyncStreamGenerator(stream)
    s_parent = SParent()

    arr: List[SParent.SArrayElement] = []
    child: List[str] = []
    operation_list = []

    async def consume_nested():
        nonlocal arr, child
        async for element in s_parent.arr:
            arr.append(element)
            op = "[nested] received: <SArrayElement>"
            log_emit(op)
            operation_list.append(op)

            key_value = await element.key
            await asyncio.sleep(0)
            child.append(key_value)
            op = f"[child] received: {key_value}"
            log_emit(op)
            operation_list.append(op)

    async def produce():
        async for ch in llm_stream:
            op = f"[producer] sending: {ch}"
            log_emit(op)
            operation_list.append(op)
            await s_parent.feed_char(ch)
            # Yield control to allow other tasks to run
            # Necessary in the tests only, for API calls this is not needed
            await asyncio.sleep(0)

    await gather(
        produce(),
        consume_nested(),
    )

    parsed_json = json.loads(stream)
    assert arr is not None
    assert len(arr) == 2
    assert isinstance(arr[0], SParent.SArrayElement)
    assert child[0] == parsed_json["arr"][0]["key"]
    assert operation_list == expected_operations


@pytest.mark.parametrize(
    "stream,expected_operations",
    [
        (
            '{"arr_int":[1,2],"arr_float":[1.1,2.2],"arr_bool":[true,false],"arr_str":["ab","cd"]}',
            [
                "[producer] sending: {",
                '[producer] sending: "',
                "[producer] sending: a",
                "[producer] sending: r",
                "[producer] sending: r",
                "[producer] sending: _",
                "[producer] sending: i",
                "[producer] sending: n",
                "[producer] sending: t",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending: [",
                "[producer] sending: 1",
                "[producer] sending: ,",
                "[arr_int] received: 1",
                "[producer] sending: 2",
                "[producer] sending: ]",
                "[arr_int] received: 2",
                "[producer] sending: ,",
                '[producer] sending: "',
                "[producer] sending: a",
                "[producer] sending: r",
                "[producer] sending: r",
                "[producer] sending: _",
                "[producer] sending: f",
                "[producer] sending: l",
                "[producer] sending: o",
                "[producer] sending: a",
                "[producer] sending: t",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending: [",
                "[producer] sending: 1",
                "[producer] sending: .",
                "[producer] sending: 1",
                "[producer] sending: ,",
                "[arr_float] received: 1.1",
                "[producer] sending: 2",
                "[producer] sending: .",
                "[producer] sending: 2",
                "[producer] sending: ]",
                "[arr_float] received: 2.2",
                "[producer] sending: ,",
                '[producer] sending: "',
                "[producer] sending: a",
                "[producer] sending: r",
                "[producer] sending: r",
                "[producer] sending: _",
                "[producer] sending: b",
                "[producer] sending: o",
                "[producer] sending: o",
                "[producer] sending: l",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending: [",
                "[producer] sending: t",
                "[producer] sending: r",
                "[producer] sending: u",
                "[producer] sending: e",
                "[producer] sending: ,",
                "[arr_bool] received: True",
                "[producer] sending: f",
                "[producer] sending: a",
                "[producer] sending: l",
                "[producer] sending: s",
                "[producer] sending: e",
                "[producer] sending: ]",
                "[arr_bool] received: False",
                "[producer] sending: ,",
                '[producer] sending: "',
                "[producer] sending: a",
                "[producer] sending: r",
                "[producer] sending: r",
                "[producer] sending: _",
                "[producer] sending: s",
                "[producer] sending: t",
                "[producer] sending: r",
                '[producer] sending: "',
                "[producer] sending: :",
                "[producer] sending: [",
                '[producer] sending: "',
                "[producer] sending: a",
                "[producer] sending: b",
                '[producer] sending: "',
                "[arr_str] received: ab",
                "[producer] sending: ,",
                '[producer] sending: "',
                "[producer] sending: c",
                "[producer] sending: d",
                '[producer] sending: "',
                "[arr_str] received: cd",
                "[producer] sending: ]",
                "[producer] sending: }",
            ],
        )
    ],
)
@pytest.mark.anyio
async def test_json_demux__object_with_array_of_primitives(
    stream: str, expected_operations: List[str]
):
    class SParent(JMux):
        arr_int: StreamableValues[int]
        arr_float: StreamableValues[float]
        arr_bool: StreamableValues[bool]
        arr_str: StreamableValues[str]

    llm_stream = AsyncStreamGenerator(stream)
    s_parent = SParent()

    arr_int: List[int] = []
    arr_float: List[float] = []
    arr_bool: List[bool] = []
    arr_str: List[str] = []
    operation_list = []

    async def consume_int_arr():
        nonlocal arr_int
        async for element in s_parent.arr_int:
            arr_int.append(element)
            op = f"[arr_int] received: {element}"
            print(op)
            operation_list.append(op)

    async def consume_float_arr():
        nonlocal arr_float
        async for element in s_parent.arr_float:
            arr_float.append(element)
            op = f"[arr_float] received: {element}"
            print(op)
            operation_list.append(op)

    async def consume_bool_arr():
        nonlocal arr_bool
        async for element in s_parent.arr_bool:
            arr_bool.append(element)
            op = f"[arr_bool] received: {element}"
            print(op)
            operation_list.append(op)

    async def consume_str_arr():
        nonlocal arr_str
        async for element in s_parent.arr_str:
            arr_str.append(element)
            op = f"[arr_str] received: {element}"
            print(op)
            operation_list.append(op)

    async def produce():
        async for ch in llm_stream:
            op = f"[producer] sending: {ch}"
            print(op)
            operation_list.append(op)
            await s_parent.feed_char(ch)
            # Yield control to allow other tasks to run
            # Necessary in the tests only, for API calls this is not needed
            await asyncio.sleep(0)

    await gather(
        produce(),
        consume_int_arr(),
        consume_float_arr(),
        consume_bool_arr(),
        consume_str_arr(),
    )

    parsed_json = json.loads(stream)
    assert len(arr_int) == 2
    assert arr_int == parsed_json["arr_int"]
    assert len(arr_float) == 2
    assert arr_float == parsed_json["arr_float"]
    assert len(arr_bool) == 2
    assert arr_bool == parsed_json["arr_bool"]
    assert len(arr_str) == 2
    assert arr_str == parsed_json["arr_str"]
    assert operation_list == expected_operations
