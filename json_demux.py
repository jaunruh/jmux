from asyncio import Queue
from typing import AsyncGenerator, List, Optional


class StreamSink[T]:
    def __init__(self):
        self._queue = Queue()
        self._closed = False

    async def put(self, item):
        await self._queue.put(item)

    async def close(self):
        self._closed = True
        await self._queue.put(None)

    def __aiter__(self):
        return self._stream()

    async def _stream(self) -> AsyncGenerator[T, None]:
        while True:
            item = await self._queue.get()
            if item is None and self._closed:
                break
            yield item


class SCityName:
    city_name: StreamSink
    country: StreamSink

    def __init__(self):
        self.city_name = StreamSink()
        self.country = StreamSink()


class StreamingJSONSplitter:
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

    def __init__(self, model: SCityName):
        self.model: SCityName = model
        self.state_stack: List[str] = []
        self.current_key: Optional[str] = None
        self.current_sink: Optional[StreamSink] = None
        self.string_escape = False

    async def feed_char(self, ch):
        state = self.state_stack[-1] if self.state_stack else None

        if state == "expecting_key":
            if ch == '"':
                self.state_stack.append("parsing_key")
                self.buffer = ""
        elif state == "parsing_key":
            if self.string_escape:
                self.buffer += self._unescape(ch)
                self.string_escape = False
            elif ch == "\\":
                self.string_escape = True
            elif ch == '"':
                self.current_key = self.buffer
                self.buffer = ""
                self.state_stack.pop()
                self.state_stack.append("expecting_colon")
            else:
                self.buffer += ch

        elif state == "expecting_colon":
            if ch == ":":
                self.state_stack.pop()
                self.state_stack.append("expecting_value")

        elif state == "expecting_value":
            if ch == '"':
                self.state_stack.pop()
                self.state_stack.append("streaming_string")
                if not self.current_key:
                    raise ValueError("Current key is not set before streaming string.")
                self.current_sink = getattr(self.model, self.current_key)
                self.string_escape = False

        elif state == "streaming_string":
            if self.string_escape:
                await self._emit(self._unescape(ch))
                self.string_escape = False
            elif ch == "\\":
                self.string_escape = True
            elif ch == '"':
                self.state_stack.pop()
                await self._close_sink()
            else:
                await self._emit(ch)

        elif ch == "{":
            self.state_stack.append("expecting_key")

    async def _emit(self, ch):
        if self.current_sink:
            await self.current_sink.put(ch)

    async def _close_sink(self):
        if self.current_sink:
            await self.current_sink.close()
        self.current_sink = None

    def _unescape(self, ch: str) -> str:
        return self.escape_map.get(ch, ch)
