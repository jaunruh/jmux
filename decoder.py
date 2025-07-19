from typing import Protocol

from jmux.error import StreamParseError


class IDecoder(Protocol):
    def push(self, ch: str) -> str | None: ...

    def is_terminating_quote(self, ch: str) -> bool: ...

    def reset(self) -> None: ...

    @property
    def buffer(self) -> str: ...


class StringDecoder:
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
        self.is_parsing_unicode: bool = False
        self.unicode_buffer: str = ""
        self.high_surrogate = None
        self.expect_low_surrogate = False

    def push(self, ch: str) -> str | None:
        if self.is_parsing_unicode:
            self.unicode_buffer += ch
            if len(self.unicode_buffer) == 4:
                code_unit = int(self.unicode_buffer, 16)
                self.is_parsing_unicode = False
                self.unicode_buffer = ""

                if self.high_surrogate is not None:
                    # Expecting a low surrogate
                    if 0xDC00 <= code_unit <= 0xDFFF:
                        # Combine surrogate pair into single character
                        combined = (
                            0x10000
                            + ((self.high_surrogate - 0xD800) << 10)
                            + (code_unit - 0xDC00)
                        )
                        self._buffer += chr(combined)
                    else:
                        # Invalid low surrogate — output both separately
                        self._buffer += chr(self.high_surrogate)
                        self._buffer += chr(code_unit)
                        raise StreamParseError(
                            f"Invalid low surrogate: {code_unit:#04x} after high surrogate: {self.high_surrogate:#04x}"
                        )
                    self.high_surrogate = None
                elif 0xD800 <= code_unit <= 0xDBFF:
                    # High surrogate, wait for the next \uXXXX
                    self.high_surrogate = code_unit
                else:
                    # Regular BMP character
                    self._buffer += chr(code_unit)
            return

        if self._string_escape:
            self._string_escape = False
            if ch == "u":
                self.is_parsing_unicode = True
                self.unicode_buffer = ""
                return
            escaped_char = self.escape_map.get(ch, ch)
            self._buffer += escaped_char
            return escaped_char

        if ch == "\\":
            self._string_escape = True
        else:
            self._buffer += ch
            return ch

    def is_terminating_quote(self, ch: str) -> bool:
        if self._string_escape:
            return False
        if ch == '"':
            return True
        return False

    def reset(self) -> None:
        self._buffer = ""
        self._string_escape = False

    @property
    def buffer(self) -> str:
        return self._buffer
