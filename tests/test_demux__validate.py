from enum import Enum

import pytest
from pydantic import BaseModel

from jmux.awaitable import AwaitableValue, StreamableValues
from jmux.demux import JMux
from jmux.error import ObjectMissmatchedError


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
