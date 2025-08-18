from abc import ABC
from enum import Enum
from types import NoneType
from typing import (
    Optional,
    Set,
    Type,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import BaseModel

from jmux.awaitable import AwaitableValue, IAsyncSink, SinkType, StreamableValues
from jmux.decoder import IDecoder, StringEscapeDecoder
from jmux.error import (
    EmptyKeyError,
    ForbiddenTypeHintsError,
    MissingAttributeError,
    NoCurrentSinkError,
    NotAllObjectPropertiesSetError,
    NothingEmittedError,
    ObjectAlreadyClosedError,
    ObjectMissmatchedError,
    ParsePrimitiveError,
    TypeEmitError,
    UnexpectedAttributeTypeError,
    UnexpectedCharacterError,
    UnexpectedStateError,
)
from jmux.helpers import (
    extract_types_from_generic_alias,
    get_main_type,
    str_to_bool,
)
from jmux.pda import PushDownAutomata
from jmux.types import (
    ARRAY_CLOSE,
    ARRAY_OPEN,
    BOOLEAN_ALLOWED,
    BOOLEAN_OPEN,
    COLON,
    COMMA,
    FLOAT_ALLOWED,
    INTERGER_ALLOWED,
    JSON_FALSE,
    JSON_NULL,
    JSON_TRUE,
    JSON_WHITESPACE,
    NULL_ALLOWED,
    NULL_OPEN,
    NUMBER_OPEN,
    OBJECT_CLOSE,
    OBJECT_OPEN,
    PARSING_PRIMITIVE_STATES,
    QUOTE,
)
from jmux.types import Mode as M
from jmux.types import State as S

type Primitive = int | float | str | bool | None
type Emittable = Primitive | "JMux" | Enum


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
    """
    JMux is an abstract base class for creating JSON demultiplexers.
    It parses a JSON stream and demultiplexes it into different sinks,
    which can be either AwaitableValue or StreamableValues.
    """

    def __init__(self):
        self._instantiate_attributes()
        self._pda: PushDownAutomata[M, S] = PushDownAutomata[M, S](S.START)
        self._decoder: IDecoder = StringEscapeDecoder()
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
                    f"Attribute '{attr_name}' must conform to protocol IAsyncSink, "
                    f"got {TargetType}."
                )
            setattr(self, attr_name, target_instance)

    @classmethod
    def assert_conforms_to(cls, pydantic_model: Type[BaseModel]) -> None:
        """
        Asserts that the JMux class conforms to a given Pydantic model.

        Args:
            pydantic_model: The Pydantic model to compare against.

        Raises:
            MissingAttributeError: If an attribute is missing in the Pydantic model.
            ForbiddenTypeHintsError: If a type hint is not allowed.
            ObjectMissmatchedError: If the JMux class does not match the Pydantic model.
        """
        for attr_name, type_alias in get_type_hints(cls).items():
            jmux_main_type_set, jmux_subtype_set = extract_types_from_generic_alias(
                type_alias
            )

            MaybePydanticType = get_type_hints(pydantic_model).get(attr_name, None)
            if MaybePydanticType is None:
                if NoneType in jmux_subtype_set:
                    continue
                else:
                    raise MissingAttributeError(
                        object_name=pydantic_model.__name__,
                        attribute=attr_name,
                    )

            pydantic_main_type_set, pydantic_subtype_set = (
                extract_types_from_generic_alias(MaybePydanticType)
            )
            cls._assert_only_allowed_types(
                jmux_main_type_set,
                jmux_subtype_set,
                pydantic_main_type_set,
                pydantic_subtype_set,
            )
            cls._assert_correct_set_combinations(
                jmux_main_type_set,
                pydantic_main_type_set,
                pydantic_subtype_set,
            )

            if StreamableValues in jmux_main_type_set:
                cls._assert_is_allowed_streamable_values(
                    jmux_subtype_set,
                    pydantic_subtype_set,
                    pydantic_main_type_set,
                    pydantic_model,
                    attr_name,
                )
            elif AwaitableValue in jmux_main_type_set:
                cls._assert_is_allowed_awaitable_value(
                    jmux_subtype_set,
                    pydantic_subtype_set,
                    pydantic_main_type_set,
                    pydantic_model,
                    attr_name,
                )
            else:
                raise ObjectMissmatchedError(
                    jmux_model=cls.__name__,
                    pydantic_model=pydantic_model.__name__,
                    attribute=attr_name,
                    message="Unexpected main type on JMux",
                )

    @classmethod
    def _assert_correct_set_combinations(
        cls,
        jmux_main_type_set: Set[Type],
        pydantic_main_type_set: Set[Type],
        pydantic_subtype_set: Set[Type],
    ):
        if (
            pydantic_wrong := (
                len(pydantic_main_type_set) != 1 and list not in pydantic_main_type_set
            )
            and len(pydantic_subtype_set) > 0
        ) or len(jmux_main_type_set) != 1:
            wrong_obj = "pydantic" if pydantic_wrong else "JMux"
            wrong_set = pydantic_main_type_set if pydantic_wrong else jmux_main_type_set
            raise ForbiddenTypeHintsError(
                message=(f"Forbidden typing received on {wrong_obj}: {wrong_set}"),
            )

    @classmethod
    def _assert_only_allowed_types(
        cls,
        jmux_main_type_set: Set[Type],
        jmux_subtype_set: Set[Type],
        pydantic_main_type_set: Set[Type],
        pydantic_subtype_set: Set[Type],
    ) -> None:
        if not all(t in (AwaitableValue, StreamableValues) for t in jmux_main_type_set):
            raise ForbiddenTypeHintsError(
                message=(
                    "JMux must have either AwaitableValue or StreamableValues as "
                    f"main type, got {jmux_main_type_set}."
                )
            )

        if not cls._all_elements_in_set_a_are_subclass_of_an_element_in_set_b(
            set_a=jmux_subtype_set,
            set_b={int, float, str, bool, NoneType, JMux, Enum},
        ):
            raise ForbiddenTypeHintsError(
                message=(
                    "JMux sub type must be one of the emittable types, got: "
                    f"{jmux_subtype_set}."
                )
            )

        if not cls._all_elements_in_set_a_are_subclass_of_an_element_in_set_b(
            set_a=pydantic_subtype_set,
            set_b={int, float, str, bool, NoneType, BaseModel, Enum},
        ):
            raise ForbiddenTypeHintsError(
                message=(
                    "Pydantic sub type must be one of the primitive, enum or "
                    f"BaseModel, got: {pydantic_subtype_set}."
                )
            )

        if not cls._all_elements_in_set_a_are_subclass_of_an_element_in_set_b(
            set_a=pydantic_main_type_set,
            set_b={int, float, str, bool, list, NoneType, BaseModel, Enum},
        ):
            raise ForbiddenTypeHintsError(
                message=(
                    "Pydantic main type must be one of the primitive, enum, list "
                    f"or BaseModel, got {pydantic_main_type_set}."
                )
            )

    @classmethod
    def _all_elements_in_set_a_are_subclass_of_an_element_in_set_b(
        cls, set_a: Set[Type], set_b: Set[Type]
    ) -> bool:
        return all(any(issubclass(elem, t) for t in set_b) for elem in set_a)

    @classmethod
    def _assert_is_allowed_streamable_values(
        cls,
        jmux_subtype_set: Set[Type],
        pydantic_subtype_set: Set[Type],
        pydantic_main_type_set: Set[Type],
        pydantic_model: Type[BaseModel],
        attr_name: str,
    ):
        if len(jmux_subtype_set) != 1:
            raise ForbiddenTypeHintsError(
                "StreamableValues must have exactly one underlying type, "
                f"got {jmux_subtype_set}."
            )

        if list in pydantic_main_type_set:
            NonNoneType = get_main_type(jmux_subtype_set)
            PydanticNonNoneType = get_main_type(pydantic_subtype_set)
            if issubclass(NonNoneType, JMux):
                NonNoneType.assert_conforms_to(PydanticNonNoneType)
                return
            if jmux_subtype_set != pydantic_subtype_set:
                raise ObjectMissmatchedError(
                    jmux_model=cls.__name__,
                    pydantic_model=pydantic_model.__name__,
                    attribute=attr_name,
                    message=(
                        "StreamableValues of type list with subtype "
                        f"{jmux_subtype_set} does not match pydantic model "
                        f"type: {pydantic_subtype_set}"
                    ),
                )
        elif str in pydantic_main_type_set:
            if jmux_subtype_set != pydantic_main_type_set:
                raise ObjectMissmatchedError(
                    jmux_model=cls.__name__,
                    pydantic_model=pydantic_model.__name__,
                    attribute=attr_name,
                    message=(
                        "StreamableValues of type string does not match pydantic "
                        f"model type: {pydantic_main_type_set}"
                    ),
                )
        else:
            raise ForbiddenTypeHintsError(
                message="StreamableValues must be initialized with a sequence type."
            )

    @classmethod
    def _assert_is_allowed_awaitable_value(
        cls,
        jmux_subtype_set: Set[Type],
        pydantic_subtype_set: Set[Type],
        pydantic_main_type_set: Set[Type],
        pydantic_model: Type[BaseModel],
        attr_name: str,
    ):
        if len(pydantic_subtype_set) > 0:
            raise ForbiddenTypeHintsError(
                message="Pydantic model cannot have subtype for AwaitableValue."
            )
        NonNoneType = get_main_type(jmux_subtype_set)
        PydanticNonNoneType = get_main_type(pydantic_main_type_set)
        if issubclass(NonNoneType, JMux):
            NonNoneType.assert_conforms_to(PydanticNonNoneType)
            return
        if not jmux_subtype_set == pydantic_main_type_set:
            raise ObjectMissmatchedError(
                jmux_model=cls.__name__,
                pydantic_model=pydantic_model.__name__,
                attribute=attr_name,
                message=(
                    f"AwaitableValue with type {jmux_subtype_set} does not match "
                    f"pydantic model type: {pydantic_main_type_set}"
                ),
            )

    async def feed_chunks(self, chunks: str) -> None:
        """
        Feeds a string of characters to the JMux parser.

        Args:
            chunks: The string of characters to feed.

        Raises:
            UnexpectedCharacterError: If an unexpected character is encountered.
            ObjectAlreadyClosedError: If the JMux object is already closed.
            UnexpectedStateError: If the parser is in an unexpected state.
            EmptyKeyError: If an empty key is encountered in a JSON object.
        """
        for ch in chunks:
            await self.feed_char(ch)

    async def feed_char(self, ch: str) -> None:
        """
        Feeds a character to the JMux parser.

        Args:
            ch: The character to feed.

        Raises:
            UnexpectedCharacterError: If an unexpected character is encountered.
            ObjectAlreadyClosedError: If the JMux object is already closed.
            UnexpectedStateError: If the parser is in an unexpected state.
            EmptyKeyError: If an empty key is encountered in a JSON object.
        """
        if len(ch) != 1:
            raise UnexpectedCharacterError(
                character=ch,
                pda_stack=self._pda.stack,
                pda_state=self._pda.state,
                message="Only single characters are allowed to be fed to JMux.",
            )
        match self._pda.top:
            # CONTEXT: Start
            case None:
                match self._pda.state:
                    case S.START:
                        if ch in JSON_WHITESPACE:
                            pass
                        elif ch in OBJECT_OPEN:
                            self._pda.push(M.ROOT)
                            self._pda.set_state(S.EXPECT_KEY)
                        else:
                            raise UnexpectedCharacterError(
                                ch,
                                self._pda.stack,
                                self._pda.state,
                                "JSON must start with '{' character.",
                            )
                    case S.END:
                        if ch in JSON_WHITESPACE:
                            pass
                        else:
                            raise ObjectAlreadyClosedError(
                                object_name=self.__class__.__name__,
                                message=(
                                    "Cannot feed more characters to closed JMux "
                                    f"object, got '{ch}'"
                                ),
                            )
                    case _:
                        raise UnexpectedStateError(
                            self._pda.stack,
                            self._pda.state,
                            message=(
                                "Only START and END states are allowed in the root "
                                "context."
                            ),
                        )

            # CONTEXT: Root
            case M.ROOT:
                match self._pda.state:
                    case S.EXPECT_KEY:
                        if ch in JSON_WHITESPACE:
                            pass
                        elif ch == '"':
                            self._pda.set_state(S.PARSING_KEY)
                            self._decoder.reset()
                        else:
                            raise UnexpectedCharacterError(
                                ch,
                                self._pda.stack,
                                self._pda.state,
                                "Char needs to be '\"' or JSON whitespaces",
                            )

                    case S.PARSING_KEY:
                        if self._decoder.is_terminating_quote(ch):
                            buffer = self._decoder.buffer
                            if not buffer:
                                raise EmptyKeyError(
                                    "Empty key is not allowed in JSON objects."
                                )
                            self._sink.set_current(buffer)
                            self._decoder.reset()
                            self._pda.set_state(S.EXPECT_COLON)
                        else:
                            self._decoder.push(ch)

                    case S.EXPECT_COLON:
                        if ch in JSON_WHITESPACE:
                            pass
                        elif ch in COLON:
                            self._pda.set_state(S.EXPECT_VALUE)
                        else:
                            raise UnexpectedCharacterError(
                                ch,
                                self._pda.stack,
                                self._pda.state,
                                "Char must be ':' or JSON whitespaces.",
                            )

                    case S.EXPECT_VALUE:
                        if ch in JSON_WHITESPACE:
                            pass
                        elif res := await self._handle_common__expect_value(ch):
                            if (
                                self._sink.current_sink_type
                                is SinkType.STREAMABLE_VALUES
                                and res is not S.PARSING_STRING
                            ):
                                raise UnexpectedCharacterError(
                                    ch,
                                    self._pda.stack,
                                    self._pda.state,
                                    "Expected '[' or '\"' for 'StreamableValues'",
                                )
                        elif ch in ARRAY_OPEN:
                            self._pda.set_state(S.EXPECT_VALUE)
                            self._pda.push(M.ARRAY)
                        else:
                            raise UnexpectedCharacterError(
                                ch,
                                self._pda.stack,
                                self._pda.state,
                                "Expected '[' or white space.",
                            )

                    case S.PARSING_STRING:
                        if self._decoder.is_terminating_quote(ch):
                            if self._sink.current_sink_type == SinkType.AWAITABLE_VALUE:
                                MainType = self._sink.current_underlying_main_generic
                                if issubclass(MainType, Enum):
                                    try:
                                        value = MainType(self._decoder.buffer)
                                        await self._sink.emit(value)
                                    except ValueError as e:
                                        raise ParsePrimitiveError(
                                            f"Invalid enum value: "
                                            f"{self._decoder.buffer}"
                                        ) from e
                                else:
                                    await self._sink.emit(self._decoder.buffer)
                            self._decoder.reset()
                            await self._sink.close()
                            self._pda.set_state(S.EXPECT_COMMA_OR_EOC)
                        else:
                            maybe_char = self._decoder.push(ch)
                            if (
                                maybe_char is not None
                                and self._sink.current_sink_type
                                is SinkType.STREAMABLE_VALUES
                            ):
                                await self._sink.emit(maybe_char)

                    case _ if self._pda.state in PARSING_PRIMITIVE_STATES:
                        if ch in COMMA | OBJECT_CLOSE | JSON_WHITESPACE:
                            await self._parse_primitive()
                            await self._sink.close()
                            self._decoder.reset()
                            if ch in JSON_WHITESPACE:
                                self._pda.set_state(S.EXPECT_COMMA_OR_EOC)
                            else:
                                self._pda.set_state(S.EXPECT_KEY)
                            if ch in OBJECT_CLOSE:
                                await self._finalize()
                        else:
                            self._assert_primitive_character_allowed_in_state(ch)
                            self._decoder.push(ch)

                    case S.EXPECT_COMMA_OR_EOC:
                        if ch in JSON_WHITESPACE:
                            pass
                        elif ch in COMMA:
                            self._pda.set_state(S.EXPECT_KEY)
                        elif ch in OBJECT_CLOSE:
                            await self._finalize()
                        else:
                            raise UnexpectedCharacterError(
                                ch,
                                self._pda.stack,
                                self._pda.state,
                                "Expected ',', '}' or white space.",
                            )

                    case _:
                        raise UnexpectedStateError(
                            self._pda.stack,
                            self._pda.state,
                            message="State not allowed in root context.",
                        )

            # CONTEXT: Array
            case M.ARRAY:
                if ch in ARRAY_OPEN:
                    raise UnexpectedCharacterError(
                        ch,
                        self._pda.stack,
                        self._pda.state,
                        "No support for 2-dimensional arrays.",
                    )

                match self._pda.state:
                    case S.EXPECT_VALUE:
                        if ch in JSON_WHITESPACE:
                            pass
                        elif await self._handle_common__expect_value(ch):
                            pass
                        elif ch in ARRAY_CLOSE:
                            await self._close_context(S.EXPECT_COMMA_OR_EOC)
                        else:
                            raise UnexpectedCharacterError(
                                ch,
                                self._pda.stack,
                                self._pda.state,
                                "Expected value, ']' or white space",
                            )

                    case S.PARSING_STRING:
                        if self._sink.current_sink_type is SinkType.AWAITABLE_VALUE:
                            raise UnexpectedCharacterError(
                                ch,
                                self._pda.stack,
                                self._pda.state,
                                (
                                    "Cannot parse string inside of an array with "
                                    "AwaitableValue sink type."
                                ),
                            )
                        if self._decoder.is_terminating_quote(ch):
                            MainType = self._sink.current_underlying_main_generic
                            if issubclass(MainType, Enum):
                                try:
                                    value = MainType(self._decoder.buffer)
                                    await self._sink.emit(value)
                                except ValueError as e:
                                    raise ParsePrimitiveError(
                                        f"Invalid enum value: {self._decoder.buffer}"
                                    ) from e
                            else:
                                await self._sink.emit(self._decoder.buffer)
                            self._decoder.reset()
                            self._pda.set_state(S.EXPECT_COMMA_OR_EOC)
                        else:
                            self._decoder.push(ch)

                    case _ if self._pda.state in PARSING_PRIMITIVE_STATES:
                        if ch in COMMA | ARRAY_CLOSE | JSON_WHITESPACE:
                            await self._parse_primitive()
                            self._decoder.reset()
                            if ch in COMMA:
                                self._pda.set_state(S.EXPECT_VALUE)
                            elif ch in ARRAY_CLOSE:
                                await self._close_context(S.EXPECT_COMMA_OR_EOC)
                        else:
                            self._assert_primitive_character_allowed_in_state(ch)
                            self._decoder.push(ch)

                    case S.EXPECT_COMMA_OR_EOC:
                        if ch in JSON_WHITESPACE:
                            pass
                        elif ch in COMMA:
                            self._pda.set_state(S.EXPECT_VALUE)
                        elif ch in ARRAY_CLOSE:
                            await self._close_context(S.EXPECT_COMMA_OR_EOC)
                        else:
                            raise UnexpectedCharacterError(
                                ch,
                                self._pda.stack,
                                self._pda.state,
                                "Expected ',', ']' or white space.",
                            )

                    case _:
                        raise UnexpectedStateError(
                            self._pda.stack,
                            self._pda.state,
                            message="State not allowed in array context.",
                        )

            # CONTEXT: Object
            case M.OBJECT:
                if self._pda.state is not S.PARSING_OBJECT:
                    raise UnexpectedCharacterError(
                        ch,
                        self._pda.stack,
                        self._pda.state,
                        "State in object context must be 'parsing_object'",
                    )
                if ch in OBJECT_OPEN:
                    if self._pda.top is M.OBJECT:
                        await self._sink.forward_char(ch)
                    self._pda.push(M.OBJECT)
                elif ch in OBJECT_CLOSE:
                    self._pda.pop()
                    if self._pda.top is M.OBJECT:
                        await self._sink.forward_char(ch)
                        return

                    if self._pda.top is M.ROOT:
                        await self._sink.close()
                    self._pda.set_state(S.EXPECT_COMMA_OR_EOC)
                    return
                else:
                    await self._sink.forward_char(ch)
                    return

    async def _parse_primitive(self) -> None:
        if self._pda.state is S.PARSING_NULL:
            if not self._decoder.buffer == JSON_NULL:
                raise ParsePrimitiveError(
                    f"Expected 'null', got '{self._decoder.buffer}'"
                )
            await self._sink.emit(None)
        elif self._pda.state is S.PARSING_BOOLEAN:
            bool_value = str_to_bool(self._decoder.buffer)
            await self._sink.emit(bool_value)
        else:
            try:
                buffer = self._decoder.buffer
                generic = self._sink.current_underlying_main_generic
                value = float(buffer) if issubclass(generic, float) else int(buffer)
            except ValueError as e:
                raise ParsePrimitiveError(f"Buffer: {buffer}; Error: {e}") from e
            await self._sink.emit(value)

    async def _handle_common__expect_value(self, ch: str) -> S | None:
        generic_set = self._sink.current_underlying_generics
        generic = self._sink.current_underlying_main_generic
        if ch in QUOTE:
            if not (str in generic_set or issubclass(generic, Enum)):
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    (
                        "Trying to parse 'string' but underlying generic is "
                        f"'{generic_set}'."
                    ),
                )
            self._pda.set_state(S.PARSING_STRING)
            self._decoder.reset()
            return S.PARSING_STRING
        if ch in NUMBER_OPEN:
            if not any(t in generic_set for t in (int, float)):
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    (
                        "Trying to parse 'number' but underlying generic is "
                        f"'{generic_set}'."
                    ),
                )
            self._decoder.push(ch)
            if generic is int:
                self._pda.set_state(S.PARSING_INTEGER)
                return S.PARSING_INTEGER
            else:
                self._pda.set_state(S.PARSING_FLOAT)
                return S.PARSING_FLOAT
        if ch in BOOLEAN_OPEN:
            if bool not in generic_set:
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    (
                        "Trying to parse 'boolean' but underlying generic is "
                        f"'{generic.__name__}'."
                    ),
                )
            self._pda.set_state(S.PARSING_BOOLEAN)
            self._decoder.push(ch)
            return S.PARSING_BOOLEAN
        if ch in NULL_OPEN:
            if NoneType not in generic_set:
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    (
                        "Trying to parse 'null' but underlying generic is "
                        f"'{generic.__name__}'."
                    ),
                )
            self._pda.set_state(S.PARSING_NULL)
            self._decoder.push(ch)
            return S.PARSING_NULL
        if ch in OBJECT_OPEN:
            if not issubclass(generic, JMux):
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    (
                        f"Trying to parse 'object' but underlying generic is "
                        f"'{generic.__name__}'."
                    ),
                )
            await self._sink.create_and_emit_nested()
            await self._sink.forward_char(ch)
            self._pda.set_state(S.PARSING_OBJECT)
            self._pda.push(M.OBJECT)
            return S.PARSING_OBJECT

    async def _close_context(self, new_state: S) -> None:
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
                raise NotAllObjectPropertiesSetError(
                    f"Unable to finalize. Property '{attr_name}' was not set before "
                    "closing the JMux instance."
                ) from e

        self._pda.pop()
        self._pda.set_state(S.END)

    def _assert_primitive_character_allowed_in_state(self, ch: str) -> None:
        if self._pda.state is S.PARSING_INTEGER:
            if ch not in INTERGER_ALLOWED:
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    "Trying to parse 'integer' but received unexpected character.",
                )
        elif self._pda.state is S.PARSING_FLOAT:
            if ch not in FLOAT_ALLOWED:
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    "Trying to parse 'float' but received unexpected character.",
                )
        elif self._pda.state is S.PARSING_BOOLEAN:
            if ch not in BOOLEAN_ALLOWED:
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    "Trying to parse 'boolean' but received unexpected character.",
                )
            if not any(
                bool_str.startswith(f"{self._decoder.buffer}{ch}")
                for bool_str in (JSON_TRUE, JSON_FALSE)
            ):
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    (
                        "Unexpected character added to buffer for 'boolean': "
                        f"'{self._decoder.buffer}{ch}'."
                    ),
                )
        elif self._pda.state is S.PARSING_NULL:
            if ch not in NULL_ALLOWED:
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    "Trying to parse 'null' but received unexpected character.",
                )
            if not JSON_NULL.startswith(f"{self._decoder.buffer}{ch}"):
                raise UnexpectedCharacterError(
                    ch,
                    self._pda.stack,
                    self._pda.state,
                    (
                        f"Unexpected character added to buffer for 'null': "
                        f"'{self._decoder.buffer}{ch}'."
                    ),
                )
        else:
            raise UnexpectedCharacterError(
                ch,
                self._pda.stack,
                self._pda.state,
                "An unexpected error happened.",
            )
