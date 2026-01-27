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


@pytest.mark.parametrize(
    "stream,expected_string",
    [
        ("\\n", "\n"),
        ("hello\\nworld", "hello\nworld"),
        ("line1\\nline2\\nline3", "line1\nline2\nline3"),
        ("\\n\\n\\n", "\n\n\n"),
    ],
)
def test_string_decoder__newline_escape(stream: str, expected_string: str):
    decoder = StringEscapeDecoder()
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == expected_string


@pytest.mark.parametrize(
    "stream,expected_string",
    [
        ("\\t", "\t"),
        ("col1\\tcol2\\tcol3", "col1\tcol2\tcol3"),
        ("\\t\\t\\t", "\t\t\t"),
    ],
)
def test_string_decoder__tab_escape(stream: str, expected_string: str):
    decoder = StringEscapeDecoder()
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == expected_string


@pytest.mark.parametrize(
    "stream,expected_string",
    [
        ("\\r", "\r"),
        ("line1\\rline2", "line1\rline2"),
        ("\\r\\n", "\r\n"),
    ],
)
def test_string_decoder__carriage_return_escape(stream: str, expected_string: str):
    decoder = StringEscapeDecoder()
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == expected_string


@pytest.mark.parametrize(
    "stream,expected_string",
    [
        ("\\b", "\b"),
        ("hello\\bworld", "hello\bworld"),
    ],
)
def test_string_decoder__backspace_escape(stream: str, expected_string: str):
    decoder = StringEscapeDecoder()
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == expected_string


@pytest.mark.parametrize(
    "stream,expected_string",
    [
        ("\\f", "\f"),
        ("page1\\fpage2", "page1\fpage2"),
    ],
)
def test_string_decoder__formfeed_escape(stream: str, expected_string: str):
    decoder = StringEscapeDecoder()
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == expected_string


@pytest.mark.parametrize(
    "stream,expected_string",
    [
        ("\\/", "/"),
        ("http:\\/\\/example.com", "http://example.com"),
    ],
)
def test_string_decoder__forward_slash_escape(stream: str, expected_string: str):
    decoder = StringEscapeDecoder()
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == expected_string


@pytest.mark.parametrize(
    "stream,expected_string",
    [
        ("\\\\", "\\"),
        ("C:\\\\Users\\\\Name", "C:\\Users\\Name"),
        ("\\\\\\\\", "\\\\"),
    ],
)
def test_string_decoder__backslash_escape(stream: str, expected_string: str):
    decoder = StringEscapeDecoder()
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == expected_string


@pytest.mark.parametrize(
    "stream,expected_string",
    [
        ("\\\"", '"'),
        ("say \\\"hello\\\"", 'say "hello"'),
        ("\\\"\\\"\\\"", '"""'),
    ],
)
def test_string_decoder__quote_escape(stream: str, expected_string: str):
    decoder = StringEscapeDecoder()
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == expected_string


def test_string_decoder__is_terminating_quote_unescaped():
    decoder = StringEscapeDecoder()
    assert decoder.is_terminating_quote('"') is True


def test_string_decoder__is_terminating_quote_escaped():
    decoder = StringEscapeDecoder()
    decoder.push("\\")
    assert decoder.is_terminating_quote('"') is False


def test_string_decoder__is_terminating_quote_other_chars():
    decoder = StringEscapeDecoder()
    assert decoder.is_terminating_quote("a") is False
    assert decoder.is_terminating_quote("'") is False
    assert decoder.is_terminating_quote(" ") is False
    assert decoder.is_terminating_quote("\\") is False


def test_string_decoder__is_terminating_quote_after_escaped_backslash():
    decoder = StringEscapeDecoder()
    decoder.push("\\")
    decoder.push("\\")
    assert decoder.is_terminating_quote('"') is True


def test_string_decoder__reset_clears_buffer():
    decoder = StringEscapeDecoder()
    decoder.push("h")
    decoder.push("e")
    decoder.push("l")
    decoder.push("l")
    decoder.push("o")
    assert decoder.buffer == "hello"
    decoder.reset()
    assert decoder.buffer == ""


def test_string_decoder__reset_clears_escape_state():
    decoder = StringEscapeDecoder()
    decoder.push("\\")
    decoder.reset()
    assert decoder.is_terminating_quote('"') is True


def test_string_decoder__buffer_property_returns_accumulated():
    decoder = StringEscapeDecoder()
    assert decoder.buffer == ""
    decoder.push("a")
    assert decoder.buffer == "a"
    decoder.push("b")
    assert decoder.buffer == "ab"
    decoder.push("c")
    assert decoder.buffer == "abc"


