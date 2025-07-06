from abc import ABC
from typing import (
    List,
    Literal,
    Optional,
    get_args,
    get_origin,
    get_type_hints,
)

from jmux.decoder import StringDecoder
from jmux.pda import PushDownAutomata
from jmux.types import IAsyncSink, SinkType

type Primitive = int | float | str | bool | None
type Emittable = Primitive | "JMux"


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
        self.pda: PushDownAutomata = PushDownAutomata[Mode, State]("start")
        self.decoder: StringDecoder = StringDecoder()
        self.sink = Sink[Emittable](self)

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
        self._assert_state_allowed(ch)

        if self.pda.state == "expect_value":
            if ch == '"':
                self.pda.set_state("parsing_string")
                self.decoder.reset()
                return
            if ch in "0123456789-tfn":
                self.pda.set_state("parsing_primitive")
                self.decoder.push(ch)
                return

        # CONTEXT: Start
        if self.pda.top is None:
            if self.pda.state == "start" and ch == "{":
                self.pda.push("$")
                self.pda.set_state("expect_key")
                return

        # CONTEXT: Root
        if self.pda.top == "$":
            if self.pda.state == "parsing_string":
                if self.decoder.is_terminating_quote(ch):
                    if self.sink.current_sink_type == "AwaitableValue":
                        await self.sink.emit(self.decoder.buffer)
                    self.decoder.reset()
                    await self.sink.close()
                    self.pda.set_state("expect_comma_or_eoc")
                    return
                else:
                    self.decoder.push(ch)
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
                self.decoder.reset()
                return

            if self.pda.state == "parsing_key":
                if self.decoder.is_terminating_quote(ch):
                    self.sink.set_current(self.decoder.buffer)
                    self.decoder.reset()
                    self.pda.set_state("expect_colon")
                    return
                else:
                    self.decoder.push(ch)
                    return

            if self.pda.state == "parsing_primitive":
                if ch not in ",}":
                    self.decoder.push(ch)
                    return
                else:
                    if self.decoder.buffer == "null":
                        await self.sink.emit(None)
                    elif self.decoder.buffer == "true":
                        await self.sink.emit(True)
                    elif self.decoder.buffer == "false":
                        await self.sink.emit(False)

                    else:
                        try:
                            buffer = self.decoder.buffer
                            value = float(buffer) if "." in buffer else int(buffer)
                            await self.sink.emit(value)
                        except ValueError as e:
                            raise ValueError(
                                f"Invalid primitive value: {buffer}"
                            ) from e
                    await self.sink.close()
                    self.decoder.reset()
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
                if self.decoder.is_terminating_quote(ch):
                    await self.sink.emit(self.decoder.buffer)
                    self.decoder.reset()
                    self.pda.set_state("expect_comma_or_eoc")
                    return
                else:
                    self.decoder.push(ch)
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
                    self.decoder.push(ch)
                    return
                else:
                    if self.decoder.buffer == "null":
                        await self.sink.emit(None)
                    elif self.decoder.buffer == "true":
                        await self.sink.emit(True)
                    elif self.decoder.buffer == "false":
                        await self.sink.emit(False)
                    else:
                        try:
                            buffer = self.decoder.buffer
                            value = float(buffer) if "." in buffer else int(buffer)
                            await self.sink.emit(value)
                        except ValueError as e:
                            raise ValueError(
                                f"Error parsing primitive value, buffer: {buffer}, {e}"
                            ) from e
                    self.decoder.reset()
                    if ch == ",":
                        self.pda.set_state("expect_value")
                    elif ch == "]":
                        await self.sink.close()
                        self.pda.pop()
                        self.pda.set_state("expect_comma_or_eoc")
                    return

        # CONTEXT: Object
        if self.pda.top == "object":
            if ch == "}":
                self.pda.pop()
                if self.pda.top == "$":
                    await self.sink.close()
                self.pda.set_state("expect_comma_or_eoc")
                return
            else:
                await self.sink.forward_char(ch)
                return

    def _assert_state_allowed(self, ch: str) -> None:
        if self.pda.state == "start" and ch != "{":
            raise ValueError("JSON must start with '{' character.")

        if self.pda.top == "array" and ch == "[":
            raise ValueError("No support for 2-dimensional arrays.")

        if (
            self.pda.top == "array"
            and self.pda.state == "parsing_string"
            and self.sink.current_sink_type == "AwaitableValue"
        ):
            raise ValueError(
                "Cannot parse string in an array with AwaitableValue sink type."
            )

        if self.pda.top == "object" and self.pda.state != "parsing_object":
            raise ValueError(
                f"State in object context must be 'parsing_object', got '{self.pda.state}'."
            )

        if (
            self.pda.state == "expect_comma_or_eoc"
            and not ch.isspace()
            and ch not in ",}]"
        ):
            raise ValueError(
                f"Expected ',', '}}', ']' or white space in state '{self.pda.state}', got '{ch}'."
            )

        if self.pda.state == "expect_colon" and not ch.isspace() and ch != ":":
            raise ValueError(f"Expected ':' in state '{self.pda.state}', got '{ch}'.")
