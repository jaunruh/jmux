from typing import Protocol


class IDecoder(Protocol):
    def push(self, ch: str) -> str | None: ...

    def is_terminating_quote(self, ch: str) -> bool: ...

    def reset(self) -> None: ...

    @property
    def buffer(self) -> str: ...


class StringEscapeDecoder:
    r"""
    Decoder for strings with escape sequences, such as JSON strings.
    Handles escape sequences like \", \\, \/, \b, \f, \n, \r, \t, and unicode escapes.
    """

    escape_map = {
        '"': '"',
        "\\": "\\",
        "/": "/",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }

    def __init__(self):
        self._buffer = ""
        self._string_escape = False
        self._is_parsing_unicode = False
        self._unicode_buffer = ""

    def push(self, ch: str) -> str | None:
        if self._is_parsing_unicode:
            self._unicode_buffer += ch
            if len(self._unicode_buffer) == 4:
                code_point = int(self._unicode_buffer, 16)
                decoded_char = chr(code_point)
                self._buffer += decoded_char
                self._is_parsing_unicode = False
                self._unicode_buffer = ""
                return decoded_char
            return None

        if self._string_escape:
            self._string_escape = False
            if ch == "u":
                self._is_parsing_unicode = True
                self._unicode_buffer = ""
                return None
            escaped_char = self.escape_map.get(ch, ch)
            self._buffer += escaped_char
            return escaped_char

        if ch == "\\":
            self._string_escape = True
            return None
        else:
            self._buffer += ch
            return ch

    def is_terminating_quote(self, ch: str) -> bool:
        if self._string_escape or self._is_parsing_unicode:
            return False
        if ch == '"':
            return True
        return False

    def reset(self) -> None:
        self._buffer = ""
        self._string_escape = False
        self._is_parsing_unicode = False
        self._unicode_buffer = ""

    @property
    def buffer(self) -> str:
        return self._buffer
