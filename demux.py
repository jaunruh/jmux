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
from jmux.error import (
    EmptyKeyError,
    MissingAttributeError,
    NoCurrentSinkError,
    ParsePrimitiveError,
    TypeEmitError,
    UnexpectedAttributeTypeError,
    UnexpectedCharacterError,
)
from jmux.helpers import is_json_whitespace
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
    "parsing_integer",
    "parsing_float",
    "parsing_boolean",
    "parsing_null",
    "parsing_object",
]

PRIMITIVE_STATES: List[State] = [
    "parsing_integer",
    "parsing_float",
    "parsing_boolean",
    "parsing_null",
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
            raise NoCurrentSinkError()
        return self._current_sink.get_sink_type()

    @property
    def current_underlying_generic(self) -> type[T]:
        if self._current_sink is None:
            raise NoCurrentSinkError()
        return self._current_sink.get_underlying_generic()

    def set_current(self, attr_name: str) -> None:
        if not hasattr(self._delegate, attr_name):
            raise MissingAttributeError(
                object_name=self._delegate.__class__.__name__,
                attribute=attr_name,
            )
        sink = getattr(self._delegate, attr_name)
        if not isinstance(sink, IAsyncSink):
            raise UnexpectedAttributeTypeError(
                attribute=attr_name,
                object_name=type(sink).__name__,
                expected_type="IAsyncSink",
            )
        self._current_key = attr_name
        self._current_sink = sink

    async def emit(self, val: T) -> None:
        if self._current_sink is None:
            raise NoCurrentSinkError()
        underlying_generic = self._current_sink.get_underlying_generic()
        if not isinstance(val, underlying_generic):
            raise TypeEmitError(
                expected_type=f"{underlying_generic.__name__}",
                actual_type=f"{type(val).__name__}",
            )
        await self._current_sink.put(val)

    async def close(self) -> None:
        if self._current_sink is None:
            raise NoCurrentSinkError()
        await self._current_sink.close()

    async def create_and_emit_nested(self) -> None:
        if self._current_sink is None:
            raise NoCurrentSinkError()
        NestedJmux = self._current_sink.get_underlying_generic()
        if not issubclass(NestedJmux, JMux):
            raise TypeEmitError(
                expected_type="JMux",
                actual_type=f"{NestedJmux.__name__}",
            )
        nested = NestedJmux()
        await self.emit(nested)

    async def forward_char(self, ch: str) -> None:
        if self._current_sink is None:
            raise NoCurrentSinkError()
        maybe_jmux = self._current_sink.get_current()
        if not isinstance(maybe_jmux, JMux):
            raise TypeEmitError(
                expected_type="JMux",
                actual_type=f"{type(maybe_jmux).__name__}",
            )
        await maybe_jmux.feed_char(ch)


class JMux(ABC):
    def __init__(self):
        self._instantiate_attributes()
        self._history: List[str] = []
        self.pda: PushDownAutomata[Mode, State] = PushDownAutomata[Mode, State]("start")
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

        # CONTEXT: Start
        if self.pda.top is None:
            if self.pda.state == "start":
                if ch == "{":
                    self.pda.push("$")
                    self.pda.set_state("expect_key")
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self.pda.stack,
                        self.pda.state,
                        "JSON must start with '{' character.",
                    )

        # CONTEXT: Root
        if self.pda.top == "$":
            if self.pda.state == "expect_key":
                if is_json_whitespace(ch):
                    return
                elif ch == '"':
                    self.pda.set_state("parsing_key")
                    self.decoder.reset()
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self.pda.stack,
                        self.pda.state,
                        f"Expected '\"' in state '{self.pda.state}', got '{ch}'.",
                    )

            if self.pda.state == "parsing_key":
                if self.decoder.is_terminating_quote(ch):
                    buffer = self.decoder.buffer
                    if not buffer:
                        raise EmptyKeyError("Empty key is not allowed in JSON objects.")
                    self.sink.set_current(buffer)
                    self.decoder.reset()
                    self.pda.set_state("expect_colon")
                    return
                else:
                    self.decoder.push(ch)
                    return

            if self.pda.state == "expect_colon":
                if is_json_whitespace(ch):
                    return
                elif ch == ":":
                    self.pda.set_state("expect_value")
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self.pda.stack,
                        self.pda.state,
                        f"Expected ':' in state '{self.pda.state}', got '{ch}'.",
                    )

            if self.pda.state == "expect_value":
                if is_json_whitespace(ch):
                    return
                elif res := await self._handle_common__expect_value(ch):
                    if (
                        self.sink.current_sink_type == "StreamableValues"
                        and res != "parsing_string"
                    ):
                        raise UnexpectedCharacterError(
                            ch,
                            self.pda.stack,
                            self.pda.state,
                            f"Expected '[' or '\"' in state '{self.pda.state}' for  'StreamableValues', got '{ch}'.",
                        )
                    return
                elif ch == "[":
                    self.pda.set_state("expect_value")
                    self.pda.push("array")
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self.pda.stack,
                        self.pda.state,
                        f"Expected value, '[', or white space in state '{self.pda.state}', got '{ch}'.",
                    )

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

            if self.pda.state in PRIMITIVE_STATES:
                if ch not in ",}":
                    self._assert_primitive_character_allowed_in_state(ch)
                    self.decoder.push(ch)
                    return
                else:
                    await self._parse_primitive(ch)
                    await self.sink.close()
                    self.decoder.reset()
                    self.pda.set_state("expect_key")
                    return

            if self.pda.state == "expect_comma_or_eoc":
                if is_json_whitespace(ch):
                    return
                elif ch == ",":
                    self.pda.set_state("expect_key")
                    return
                elif ch == "}":
                    await self._emit_and_close_context("end")
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self.pda.stack,
                        self.pda.state,
                        f"Expected ',', '}}' or white space in state '{self.pda.state}', got '{ch}'.",
                    )
        # CONTEXT: Array
        if self.pda.top == "array":
            if ch == "[":
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    "No support for 2-dimensional arrays.",
                )

            if self.pda.state == "expect_value":
                if is_json_whitespace(ch):
                    return
                elif await self._handle_common__expect_value(ch):
                    return
                elif ch == "]":
                    await self._emit_and_close_context("expect_comma_or_eoc")
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self.pda.stack,
                        self.pda.state,
                        f"Expected value, ']' or white space in state '{self.pda.state}', got '{ch}'.",
                    )

            if self.pda.state == "parsing_string":
                if self.sink.current_sink_type == "AwaitableValue":
                    raise UnexpectedCharacterError(
                        ch,
                        self.pda.stack,
                        self.pda.state,
                        "Cannot parse string in an array with AwaitableValue sink type.",
                    )
                if self.decoder.is_terminating_quote(ch):
                    await self.sink.emit(self.decoder.buffer)
                    self.decoder.reset()
                    self.pda.set_state("expect_comma_or_eoc")
                    return
                else:
                    self.decoder.push(ch)
                    return

            if self.pda.state in PRIMITIVE_STATES:
                if ch not in ",]":
                    self._assert_primitive_character_allowed_in_state(ch)
                    self.decoder.push(ch)
                    return
                else:
                    await self._parse_primitive(ch)
                    self.decoder.reset()
                    if ch == ",":
                        self.pda.set_state("expect_value")
                    elif ch == "]":
                        await self._emit_and_close_context("expect_comma_or_eoc")
                    return

            if self.pda.state == "expect_comma_or_eoc":
                if is_json_whitespace(ch):
                    return
                elif ch == ",":
                    self.pda.set_state("expect_value")
                    return
                elif ch == "]":
                    await self._emit_and_close_context("expect_comma_or_eoc")
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self.pda.stack,
                        self.pda.state,
                        f"Expected ',', ']' or white space in state '{self.pda.state}', got '{ch}'.",
                    )

        # CONTEXT: Object
        if self.pda.top == "object":
            if self.pda.state != "parsing_object":
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"State in object context must be 'parsing_object', got '{self.pda.state}'.",
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

    async def _parse_primitive(self, ch: str) -> None:
        if self.pda.state == "parsing_null":
            if not self.decoder.buffer == "null":
                raise ParsePrimitiveError(
                    f"Expected 'null', got '{self.decoder.buffer}'"
                )
            await self.sink.emit(None)
        elif self.pda.state == "parsing_boolean":
            await self.sink.emit(self.decoder.buffer == "true")
        else:
            try:
                buffer = self.decoder.buffer
                generic = self.sink.current_underlying_generic
                value = float(buffer) if issubclass(generic, float) else int(buffer)
            except ValueError as e:
                raise ParsePrimitiveError(f"Buffer: {buffer}; Error: {e}") from e
            await self.sink.emit(value)

    async def _handle_common__expect_value(self, ch: str) -> State | None:
        generic = self.sink.current_underlying_generic
        if ch == '"':
            if generic is not str:
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"Trying to parse string but underlying generic is '{generic.__name__}', expected 'str'.",
                )
            self.pda.set_state("parsing_string")
            self.decoder.reset()
            return "parsing_string"
        if ch in "0123456789-":
            if generic not in (int, float):
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"Trying to parse number but underlying generic is '{generic.__name__}', expected 'int' or 'float'.",
                )
            self.decoder.push(ch)
            if generic is int:
                self.pda.set_state("parsing_integer")
                return "parsing_integer"
            else:
                self.pda.set_state("parsing_float")
                return "parsing_float"
        if ch in "tf":
            if generic is not bool:
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"Trying to parse boolean but underlying generic is '{generic.__name__}', expected 'bool'.",
                )
            self.pda.set_state("parsing_boolean")
            self.decoder.push(ch)
            return "parsing_boolean"
        if ch in "n":
            if generic is not type(None):
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"Trying to parse null but underlying generic is '{generic.__name__}', expected 'NoneType'.",
                )
            self.pda.set_state("parsing_null")
            self.decoder.push(ch)
            return "parsing_null"
        if ch == "{":
            if not issubclass(generic, JMux):
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"Trying to parse object but underlying generic is '{generic.__name__}', expected 'JMux'.",
                )
            await self.sink.create_and_emit_nested()
            await self.sink.forward_char(ch)
            self.pda.set_state("parsing_object")
            self.pda.push("object")
            return "parsing_object"

    async def _emit_and_close_context(self, new_state: State) -> None:
        await self.sink.close()
        self.pda.pop()
        self.pda.set_state(new_state)

    def _assert_primitive_character_allowed_in_state(self, ch: str) -> None:
        if self.pda.state == "parsing_integer":
            if ch not in "0123456789":
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"Unexpected character '{ch}' in state '{self.pda.state}'.",
                )
        elif self.pda.state == "parsing_float":
            if ch not in "0123456789-+eE.":
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"Unexpected character '{ch}' in state '{self.pda.state}'.",
                )
        elif self.pda.state == "parsing_boolean":
            if ch not in "truefals":
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"Unexpected character '{ch}' in state '{self.pda.state}'.",
                )
            if not (
                "true".startswith(f"{self.decoder.buffer}{ch}")
                or "false".startswith(f"{self.decoder.buffer}{ch}")
            ):
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"Unexpected character '{ch}' in state '{self.pda.state}'.",
                )
        elif self.pda.state == "parsing_null":
            if ch not in "nul":
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"Unexpected character '{ch}' in state '{self.pda.state}'.",
                )
            if not "null".startswith(f"{self.decoder.buffer}{ch}"):
                raise UnexpectedCharacterError(
                    ch,
                    self.pda.stack,
                    self.pda.state,
                    f"Unexpected character '{ch}' in state '{self.pda.state}'.",
                )
        else:
            raise UnexpectedCharacterError(
                ch,
                self.pda.stack,
                self.pda.state,
                f"Unexpected character '{ch}' in state '{self.pda.state}'.",
            )
