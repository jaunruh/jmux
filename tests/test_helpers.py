from types import NoneType
from typing import List, Optional, Set, Tuple, Type, Union

import pytest

from jmux.awaitable import (
    AwaitableValue,
    StreamableValues,
    UnderlyingGenericMixin,
)
from jmux.demux import JMux
from jmux.error import ParsePrimitiveError
from jmux.helpers import (
    deconstruct_flat_type,
    extract_types_from_generic_alias,
    get_main_type,
    str_to_bool,
)


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


def test_str_to_bool__true():
    assert str_to_bool("true") is True


def test_str_to_bool__false():
    assert str_to_bool("false") is False


@pytest.mark.parametrize(
    "invalid_input",
    [
        "True",
        "False",
        "TRUE",
        "FALSE",
        "1",
        "0",
        "yes",
        "no",
        "",
        " ",
        "  true",
        "true  ",
        " true ",
        "tRue",
        "fAlse",
        "null",
        "None",
        "t",
        "f",
    ],
)
def test_str_to_bool__invalid_input_raises_parse_primitive_error(invalid_input: str):
    with pytest.raises(ParsePrimitiveError):
        str_to_bool(invalid_input)


def test_get_main_type__single_type():
    assert get_main_type({int}) == int
    assert get_main_type({str}) == str
    assert get_main_type({float}) == float
    assert get_main_type({bool}) == bool
    assert get_main_type({JMux}) == JMux


def test_get_main_type__type_with_none():
    assert get_main_type({int, NoneType}) == int
    assert get_main_type({str, NoneType}) == str
    assert get_main_type({float, NoneType}) == float
    assert get_main_type({bool, NoneType}) == bool
    assert get_main_type({JMux, NoneType}) == JMux


def test_get_main_type__empty_set_raises_type_error():
    with pytest.raises(TypeError):
        get_main_type(set())


def test_get_main_type__multiple_non_none_types_raises_type_error():
    with pytest.raises(TypeError):
        get_main_type({int, str})


def test_get_main_type__multiple_types_with_none_raises_type_error():
    with pytest.raises(TypeError):
        get_main_type({int, str, NoneType})


def test_get_main_type__only_none_type_raises_type_error():
    with pytest.raises(TypeError):
        get_main_type({NoneType})


def test_get_main_type__does_not_modify_input():
    input_set = {int, NoneType}
    original_copy = input_set.copy()
    get_main_type(input_set)
    assert input_set == original_copy


@pytest.mark.parametrize(
    "input_type",
    [
        NestedObject,
        AwaitableValue,
        StreamableValues,
    ],
)
def test_get_main_type__custom_types(input_type: Type):
    assert get_main_type({input_type}) == input_type
    assert get_main_type({input_type, NoneType}) == input_type


def test_deconstruct_flat_type__raises_on_list():
    with pytest.raises(TypeError):
        deconstruct_flat_type(List[int])


def test_deconstruct_flat_type__raises_on_generic_class():
    with pytest.raises(TypeError):
        deconstruct_flat_type(AwaitableValue[int])


def test_deconstruct_flat_type__none_type_directly():
    assert deconstruct_flat_type(None) == {NoneType}
    assert deconstruct_flat_type(NoneType) == {NoneType}


def test_extract_types_from_generic_alias__raises_on_dict():
    with pytest.raises(TypeError):
        extract_types_from_generic_alias(dict[str, int])


def test_extract_types_from_generic_alias__raises_on_tuple():
    with pytest.raises(TypeError):
        extract_types_from_generic_alias(tuple[int, str])


def test_extract_types_from_generic_alias__raises_on_multi_type_union_in_generic():
    with pytest.raises(TypeError):
        extract_types_from_generic_alias(AwaitableValue[int | str])


def test_extract_types_from_generic_alias__raises_on_union_without_none_in_generic():
    with pytest.raises(TypeError):
        extract_types_from_generic_alias(AwaitableValue[int | float])
