from types import NoneType
from typing import List, Optional, Set, Tuple, Type

import pytest

from jmux.awaitable import (
    AwaitableValue,
    StreamableValues,
    UnderlyingGenericMixin,
)
from jmux.demux import JMux
from jmux.helpers import deconstruct_type, extract_types_from_generic_alias


@pytest.mark.parametrize(
    "TargetType,expected_tuple",
    [
        (int, {int}),
        (Optional[int], {int, NoneType}),
        (int | None, {int, NoneType}),
        (int | str, {str, int}),
        (int | str | NoneType, {str, int, NoneType}),
        (JMux, {JMux}),
        (JMux | None, {JMux, NoneType}),
        (JMux | NoneType, {JMux, NoneType}),
    ],
)
def test_extract_types(
    TargetType: Type[UnderlyingGenericMixin], expected_tuple: Tuple[Type, Set[Type]]
):
    underlying_types = deconstruct_type(TargetType)

    assert underlying_types == expected_tuple


class NestedObject(JMux):
    key: AwaitableValue[str]


# fmt: off
@pytest.mark.parametrize(
    "TargetType,expected_tuple",
    [
        (int, ({int}, set())),
        (str, ({str}, set())),
        (Optional[int], ({int, NoneType}, set())),
        (int | None, ({int, NoneType}, set())),
        (List[int], ({list}, {int})),
        (List[int | None], ({list}, {int, NoneType})),
        (AwaitableValue[int], ({AwaitableValue}, {int})),
        (AwaitableValue[float], ({AwaitableValue}, {float})),
        (AwaitableValue[str], ({AwaitableValue}, {str})),
        (AwaitableValue[bool], ({AwaitableValue}, {bool})),
        (AwaitableValue[NestedObject], ({AwaitableValue}, {NestedObject})),
        (AwaitableValue[int | None], ({AwaitableValue}, {int, NoneType})),
        (AwaitableValue[float | None], ({AwaitableValue}, {float, NoneType})),
        (AwaitableValue[str | None], ({AwaitableValue}, {str, NoneType})),
        (AwaitableValue[bool | None], ({AwaitableValue}, {bool, NoneType})),
        (AwaitableValue[NestedObject | None], ({AwaitableValue}, {NestedObject, NoneType})),
        (StreamableValues[int], ({StreamableValues}, {int})),
        (StreamableValues[float], ({StreamableValues}, {float})),
        (StreamableValues[str], ({StreamableValues}, {str})),
        (StreamableValues[bool], ({StreamableValues}, {bool})),
        (StreamableValues[NestedObject], ({StreamableValues}, {NestedObject})),
    ],
)
# fmt: on
def test_extract_types_from_generic_alias(
    TargetType: Type[UnderlyingGenericMixin], expected_tuple: Tuple[Type, Set[Type]]
):
    underlying_types = extract_types_from_generic_alias(TargetType)

    assert underlying_types == expected_tuple
