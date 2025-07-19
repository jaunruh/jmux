from types import NoneType
from typing import Set, Type

import pytest

from jmux.awaitable import (
    AwaitableValue,
    IAsyncSink,
    StreamableValues,
)
from jmux.demux import JMux


class NestedObject(JMux):
    key: AwaitableValue[str]


@pytest.mark.parametrize(
    "TargetType,expected_set",
    [
        (AwaitableValue[int], {int}),
        (AwaitableValue[float], {float}),
        (AwaitableValue[str], {str}),
        (AwaitableValue[bool], {bool}),
        (AwaitableValue[NestedObject], {NestedObject}),
        (AwaitableValue[int | None], {int, NoneType}),
        (AwaitableValue[float | None], {float, NoneType}),
        (AwaitableValue[str | None], {str, NoneType}),
        (AwaitableValue[bool | None], {bool, NoneType}),
        (AwaitableValue[NestedObject | None], {NestedObject, NoneType}),
        (StreamableValues[int], {int}),
        (StreamableValues[float], {float}),
        (StreamableValues[str], {str}),
        (StreamableValues[bool], {bool}),
        (StreamableValues[NestedObject], {NestedObject}),
    ],
)
def test_underlying_generic_mixin__get_underlying_generic__expected_set(
    TargetType: Type[IAsyncSink], expected_set: Set[Type]
):
    target = TargetType()
    underlying_types = target.get_underlying_generics()

    assert underlying_types == expected_set


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
        (StreamableValues[int | None], TypeError),
        (StreamableValues[float | None], TypeError),
        (StreamableValues[str | None], TypeError),
        (StreamableValues[bool | None], TypeError),
        (StreamableValues[NestedObject | None], TypeError),
    ],
)
def test_underlying_generic_mixin__get_underlying_generic__check_instantiation(
    TargetType: Type[IAsyncSink], MaybeExpectedError: Type[Exception] | None
):
    target = TargetType()
    if MaybeExpectedError:
        with pytest.raises(MaybeExpectedError):
            _ = target.get_underlying_generics()
    else:
        _ = target.get_underlying_generics()
