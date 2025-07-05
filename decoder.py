class StringDecoder:
    escape_map = {
        '"': '"',
        "\\": "\\\\",
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

    def push(self, ch: str) -> None:
        if self._string_escape:
            self._buffer += self.escape_map.get(ch, ch)
            self._string_escape = False
        elif ch == "\\":
            self._string_escape = True
        else:
            self._buffer += ch

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
