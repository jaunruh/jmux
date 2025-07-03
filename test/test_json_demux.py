import asyncio
import json
from asyncio import gather
from typing import List, Optional

import pytest
from jmux.json_demux import AwaitableValue, JMux, StreamableValues


class AsyncStreamGenerator:
    stream: str

    def __init__(self, stream):
        self.stream = stream

    async def __anext__(self):
        raise Exception("This method is not implemented")

    async def __aiter__(self):
        for char in self.stream:
            yield char


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
            operation_list.append(op)
            city_name += ch

    async def consume_country():
        nonlocal country
        async for ch in s_city.country:
            op = f"[country] received: {ch}"
            operation_list.append(op)
            country += ch

    async def produce():
        async for ch in llm_stream:
            op = f"[producer] sending: {ch}"
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

    s_emoji_class = SEmojis

    print(f"Class type: {type(s_emoji_class)}")

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
            '{"my_int":42,"my_float":3.14,"my_bool":true,"my_none":null}',
            [
                "[producer] sending: {",
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
async def test_json_demux__primitves(stream: str, expected_operations: List[str]):
    class SPrimitives(JMux):
        my_int: AwaitableValue[int]
        my_float: AwaitableValue[float]
        my_bool: AwaitableValue[bool]
        my_none: AwaitableValue[None]

    llm_stream = AsyncStreamGenerator(stream)
    s_primitives = SPrimitives()

    my_int: Optional[int] = None
    my_float: Optional[float] = None
    my_bool: Optional[bool] = None
    my_none: Optional[None] = None
    operation_list = []

    async def consume_int():
        nonlocal my_int
        my_int = await s_primitives.my_int
        op = f"[int] received: {my_int}"
        operation_list.append(op)

    async def consume_float():
        nonlocal my_float
        my_float = await s_primitives.my_float
        op = f"[float] received: {my_float}"
        operation_list.append(op)

    async def consume_bool():
        nonlocal my_bool
        my_bool = await s_primitives.my_bool
        op = f"[bool] received: {my_bool}"
        operation_list.append(op)

    async def consume_none():
        nonlocal my_none
        my_none = await s_primitives.my_none
        op = f"[none] received: {my_none}"
        operation_list.append(op)

    async def produce():
        async for ch in llm_stream:
            op = f"[producer] sending: {ch}"
            operation_list.append(op)
            await s_primitives.feed_char(ch)
            # Yield control to allow other tasks to run
            # Necessary in the tests only, for API calls this is not needed
            await asyncio.sleep(0)

    await gather(
        produce(),
        consume_int(),
        consume_float(),
        consume_bool(),
        consume_none(),
    )

    parsed_json = json.loads(stream)

    assert my_int == parsed_json["my_int"]
    assert my_float == parsed_json["my_float"]
    assert my_bool == parsed_json["my_bool"]
    assert my_none == parsed_json["my_none"]
    assert operation_list == expected_operations
