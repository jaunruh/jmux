from enum import Enum

import pytest
from pydantic import BaseModel

from jmux.awaitable import AwaitableValue, StreamableValues
from jmux.demux import JMux
from jmux.error import (
    ForbiddenTypeHintsError,
    MissingAttributeError,
    ObjectMissmatchedError,
)


class SEnum(Enum):
    VALUE1 = "value1"
    VALUE2 = "value2"


class CorrectJMux_1(JMux):
    class NestedJMux(JMux):
        nested_key: AwaitableValue[str]

    key_str: AwaitableValue[str]
    key_int: AwaitableValue[int]
    key_float: AwaitableValue[float]
    key_bool: AwaitableValue[bool]
    key_none: AwaitableValue[None]
    key_enum: AwaitableValue[SEnum]
    key_nested: AwaitableValue[NestedJMux]

    key_stream: StreamableValues[str]

    arr_str: StreamableValues[str]
    arr_int: StreamableValues[int]
    arr_float: StreamableValues[float]
    arr_bool: StreamableValues[bool]
    arr_none: StreamableValues[None]
    arr_enum: StreamableValues[SEnum]
    arr_nested: StreamableValues[NestedJMux]


class CorrectPydantic_1(BaseModel):
    class NestedPydantic(BaseModel):
        nested_key: str

    key_str: str
    key_int: int
    key_float: float
    key_bool: bool
    key_none: None
    key_stream: str
    key_enum: SEnum
    key_nested: NestedPydantic

    arr_str: list[str]
    arr_int: list[int]
    arr_float: list[float]
    arr_bool: list[bool]
    arr_none: list[None]
    arr_enum: list[SEnum]
    arr_nested: list[NestedPydantic]


class CorrectJMux_2(JMux):
    key_str: AwaitableValue[str | None]
    key_int: AwaitableValue[int | None]
    key_float: AwaitableValue[float | None]
    key_bool: AwaitableValue[bool | None]


class CorrectPydantic_2(BaseModel):
    key_str: str | None
    key_int: int | None
    key_float: float | None
    key_bool: bool | None


class CorrectJMux_3(JMux):
    arr_str: StreamableValues[str]


class CorrectPydantic_3(BaseModel):
    arr_str: list[str] | None


class IncorrectJMux_1(JMux):
    key_str: AwaitableValue[str]


class IncorrectPydantic_1(BaseModel):
    key_str: str | None


class IncorrectJMux_2(JMux):
    key_str: AwaitableValue[str | None]


class IncorrectPydantic_2(BaseModel):
    key_str: str


class IncorrectJMux_3(JMux):
    class NestedJMux(JMux):
        nested_key: AwaitableValue[str | None]

    key_nested: AwaitableValue[NestedJMux]


class IncorrectPydantic_3(BaseModel):
    class NestedPydantic(BaseModel):
        nested_key: str

    key_nested: NestedPydantic


