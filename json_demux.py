from abc import ABC
from asyncio import Event, Queue
from typing import (
    AsyncGenerator,
    List,
    Literal,
    Optional,
    Protocol,
    Sequence,
    Type,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)


class UnderlyingGenericMixin[T]:
    def underlying_generic(self) -> Type[T]:
        # `__orig_class__` is only set after the `__init__` method is called
        if not hasattr(self, "__orig_class__"):
            raise TypeError(
                "AwaitableValue must be initialized with a defined generic type."
            )

        origin = getattr(self, "__orig_class__")
        if len(origin.__args__) != 1:
            raise TypeError(
                f"AwaitableValue must be initialized with a single generic type, got {origin.__args__}."
            )
        generic: Type[T] = origin.__args__[0]
        return generic


class StreamableValues[T: Sequence](UnderlyingGenericMixin[T]):
    def __init__(self):
        self._queue = Queue[T | None]()
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
            if item is None:
                raise ValueError("Received None item, but the sink is not closed.")
            yield item


class AwaitableValue[T: int | float | str | bool | None | JMux](
    UnderlyingGenericMixin[T]
):
    def __init__(self):
        self._was_set = False
        self._event = Event()
        self._value: T | None = None

    async def put(self, value: T):
        self._value = value
        self._event.set()

    async def close(self):
        self._was_set = True
        pass

    def __await__(self):
        return self._wait().__await__()

    async def _wait(self) -> T:
        await self._event.wait()
        if self._value is None and not self._was_set:
            raise ValueError("No value has been put into the sink.")
        return cast(T, self._value)


@runtime_checkable
class IAsyncSink(Protocol):
    def underlying_generic(self) -> Type:
        """Return the underlying generic type of the sink."""
        ...

    async def put(self, item):
        """Put an item into the sink."""
        ...

    async def close(self):
        """Close the sink."""
        ...


type State = Literal[
    "expecting_key",
    "parsing_key",
    "expecting_colon",
    "expecting_value",
    "expecting_primitive",  # number, true, false, null
    "streaming_string",
    "parsing_object",
]


class JMux(ABC):
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
        self._instantiate_attributes()
        self.state_stack: List[State] = []
        self.buffer: str = ""
        self.child_object: Optional["JMux"] = None
        self.current_key: Optional[str] = None
        self.current_sink: Optional[IAsyncSink] = None
        self.string_escape = False
        self.curly_brace_depth = 0

    def _instantiate_attributes(self) -> None:
        type_hints = get_type_hints(self.__class__)
        for attr_name, type_alias in type_hints.items():
            TargetType = get_origin(type_alias)
            type_alias_args = get_args(type_alias)
            if len(type_alias_args) != 1:
                raise TypeError(f"Generic type {type_alias} must be fully specified")
            TargetGenericType = type_alias_args[0]
            target_instance = TargetType[TargetGenericType]()
            if not issubclass(TargetType, IAsyncSink):
                raise TypeError(
                    f"Attribute '{attr_name}' must conform to protocol IAsyncSink, got {TargetType}."
                )
            setattr(self, attr_name, target_instance)

    @property
    def state(self) -> Optional[State]:
        return self.state_stack[-1] if self.state_stack else None

    async def feed_char(self, ch) -> None:
        if self.state == "expecting_key":
            if ch == '"':
                self.state_stack.append("parsing_key")
                self.buffer = ""

        elif self.state == "parsing_key":
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

        elif self.state == "expecting_colon":
            if ch == ":":
                self.state_stack.pop()
                self.state_stack.append("expecting_value")

        elif self.state == "expecting_value":
            if ch == '"':
                self.state_stack.pop()
                self.state_stack.append("streaming_string")
                if not self.current_key:
                    raise ValueError("Current key is not set before streaming string.")
                self.current_sink = self._ensure_attribute(self.current_key)
                self.string_escape = False
            elif ch in "0123456789-tfn":
                self.state_stack.pop()
                self.state_stack.append("expecting_primitive")
                if not self.current_key:
                    raise ValueError(
                        "Current key is not set before expecting primitive."
                    )
                self.current_sink = self._ensure_attribute(self.current_key)
                self.buffer = ch
            elif ch == "{":
                self.state_stack.append("parsing_object")
                if not self.current_key:
                    raise ValueError("Current key is not set before parsing object.")
                self.current_sink = self._ensure_attribute(self.current_key)

                NestedJmux = self.current_sink.underlying_generic()
                if not issubclass(NestedJmux, JMux):
                    raise TypeError(
                        f"Current sink {self.current_sink} must be a subclass of JMux."
                    )
                self.child_object = NestedJmux()
                await self._emit(self.child_object)
                self.curly_brace_depth = 1
                await self._close_sink()
                await self._feed_to_child(ch)

        elif self.state == "expecting_primitive":
            if ch not in ",}":
                self.buffer += ch
            else:
                self.state_stack.pop()
                if self.buffer == "null":
                    await self._emit(None)
                elif self.buffer == "true":
                    await self._emit(True)
                elif self.buffer == "false":
                    await self._emit(False)
                else:
                    try:
                        value = (
                            float(self.buffer)
                            if "." in self.buffer
                            else int(self.buffer)
                        )
                        await self._emit(value)
                    except ValueError as e:
                        raise ValueError(
                            f"Invalid primitive value: {self.buffer}"
                        ) from e
                self.buffer = ""
                await self._close_sink()

        elif self.state == "streaming_string":
            if self.string_escape:
                await self._emit(self._unescape(ch))
                self.string_escape = False
            elif ch == "\\":
                self.string_escape = True
            elif ch == '"':
                self.state_stack.pop()
                if isinstance(self.current_sink, AwaitableValue):
                    await self.current_sink.put(self.buffer)
                    self.buffer = ""
                await self._close_sink()
            else:
                if isinstance(self.current_sink, StreamableValues):
                    await self._emit(ch)
                elif isinstance(self.current_sink, AwaitableValue):
                    self.buffer += ch
                else:
                    raise TypeError(
                        f"Current sink {self.current_sink} does not support streaming."
                    )

        elif self.state == "parsing_object":
            await self._feed_to_child(ch)
            if ch == "{":
                self.curly_brace_depth += 1
            elif ch == "}":
                self.curly_brace_depth -= 1
                if self.curly_brace_depth == 0:
                    self.child_object = None
                    await self._close_sink()
                    self.state_stack.pop()
                    self.state_stack.append("expecting_key")

        elif ch == "{":
            self.state_stack.append("expecting_key")

        elif ch == "}":
            if self.state_stack and self.state_stack[-1] == "parsing_object":
                self.curly_brace_depth -= 1
                if self.curly_brace_depth == 0:
                    self.child_object = None
                    await self._close_sink()
                    self.state_stack.pop()
            else:
                raise ValueError("Unexpected '}' character outside of an object.")

    def _ensure_attribute(self, attr_name: str) -> IAsyncSink:
        if not hasattr(self, attr_name):
            raise AttributeError(f"Attribute '{attr_name}' is not defined in JMux.")
        return getattr(self, attr_name)

    async def _emit(self, ch) -> None:
        if self.current_sink:
            await self.current_sink.put(ch)

    async def _feed_to_child(self, ch: str) -> None:
        if not self.child_object:
            raise ValueError("No child object to feed characters to.")
        await self.child_object.feed_char(ch)

    async def _close_sink(self) -> None:
        if self.current_sink:
            await self.current_sink.close()
        self.current_sink = None

    def _unescape(self, ch: str) -> str:
        return self.escape_map.get(ch, ch)
