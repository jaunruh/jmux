from types import NoneType
from typing import Type

import pytest
from jmux.demux import JMux
from jmux.types import AwaitableValue, IAsyncSink, StreamableValues


class NestedObject(JMux):
    key: AwaitableValue[str]


@pytest.mark.parametrize(
    "TargetType,ExpectedType",
    [
        (AwaitableValue[int], int),
        (AwaitableValue[float], float),
        (AwaitableValue[str], str),
        (AwaitableValue[bool], bool),
        (AwaitableValue[NestedObject], NestedObject),
        (AwaitableValue[int | None], int | NoneType),
        (AwaitableValue[float | None], float | NoneType),
        (AwaitableValue[str | None], str | NoneType),
        (AwaitableValue[bool | None], bool | NoneType),
        (AwaitableValue[NestedObject | None], NestedObject | NoneType),
        (StreamableValues[int], int),
        (StreamableValues[float], float),
        (StreamableValues[str], str),
        (StreamableValues[bool], bool),
        (StreamableValues[NestedObject], NestedObject),
        (StreamableValues[int | None], int | NoneType),
        (StreamableValues[float | None], float | NoneType),
        (StreamableValues[str | None], str | NoneType),
        (StreamableValues[bool | None], bool | NoneType),
        (StreamableValues[NestedObject | None], NestedObject | NoneType),
    ],
)
def test_underlying_generic_mixin__get_underlying_generic__expected_set(
    TargetType: Type[IAsyncSink], ExpectedType: Type
):
    target = TargetType()
    underlying_types = target.get_underlying_generic()

    assert underlying_types == ExpectedType


@pytest.mark.parametrize(
    "TargetType,MaybeExpectedError",
    [
        (AwaitableValue[int], None),
        (AwaitableValue[str], None),
        (AwaitableValue[float], None),
        (AwaitableValue[bool], None),
        (AwaitableValue[NoneType], None),
        (AwaitableValue[NestedObject | None], None),
        (AwaitableValue[int | NoneType], None),
        (AwaitableValue[str | NoneType], None),
        (AwaitableValue[float | NoneType], None),
        (AwaitableValue[bool | NoneType], None),
        (AwaitableValue[bool | str | NoneType], TypeError),
        (AwaitableValue[bool | str], TypeError),
        (AwaitableValue[NestedObject | str], TypeError),
    ],
)
def test_underlying_generic_mixin__get_underlying_generic__check_instantiation(
    TargetType: Type[IAsyncSink], MaybeExpectedError: Type[Exception] | None
):
    target = TargetType()
    if MaybeExpectedError:
        with pytest.raises(MaybeExpectedError):
            _ = target.get_underlying_generic()
    else:
        _ = target.get_underlying_generic()
