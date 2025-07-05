from abc import ABC
from asyncio import Event, Queue
from typing import (
    AsyncGenerator,
    List,
    Literal,
    Optional,
    Protocol,
    Type,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)

type Primitive = int | float | str | bool | None
type Emittable = Primitive | "JMux"
type SinkType = Literal["StreamableValues", "AwaitableValue"]


class UnderlyingGenericMixin[T]:
    def get_underlying_generic(self) -> Type[T]:
        # `__orig_class__` is only set after the `__init__` method is called
        if not hasattr(self, "__orig_class__"):
            raise TypeError(
                "AwaitableValue must be initialized with a defined generic type."
            )

        Origin = getattr(self, "__orig_class__")
        if len(Origin.__args__) != 1:
            raise TypeError(
                f"AwaitableValue must be initialized with a single generic type, got {Origin.__args__}."
            )
        Generic: Type[T] = Origin.__args__[0]
        return Generic


class StreamableValues[T: Emittable](UnderlyingGenericMixin[T]):
    def __init__(self):
        self._queue = Queue[T | None]()
        self._last_item: T | None = None
        self._closed = False

    async def put(self, item: T):
        if self._closed:
            raise ValueError("Cannot put item into a closed sink.")
        self._last_item = item
        await self._queue.put(item)

    async def close(self):
        self._closed = True
        await self._queue.put(None)

    def get_current(self) -> T:
        if self._last_item is None:
            raise ValueError("StreamableValues has not received any items yet.")
        return self._last_item

    def get_sink_type(self) -> SinkType:
        return "StreamableValues"

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


class AwaitableValue[T: Emittable](UnderlyingGenericMixin[T]):
    def __init__(self):
        self._value_set = False
        self._event = Event()
        self._value: T | None = None

    async def put(self, value: T):
        if self._value:
            raise ValueError("AwaitableValue can only be set once.")
        self._value_set = True
        self._value = value
        self._event.set()

    async def close(self):
        pass

    def get_current(self) -> T:
        if not self._value:
            raise ValueError("AwaitableValue has not been set yet.")
        return self._value

    def get_sink_type(self) -> SinkType:
        return "AwaitableValue"

    def __await__(self):
        return self._wait().__await__()

    async def _wait(self) -> T:
        await self._event.wait()
        if self._value is None and not self._value_set:
            raise ValueError("No value has been put into the sink.")
        return cast(T, self._value)


@runtime_checkable
class IAsyncSink[T: Emittable](Protocol):
    def get_underlying_generic(self) -> Type[T]:
        """Return the underlying generic type of the sink."""
        ...

    async def put(self, item: T):
        """Put an item into the sink."""
        ...

    async def close(self):
        """Close the sink."""
        ...

    def get_current(self) -> T:
        """Get the current value from the sink."""
        ...

    def get_sink_type(self) -> SinkType:
        """Get the type of the sink."""
        ...


type State = Literal[
    "start",
    "end",
    "error",
    # expect
    "expect_key",
    "expect_colon",
    "expect_value",
    "expect_comma_or_eoc",
    # parsing
    "parsing_key",
    "parsing_string",
    "parsing_primitive",
    "parsing_object",
]

type Mode = Literal[
    "$",
    "object",
    "array",
]

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


class Pda:
    def __init__(self):
        self._stack: List[Mode] = []
        self._state: State = "start"

    @property
    def state(self) -> State:
        return self._state

    @property
    def top(self) -> Mode | None:
        if not self._stack:
            return None
        return self._stack[-1]

    def set_state(self, new_state: State) -> None:
        self._state = new_state

    def push(self, mode: Mode) -> None:
        self._stack.append(mode)

    def pop(self) -> Mode:
        if not self._stack:
            raise IndexError("PDA stack is empty.")
        return self._stack.pop()


class TextBuffer:
    def __init__(self):
        self._buffer = ""
        self._string_escape = False

    def push(self, ch: str) -> None:
        if self._string_escape:
            self._buffer += escape_map.get(ch, ch)
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


