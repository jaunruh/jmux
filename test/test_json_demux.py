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
    "stream",
    [
        '{"city_name":"Paris","country":"France"}',
        '{"city_name": "Paris", "country":"France"}',
        '{\n\t"city_name": "Paris",\n\t"country": "France"\n}',
    ],
)
@pytest.mark.anyio
async def test_json_demux(stream):
    print("Testing JSON demux with stream:", stream)

    llm_stream = AsyncStreamGenerator(stream)
    sCity = SCityName()
    stream_wrapper = StreamingJSONSplitter(sCity)

    async for char in llm_stream:
        await stream_wrapper.feed_char(char)

    city_name = ""
    country = ""
    async for char in sCity.city_name:
        city_name += char
    async for char in sCity.country:
        country += char

    assert city_name == "Paris", "Stream result does not match the input stream"
    assert country == "France", "Stream result does not match the input stream"