def test_string_decoder__push_returns_character():
    decoder = StringEscapeDecoder()
    assert decoder.push("a") == "a"
    assert decoder.push("b") == "b"


def test_string_decoder__push_returns_none_for_backslash():
    decoder = StringEscapeDecoder()
    assert decoder.push("\\") is None


def test_string_decoder__push_returns_escaped_char_after_backslash():
    decoder = StringEscapeDecoder()
    decoder.push("\\")
    assert decoder.push("n") == "\n"


def test_string_decoder__push_returns_none_for_unicode_start():
    decoder = StringEscapeDecoder()
    decoder.push("\\")
    assert decoder.push("u") is None


@pytest.mark.parametrize(
    "invalid_escape,expected_char",
    [
        ("\\x", "x"),
        ("\\a", "a"),
        ("\\z", "z"),
        ("\\1", "1"),
        ("\\@", "@"),
    ],
)
def test_string_decoder__invalid_escape_falls_back_to_literal(invalid_escape: str, expected_char: str):
    decoder = StringEscapeDecoder()
    for ch in invalid_escape:
        decoder.push(ch)
    assert decoder.buffer == expected_char


def test_string_decoder__multiple_escape_sequences():
    decoder = StringEscapeDecoder()
    stream = "line1\\nline2\\ttab\\r\\nend"
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == "line1\nline2\ttab\r\nend"


def test_string_decoder__escape_at_end_of_input():
    decoder = StringEscapeDecoder()
    decoder.push("a")
    decoder.push("b")
    decoder.push("\\")
    assert decoder.buffer == "ab"
    assert decoder._string_escape is True


def test_string_decoder__empty_string():
    decoder = StringEscapeDecoder()
    assert decoder.buffer == ""


def test_string_decoder__single_character():
    decoder = StringEscapeDecoder()
    decoder.push("x")
    assert decoder.buffer == "x"


def test_string_decoder__whitespace_preserved():
    decoder = StringEscapeDecoder()
    stream = "  hello  world  "
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == "  hello  world  "


def test_string_decoder__unicode_characters_pass_through():
    decoder = StringEscapeDecoder()
    stream = "こんにちは"
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == "こんにちは"


def test_string_decoder__emoji_pass_through():
    decoder = StringEscapeDecoder()
    stream = "🎉🚀💡"
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == "🎉🚀💡"


def test_string_decoder__mixed_content():
    decoder = StringEscapeDecoder()
    stream = "Hello\\nWorld 🌍\\t日本語"
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == "Hello\nWorld 🌍\t日本語"


def test_string_decoder__very_long_string():
    decoder = StringEscapeDecoder()
    stream = "a" * 10000
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == "a" * 10000


def test_string_decoder__all_escape_sequences_together():
    decoder = StringEscapeDecoder()
    stream = "\\\"\\\\\\b\\f\\n\\r\\t\\/"
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == '"\\\b\f\n\r\t/'


def test_string_decoder__reset_multiple_times():
    decoder = StringEscapeDecoder()
    decoder.push("a")
    decoder.reset()
    decoder.push("b")
    decoder.reset()
    decoder.push("c")
    assert decoder.buffer == "c"


def test_string_decoder__push_after_reset():
    decoder = StringEscapeDecoder()
    decoder.push("f")
    decoder.push("i")
    decoder.push("r")
    decoder.push("s")
    decoder.push("t")
    decoder.reset()
    decoder.push("s")
    decoder.push("e")
    decoder.push("c")
    decoder.push("o")
    decoder.push("n")
    decoder.push("d")
    assert decoder.buffer == "second"


def test_string_decoder__consecutive_backslashes_odd():
    decoder = StringEscapeDecoder()
    stream = "\\\\\\\\"
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == "\\\\"


def test_string_decoder__consecutive_backslashes_even():
    decoder = StringEscapeDecoder()
    stream = "\\\\\\\\\\\\"
    for ch in stream:
        decoder.push(ch)
    assert decoder.buffer == "\\\\\\"


def test_string_decoder__escape_map_access():
    decoder = StringEscapeDecoder()
    assert decoder.escape_map['"'] == '"'
    assert decoder.escape_map["\\"] == "\\"
    assert decoder.escape_map["/"] == "/"
    assert decoder.escape_map["b"] == "\b"
    assert decoder.escape_map["f"] == "\f"
    assert decoder.escape_map["n"] == "\n"
    assert decoder.escape_map["r"] == "\r"
    assert decoder.escape_map["t"] == "\t"