class Sink[T: Emittable]:
    def __init__(self, delegate: "JMux"):
        self._current_key: Optional[str] = None
        self._current_sink: Optional[IAsyncSink[T]] = None
        self._delegate: "JMux" = delegate

    @property
    def current_sink_type(self) -> SinkType:
        if self._current_sink is None:
            raise ValueError("No current sink is set.")
        return self._current_sink.get_sink_type()

    def set_current(self, attr_name: str) -> None:
        if not hasattr(self._delegate, attr_name):
            raise AttributeError(
                f"Attribute '{attr_name}' is not defined in JMux {self._delegate.__class__.__name__}."
            )
        sink: IAsyncSink = getattr(self._delegate, attr_name)
        if not isinstance(sink, IAsyncSink):
            raise TypeError(
                f"Attribute '{attr_name}' must conform to protocol IAsyncSink, got {type(sink)}."
            )
        self._current_key = attr_name
        self._current_sink = sink

    async def emit(self, val: T) -> None:
        if self._current_sink is None:
            raise ValueError("No current sink is set.")
        await self._current_sink.put(val)

    async def close(self) -> None:
        if self._current_sink is None:
            raise ValueError("No current sink is set.")
        await self._current_sink.close()

    async def create_and_emit_nested(self) -> None:
        if self._current_sink is None:
            raise ValueError("No current sink is set.")
        NestedJmux = self._current_sink.get_underlying_generic()
        if not issubclass(NestedJmux, JMux):
            raise TypeError(
                f"Cannot emit nested JMux, current sink {self._current_sink} must be a subclass of JMux."
            )
        nested = NestedJmux()
        await self.emit(nested)

    async def forward_char(self, ch: str) -> None:
        if self._current_sink is None:
            raise ValueError("No current sink is set.")
        maybe_jmux = self._current_sink.get_current()
        if not isinstance(maybe_jmux, JMux):
            raise TypeError(
                f"Current sink {self._current_sink} must be a JMux instance to forward characters."
            )
        await maybe_jmux.feed_char(ch)


