from abc import ABC
from types import NoneType
from typing import (
    List,
    Literal,
    Optional,
    Set,
    Type,
    get_args,
    get_origin,
    get_type_hints,
)

from jmux.decoder import StringDecoder
from jmux.error import (
    EmptyKeyError,
    MissingAttributeError,
    NoCurrentSinkError,
    NotAllPropertiesSetError,
    NothingEmittedError,
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
    def current_underlying_generics(self) -> Set[Type[T]]:
        if self._current_sink is None:
            raise NoCurrentSinkError()
        return self._current_sink.get_underlying_generics()

    @property
    def current_underlying_main_generic(self) -> Type[T]:
        if self._current_sink is None:
            raise NoCurrentSinkError()
        return self._current_sink.get_underlying_main_generic()

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
        generics = self._current_sink.get_underlying_generics()
        if not any(
            isinstance(val, underlying_generic) for underlying_generic in generics
        ):
            raise TypeEmitError(
                expected_type=f"{generics}",
                actual_type=f"{type(val).__name__}",
            )
        await self._current_sink.put(val)

    async def close(self) -> None:
        if self._current_sink is None:
            raise NoCurrentSinkError()
        await self._current_sink.close()

    async def ensure_closed(self) -> None:
        if self._current_sink is None:
            raise NoCurrentSinkError()
        await self._current_sink.ensure_closed()

    async def create_and_emit_nested(self) -> None:
        if self._current_sink is None:
            raise NoCurrentSinkError()
        NestedJmux = self._current_sink.get_underlying_main_generic()
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
        self._pda: PushDownAutomata[Mode, State] = PushDownAutomata[Mode, State](
            "start"
        )
        self._decoder: StringDecoder = StringDecoder()
        self._sink = Sink[Emittable](self)

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
        if self._pda.top is None:
            if self._pda.state == "start":
                if ch == "{":
                    self._pda.push("$")
                    self._pda.set_state("expect_key")
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self._pda.stack,
                        self._pda.state,
                        "JSON must start with '{' character.",
                    )

        # CONTEXT: Root
        if self._pda.top == "$":
            if self._pda.state == "expect_key":
                if is_json_whitespace(ch):
                    return
                elif ch == '"':
                    self._pda.set_state("parsing_key")
                    self._decoder.reset()
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self._pda.stack,
                        self._pda.state,
                        "Char needs to be '\"' or JSON whitespaces",
                    )

            if self._pda.state == "parsing_key":
                if self._decoder.is_terminating_quote(ch):
                    buffer = self._decoder.buffer
                    if not buffer:
                        raise EmptyKeyError("Empty key is not allowed in JSON objects.")
                    self._sink.set_current(buffer)
                    self._decoder.reset()
                    self._pda.set_state("expect_colon")
                    return
                else:
                    self._decoder.push(ch)
                    return

            if self._pda.state == "expect_colon":
                if is_json_whitespace(ch):
                    return
                elif ch == ":":
                    self._pda.set_state("expect_value")
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self._pda.stack,
                        self._pda.state,
                        "Char must be ':' or JSON whitespaces.",
                    )

            if self._pda.state == "expect_value":
                if is_json_whitespace(ch):
                    return
                elif res := await self._handle_common__expect_value(ch):
                    if (
                        self._sink.current_sink_type == "StreamableValues"
                        and res != "parsing_string"
                    ):
                        raise UnexpectedCharacterError(
                            ch,
                            self._pda.stack,
                            self._pda.state,
                            "Expected '[' or '\"' for 'StreamableValues'",
                        )
                    return
                elif ch == "[":
                    self._pda.set_state("expect_value")
                    self._pda.push("array")
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self._pda.stack,
                        self._pda.state,
                        "Expected '[' or white space.",
                    )

            if self._pda.state == "parsing_string":
                if self._decoder.is_terminating_quote(ch):
                    if self._sink.current_sink_type == "AwaitableValue":
                        await self._sink.emit(self._decoder.buffer)
                    self._decoder.reset()
                    await self._sink.close()
                    self._pda.set_state("expect_comma_or_eoc")
                    return
                else:
                    self._decoder.push(ch)
                    if self._sink.current_sink_type == "StreamableValues":
                        await self._sink.emit(ch)
                    return

            if self._pda.state in PRIMITIVE_STATES:
                if ch not in ",}":
                    self._assert_primitive_character_allowed_in_state(ch)
                    self._decoder.push(ch)
                    return
                else:
                    await self._parse_primitive(ch)
                    await self._sink.close()
                    self._decoder.reset()
                    self._pda.set_state("expect_key")
                    if ch == "}":
                        await self._finalize()
                    return

            if self._pda.state == "expect_comma_or_eoc":
                if is_json_whitespace(ch):
                    return
                elif ch == ",":
                    self._pda.set_state("expect_key")
                    return
                elif ch == "}":
                    await self._finalize()
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self._pda.stack,
                        self._pda.state,
                        "Expected ',', '}' or white space.",
                    )

        # CONTEXT: Array
        if self._pda.top == "array":
            if ch == "[":
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    "No support for 2-dimensional arrays.",
                )

            if self._pda.state == "expect_value":
                if is_json_whitespace(ch):
                    return
                elif await self._handle_common__expect_value(ch):
                    return
                elif ch == "]":
                    await self._close_context("expect_comma_or_eoc")
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self._pda.stack,
                        self._pda.state,
                        "Expected value, ']' or white space",
                    )

            if self._pda.state == "parsing_string":
                if self._sink.current_sink_type == "AwaitableValue":
                    raise UnexpectedCharacterError(
                        ch,
                        self._pda.stack,
                        self._pda.state,
                        "Cannot parse string inside of an array with AwaitableValue sink type.",
                    )
                if self._decoder.is_terminating_quote(ch):
                    await self._sink.emit(self._decoder.buffer)
                    self._decoder.reset()
                    self._pda.set_state("expect_comma_or_eoc")
                    return
                else:
                    self._decoder.push(ch)
                    return

            if self._pda.state in PRIMITIVE_STATES:
                if ch not in ",]":
                    self._assert_primitive_character_allowed_in_state(ch)
                    self._decoder.push(ch)
                    return
                else:
                    await self._parse_primitive(ch)
                    self._decoder.reset()
                    if ch == ",":
                        self._pda.set_state("expect_value")
                    elif ch == "]":
                        await self._close_context("expect_comma_or_eoc")
                    return

            if self._pda.state == "expect_comma_or_eoc":
                if is_json_whitespace(ch):
                    return
                elif ch == ",":
                    self._pda.set_state("expect_value")
                    return
                elif ch == "]":
                    await self._close_context("expect_comma_or_eoc")
                    return
                else:
                    raise UnexpectedCharacterError(
                        ch,
                        self._pda.stack,
                        self._pda.state,
                        "Expected ',', ']' or white space.",
                    )

        # CONTEXT: Object
        if self._pda.top == "object":
            if self._pda.state != "parsing_object":
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    "State in object context must be 'parsing_object'",
                )
            if ch == "}":
                self._pda.pop()
                if self._pda.top == "$":
                    await self._sink.close()
                self._pda.set_state("expect_comma_or_eoc")
                return
            else:
                await self._sink.forward_char(ch)
                return

    async def _parse_primitive(self, ch: str) -> None:
        if self._pda.state == "parsing_null":
            if not self._decoder.buffer == "null":
                raise ParsePrimitiveError(
                    f"Expected 'null', got '{self._decoder.buffer}'"
                )
            await self._sink.emit(None)
        elif self._pda.state == "parsing_boolean":
            await self._sink.emit(self._decoder.buffer == "true")
        else:
            try:
                buffer = self._decoder.buffer
                generic = self._sink.current_underlying_main_generic
                value = float(buffer) if issubclass(generic, float) else int(buffer)
            except ValueError as e:
                raise ParsePrimitiveError(f"Buffer: {buffer}; Error: {e}") from e
            await self._sink.emit(value)

    async def _handle_common__expect_value(self, ch: str) -> State | None:
        generic_set = self._sink.current_underlying_generics
        generic = self._sink.current_underlying_main_generic
        if ch == '"':
            if str not in generic_set:
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    f"Trying to parse 'string' but underlying generic is '{generic_set}'.",
                )
            self._pda.set_state("parsing_string")
            self._decoder.reset()
            return "parsing_string"
        if ch in "0123456789-":
            if not any(t in generic_set for t in (int, float)):
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    f"Trying to parse 'number' but underlying generic is '{generic_set}'.",
                )
            self._decoder.push(ch)
            if generic is int:
                self._pda.set_state("parsing_integer")
                return "parsing_integer"
            else:
                self._pda.set_state("parsing_float")
                return "parsing_float"
        if ch in "tf":
            if bool not in generic_set:
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    f"Trying to parse 'boolean' but underlying generic is '{generic.__name__}'.",
                )
            self._pda.set_state("parsing_boolean")
            self._decoder.push(ch)
            return "parsing_boolean"
        if ch in "n":
            if NoneType not in generic_set:
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    f"Trying to parse 'null' but underlying generic is '{generic.__name__}'.",
                )
            self._pda.set_state("parsing_null")
            self._decoder.push(ch)
            return "parsing_null"
        if ch == "{":
            if not issubclass(generic, JMux):
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    f"Trying to parse 'object' but underlying generic is '{generic.__name__}'.",
                )
            await self._sink.create_and_emit_nested()
            await self._sink.forward_char(ch)
            self._pda.set_state("parsing_object")
            self._pda.push("object")
            return "parsing_object"

    async def _close_context(self, new_state: State) -> None:
        await self._sink.close()
        self._pda.pop()
        self._pda.set_state(new_state)

    async def _finalize(self) -> None:
        type_hints = get_type_hints(self.__class__)
        for attr_name, _ in type_hints.items():
            self._sink.set_current(attr_name)
            try:
                await self._sink.ensure_closed()
            except NothingEmittedError as e:
                raise NotAllPropertiesSetError(
                    f"Unable to finalize. Property '{attr_name}' was not set before closing the JMux instance."
                ) from e

        self._pda.pop()
        self._pda.set_state("end")

    def _assert_primitive_character_allowed_in_state(self, ch: str) -> None:
        if self._pda.state == "parsing_integer":
            if ch not in "0123456789":
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    "Trying to parse 'integer' but received unexpected character.",
                )
        elif self._pda.state == "parsing_float":
            if ch not in "0123456789-+eE.":
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    "Trying to parse 'float' but received unexpected character.",
                )
        elif self._pda.state == "parsing_boolean":
            if ch not in "truefals":
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    "Trying to parse 'boolean' but received unexpected character.",
                )
            if not (
                "true".startswith(f"{self._decoder.buffer}{ch}")
                or "false".startswith(f"{self._decoder.buffer}{ch}")
            ):
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    f"Unexpected character added to buffer for 'boolean': '{self._decoder.buffer}{ch}'.",
                )
        elif self._pda.state == "parsing_null":
            if ch not in "nul":
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    "Trying to parse 'null' but received unexpected character.",
                )
            if not "null".startswith(f"{self._decoder.buffer}{ch}"):
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    f"Unexpected character added to buffer for 'null': '{self._decoder.buffer}{ch}'.",
                )
        else:
            raise UnexpectedCharacterError(
                ch,
                self._pda.stack,
                self._pda.state,
                "An unexpected error happened.",
            )
