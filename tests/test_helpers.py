from types import NoneType
from typing import List, Optional, Set, Tuple, Type, Union

import pytest

from jmux.awaitable import (
    AwaitableValue,
    StreamableValues,
    UnderlyingGenericMixin,
)
from jmux.demux import JMux
from jmux.helpers import deconstruct_flat_type, extract_types_from_generic_alias


@pytest.mark.parametrize(
    "TargetType,expected_tuple",
    [
        (int, {int}),
        (Union[int], {int}),
        #
        (Optional[int], {int, NoneType}),
        (int | None, {int, NoneType}),
        #
        (Union[int, None], {int, NoneType}),
        (int | NoneType, {int, NoneType}),
        (Union[int, NoneType], {int, NoneType}),
        #
        (int | str, {str, int}),
        (Union[int, str], {str, int}),
        #
        (int | str | NoneType, {str, int, NoneType}),
        (Union[int, str, NoneType], {str, int, NoneType}),
        #
        (JMux, {JMux}),
        (Union[JMux], {JMux}),
        #
        (JMux | None, {JMux, NoneType}),
        (Union[JMux, None], {JMux, NoneType}),
        (Union[JMux, NoneType], {JMux, NoneType}),
        #
        (JMux | NoneType, {JMux, NoneType}),
        (Union[JMux, NoneType], {JMux, NoneType}),
    ],
)
def test_deconstruct_flat_types(
    TargetType: Type[UnderlyingGenericMixin], expected_tuple: Tuple[Type, Set[Type]]
):
    underlying_types = deconstruct_flat_type(TargetType)

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
        (list[int], ({list}, {int})),
        (List[int | None], ({list}, {int, NoneType})),
        (list[int | None], ({list}, {int, NoneType})),
        (List[int] | None, ({list, NoneType}, {int})),
        (list[int] | None, ({list, NoneType}, {int})),
        (Optional[List[int]], ({list, NoneType}, {int})),
        (Optional[list[int]], ({list, NoneType}, {int})),
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