@pytest.mark.parametrize(
    "TargetJMux,TargetPydantic,MaybeExpectedError",
    [
        (CorrectJMux_1, CorrectPydantic_1, None),
        (CorrectJMux_2, CorrectPydantic_2, None),
        (CorrectJMux_3, CorrectPydantic_3, None),
        (IncorrectJMux_1, IncorrectPydantic_1, ObjectMissmatchedError),
        (IncorrectJMux_2, IncorrectPydantic_2, ObjectMissmatchedError),
        (IncorrectJMux_3, IncorrectPydantic_3, ObjectMissmatchedError),
    ],
)
@pytest.mark.anyio
async def test_json_demux__validate_pydantic(
    TargetJMux: type[JMux],
    TargetPydantic: type[BaseModel],
    MaybeExpectedError: type[Exception] | None,
):
    if MaybeExpectedError:
        with pytest.raises(MaybeExpectedError):
            TargetJMux.assert_conforms_to(TargetPydantic)
    else:
        TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__missing_attribute_error():
    class TargetJMux(JMux):
        required_field: AwaitableValue[str]

    class TargetPydantic(BaseModel):
        pass

    with pytest.raises(MissingAttributeError):
        TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__missing_attribute_error_with_optional_passes():
    class TargetJMux(JMux):
        optional_field: AwaitableValue[str | None]

    class TargetPydantic(BaseModel):
        pass

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__nested_mismatch():
    class NestedJMux(JMux):
        field: AwaitableValue[int]

    class TargetJMux(JMux):
        nested: AwaitableValue[NestedJMux]

    class NestedPydantic(BaseModel):
        field: str

    class TargetPydantic(BaseModel):
        nested: NestedPydantic

    with pytest.raises(ObjectMissmatchedError):
        TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__streamable_values_type_mismatch():
    class TargetJMux(JMux):
        arr: StreamableValues[int]

    class TargetPydantic(BaseModel):
        arr: list[str]

    with pytest.raises(ObjectMissmatchedError):
        TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__streamable_values_string_type():
    class TargetJMux(JMux):
        stream: StreamableValues[str]

    class TargetPydantic(BaseModel):
        stream: str

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__streamable_values_string_type_mismatch():
    class TargetJMux(JMux):
        stream: StreamableValues[str]

    class TargetPydantic(BaseModel):
        stream: int

    with pytest.raises(ObjectMissmatchedError):
        TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__enum_matching():
    class TargetEnum(Enum):
        A = "a"
        B = "b"

    class TargetJMux(JMux):
        field: AwaitableValue[TargetEnum]

    class TargetPydantic(BaseModel):
        field: TargetEnum

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__enum_optional():
    class TargetEnum(Enum):
        A = "a"

    class TargetJMux(JMux):
        field: AwaitableValue[TargetEnum | None]

    class TargetPydantic(BaseModel):
        field: TargetEnum | None

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__streamable_enum_list():
    class TargetEnum(Enum):
        A = "a"
        B = "b"

    class TargetJMux(JMux):
        arr: StreamableValues[TargetEnum]

    class TargetPydantic(BaseModel):
        arr: list[TargetEnum]

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__nested_streamable():
    class NestedJMux(JMux):
        val: AwaitableValue[str]

    class TargetJMux(JMux):
        arr: StreamableValues[NestedJMux]

    class NestedPydantic(BaseModel):
        val: str

    class TargetPydantic(BaseModel):
        arr: list[NestedPydantic]

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__pydantic_dict_type_forbidden():
    class TargetJMux(JMux):
        field: AwaitableValue[str]

    class TargetPydantic(BaseModel):
        field: dict[str, str]

    with pytest.raises(ForbiddenTypeHintsError):
        TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__pydantic_tuple_type_forbidden():
    class TargetJMux(JMux):
        field: AwaitableValue[str]

    class TargetPydantic(BaseModel):
        field: tuple[str, int]

    with pytest.raises(ForbiddenTypeHintsError):
        TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__pydantic_set_type_forbidden():
    class TargetJMux(JMux):
        field: AwaitableValue[str]

    class TargetPydantic(BaseModel):
        field: set[str]

    with pytest.raises(ObjectMissmatchedError):
        TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__multiple_fields_all_match():
    class TargetJMux(JMux):
        field1: AwaitableValue[str]
        field2: AwaitableValue[int]
        field3: AwaitableValue[bool]

    class TargetPydantic(BaseModel):
        field1: str
        field2: int
        field3: bool

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__multiple_fields_one_mismatch():
    class TargetJMux(JMux):
        field1: AwaitableValue[str]
        field2: AwaitableValue[int]
        field3: AwaitableValue[bool]

    class TargetPydantic(BaseModel):
        field1: str
        field2: str
        field3: bool

    with pytest.raises(ObjectMissmatchedError):
        TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__extra_pydantic_field_allowed():
    class TargetJMux(JMux):
        field1: AwaitableValue[str]

    class TargetPydantic(BaseModel):
        field1: str
        field2: int

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__deep_nested_objects():
    class Level3JMux(JMux):
        val: AwaitableValue[str]

    class Level2JMux(JMux):
        level3: AwaitableValue[Level3JMux]

    class Level1JMux(JMux):
        level2: AwaitableValue[Level2JMux]

    class TargetJMux(JMux):
        level1: AwaitableValue[Level1JMux]

    class Level3Pydantic(BaseModel):
        val: str

    class Level2Pydantic(BaseModel):
        level3: Level3Pydantic

    class Level1Pydantic(BaseModel):
        level2: Level2Pydantic

    class TargetPydantic(BaseModel):
        level1: Level1Pydantic

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__deep_nested_mismatch_at_bottom():
    class Level2JMux(JMux):
        val: AwaitableValue[int]

    class Level1JMux(JMux):
        level2: AwaitableValue[Level2JMux]

    class TargetJMux(JMux):
        level1: AwaitableValue[Level1JMux]

    class Level2Pydantic(BaseModel):
        val: str

    class Level1Pydantic(BaseModel):
        level2: Level2Pydantic

    class TargetPydantic(BaseModel):
        level1: Level1Pydantic

    with pytest.raises(ObjectMissmatchedError):
        TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__mixed_streamable_and_awaitable():
    class TargetJMux(JMux):
        single_val: AwaitableValue[str]
        list_val: StreamableValues[int]
        stream_str: StreamableValues[str]

    class TargetPydantic(BaseModel):
        single_val: str
        list_val: list[int]
        stream_str: str

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__optional_list_in_pydantic():
    class TargetJMux(JMux):
        arr: StreamableValues[str]

    class TargetPydantic(BaseModel):
        arr: list[str] | None

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__all_primitive_types():
    class TargetJMux(JMux):
        str_val: AwaitableValue[str]
        int_val: AwaitableValue[int]
        float_val: AwaitableValue[float]
        bool_val: AwaitableValue[bool]
        none_val: AwaitableValue[None]

    class TargetPydantic(BaseModel):
        str_val: str
        int_val: int
        float_val: float
        bool_val: bool
        none_val: None

    TargetJMux.assert_conforms_to(TargetPydantic)


def test_assert_conforms_to__all_optional_primitives():
    class TargetJMux(JMux):
        str_val: AwaitableValue[str | None]
        int_val: AwaitableValue[int | None]
        float_val: AwaitableValue[float | None]
        bool_val: AwaitableValue[bool | None]

    class TargetPydantic(BaseModel):
        str_val: str | None
        int_val: int | None
        float_val: float | None
        bool_val: bool | None

    TargetJMux.assert_conforms_to(TargetPydantic)
