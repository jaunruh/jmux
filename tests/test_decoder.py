from typing import List

import pytest

from jmux.decoder import StringEscapeDecoder


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
    ],
)
# fmt: on
@pytest.mark.anyio
async def test_string_decoder__parameterized(stream: str, expected_string: List[str]):
    decoder = StringEscapeDecoder()

    for ch in stream:
        decoder.push(ch)

    assert decoder.buffer == expected_string
