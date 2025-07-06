from typing import List

import pytest
from jmux.decoder import StringDecoder


def codepoint_to_surrogates(codepoint: int):
    """
    Use this function to convert utf-16 codepoints to surrogate pairs.
    """
    if codepoint < 0x10000:
        return [codepoint]
    codepoint -= 0x10000
    high = 0xD800 + (codepoint >> 10)
    low = 0xDC00 + (codepoint & 0x3FF)
    return [hex(high), hex(low)]


# fmt: off
@pytest.mark.parametrize(
    "stream,expected_string",
    [
        ("foo bar", "foo bar"),
        ("foo\"bar", 'foo"bar'),
        ("foo bar\"", 'foo bar"'),
        ("foo\\\\bar", "foo\\bar"),
        ("foo\\bbar", "foo\bbar"),
        ("foo\\tbar", "foo\tbar"),
        ("foo\\rbar", "foo\rbar"),
        ("foo\\fbar", "foo\fbar"),
        ("foo\\/bar", "foo/bar"),
        ("foo\\/bar", "foo/bar"),
        ("foo\\u0905bar", "fooअbar"),
        ("foo\\u20ACbar", "foo€bar"),
        ("foo\\u2713bar", "foo✓bar"),
        ("foo\\ud83d\\ude00bar", "foo😀bar"),
        ("foo\\ud83d\\ude03bar", "foo😃bar"),
    ],
)
# fmt: on
@pytest.mark.anyio
async def test_string_decoder__parameterized(stream: str, expected_string: List[str]):
    decoder = StringDecoder()

    for ch in stream:
        decoder.push(ch)

    assert decoder.buffer == expected_string
