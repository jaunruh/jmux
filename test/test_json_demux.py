import asyncio
from asyncio import gather
from typing import List

import pytest
from jmux.json_demux import SCityName, StreamingJSONSplitter


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
async def test_json_demux(stream: str, expected_operations: List[str]):
    llm_stream = AsyncStreamGenerator(stream)
    sCity = SCityName()
    splitter = StreamingJSONSplitter(sCity)

    city_name = ""
    country = ""
    operation_list = []

    async def consume_city():
        nonlocal city_name
        async for ch in sCity.city_name:
            op = f"[city] received: {ch}"
            operation_list.append(op)
            city_name += ch

    async def consume_country():
        nonlocal country
        async for ch in sCity.country:
            op = f"[country] received: {ch}"
            operation_list.append(op)
            country += ch

    async def produce():
        async for ch in llm_stream:
            op = f"[producer] sending: {ch}"
            operation_list.append(op)
            await splitter.feed_char(ch)
            # Yield control to allow other tasks to run
            # Necessary in the tests only, for API calls this is not needed
            await asyncio.sleep(0)

    await gather(
        produce(),
        consume_city(),
        consume_country(),
    )

    assert city_name == "Paris"
    assert country == "France"

    assert operation_list == expected_operations