class JMux(ABC):
    def __init__(self):
        self._instantiate_attributes()
        self._history: List[str] = []
        self.pda: Pda = Pda()
        self.text_parser: TextBuffer = TextBuffer()
        self.sink = Sink(self)

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

    async def feed_char(self, ch: str) -> None:
        self._history.append(ch)

        if self.pda.state == "start" and ch != "{":
            raise ValueError("JSON must start with '{' character.")

        if self.pda.state == "start" and ch == "{":
            self.pda.push("$")
            self.pda.set_state("expect_key")
            return

        if self.pda.state == "expect_value":
            if ch == '"':
                self.pda.set_state("parsing_string")
                self.text_parser.reset()
                return
            if ch in "0123456789-tfn":
                self.pda.set_state("parsing_primitive")
                self.text_parser.push(ch)
                return

        # CONTEXT: Root
        if self.pda.top == "$":
            if self.pda.state == "parsing_string":
                if self.text_parser.is_terminating_quote(ch):
                    if self.sink.current_sink_type == "AwaitableValue":
                        await self.sink.emit(self.text_parser.buffer)
                    self.text_parser.reset()
                    await self.sink.close()
                    self.pda.set_state("expect_comma_or_eoc")
                    return
                else:
                    self.text_parser.push(ch)
                    if self.sink.current_sink_type == "StreamableValues":
                        await self.sink.emit(ch)
                    return

            if self.pda.state == "expect_comma_or_eoc":
                if ch == ",":
                    self.pda.set_state("expect_key")
                    return
                if ch == "}":
                    await self.sink.close()
                    self.pda.pop()
                    self.pda.set_state("end")
                    return

            if self.pda.state == "expect_key" and ch == '"':
                self.pda.set_state("parsing_key")
                self.text_parser.reset()
                return

            if self.pda.state == "parsing_key":
                if self.text_parser.is_terminating_quote(ch):
                    self.sink.set_current(self.text_parser.buffer)
                    self.text_parser.reset()
                    self.pda.set_state("expect_colon")
                    return
                else:
                    self.text_parser.push(ch)
                    return

            if self.pda.state == "parsing_primitive":
                if ch not in ",}":
                    self.text_parser.push(ch)
                    return
                else:
                    if self.text_parser.buffer == "null":
                        await self.sink.emit(None)
                    elif self.text_parser.buffer == "true":
                        await self.sink.emit(True)
                    elif self.text_parser.buffer == "false":
                        await self.sink.emit(False)

                    else:
                        try:
                            buffer = self.text_parser.buffer
                            value = float(buffer) if "." in buffer else int(buffer)
                            await self.sink.emit(value)

                        except ValueError as e:
                            raise ValueError(
                                f"Invalid primitive value: {buffer}"
                            ) from e
                    await self.sink.close()
                    self.text_parser.reset()
                    self.pda.set_state("expect_key")
                    return

            if self.pda.state == "expect_colon" and ch == ":":
                self.pda.set_state("expect_value")
                return

            if self.pda.state == "expect_value":
                if ch == "{":
                    await self.sink.create_and_emit_nested()
                    await self.sink.forward_char(ch)
                    self.pda.set_state("parsing_object")
                    self.pda.push("object")
                    return
                if ch == "[":
                    self.pda.set_state("expect_value")
                    self.pda.push("array")
                    return

        # CONTEXT: Array
        if self.pda.top == "array":
            if self.pda.state == "parsing_string":
                if self.sink.current_sink_type == "AwaitableValue":
                    raise ValueError(
                        "Cannot parse string in an array with AwaitableValue sink type."
                    )
                if self.text_parser.is_terminating_quote(ch):
                    await self.sink.emit(self.text_parser.buffer)
                    self.text_parser.reset()
                    self.pda.set_state("expect_comma_or_eoc")
                    return
                else:
                    self.text_parser.push(ch)
                    return

            if self.pda.state == "expect_comma_or_eoc":
                if ch == ",":
                    self.pda.set_state("expect_value")
                    return
                if ch == "]":
                    await self.sink.close()
                    self.pda.pop()
                    self.pda.set_state("expect_comma_or_eoc")
                    return

            if self.pda.state == "expect_value":
                # Most cases are handled above
                if ch == "{":
                    await self.sink.create_and_emit_nested()
                    await self.sink.forward_char(ch)
                    self.pda.set_state("parsing_object")
                    self.pda.push("object")
                    return
                if ch == "]":
                    await self.sink.close()
                    self.pda.pop()
                    self.pda.set_state("expect_comma_or_eoc")
                    return

            if self.pda.state == "parsing_primitive":
                if ch not in ",]":
                    self.text_parser.push(ch)
                    return
                else:
                    if self.text_parser.buffer == "null":
                        await self.sink.emit(None)
                    elif self.text_parser.buffer == "true":
                        await self.sink.emit(True)
                    elif self.text_parser.buffer == "false":
                        await self.sink.emit(False)
                    else:
                        try:
                            buffer = self.text_parser.buffer
                            value = float(buffer) if "." in buffer else int(buffer)
                            await self.sink.emit(value)
                        except ValueError as e:
                            raise ValueError(
                                f"Error parsing primitive value, buffer: {buffer}, {e}"
                            ) from e
                    self.text_parser.reset()
                    if ch == ",":
                        self.pda.set_state("expect_value")
                    elif ch == "]":
                        await self.sink.close()
                        self.pda.pop()
                        self.pda.set_state("expect_comma_or_eoc")
                    return

        # CONTEXT: Object
        if self.pda.top == "object":
            if self.pda.state != "parsing_object":
                raise ValueError(
                    "Cannot feed character to object, current state is not 'parsing_object'."
                )
            if ch == "}":
                self.pda.pop()
                if self.pda.top == "$":
                    await self.sink.close()
                self.pda.set_state("expect_comma_or_eoc")
                return
            else:
                await self.sink.forward_char(ch)
                return
