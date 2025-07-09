from types import NoneType
from typing import List, Type

import pytest
from jmux.demux import JMux, Mode, State
from jmux.error import (
    EmptyKeyError,
    MissingAttributeError,
    ObjectAlreadyClosedError,
    ParsePrimitiveError,
    UnexpectedCharacterError,
)
from jmux.types import AwaitableValue, StreamableValues


# fmt: off
@pytest.mark.parametrize(
    "stream,expected_stack,expected_state",
    [
        ("", [], "start"),
        ("{", ["$"], "expect_key"),
        ("{ ", ["$"], "expect_key"),
        ('{"', ["$"], "parsing_key"),
        ('{"key_', ["$"], "parsing_key"),
        ('{"key_str', ["$"], "parsing_key"),
        ('{"key_str"', ["$"], "expect_colon"),
        ('{"key_str":', ["$"], "expect_value"),
        ('{"key_str": ', ["$"], "expect_value"),
        ('{"key_str": \t\n', ["$"], "expect_value"),
        ('{"key_str": "', ["$"], "parsing_string"),
        ('{"key_str": "val', ["$"], "parsing_string"),
        ('{"key_str": "val"', ["$"], "expect_comma_or_eoc"),
        ('{"key_str": "val" \t\n', ["$"], "expect_comma_or_eoc"),
        ('{"key_str": "val",', ["$"], "expect_key"),
        ('{"key_str": "val","key_int', ["$"], "parsing_key"),
        ('{"key_str": "val","key_int"', ["$"], "expect_colon"),
        ('{"key_str": "val","key_int":', ["$"], "expect_value"),
        ('{"key_str": "val","key_int": \t\n', ["$"], "expect_value"),
        ('{"key_str": "val","key_int":4', ["$"], "parsing_integer"),
        ('{"key_str": "val","key_int":42', ["$"], "parsing_integer"),
        ('{"key_str": "val","key_int":42,', ["$"], "expect_key"),
        ('{"key_str": "val","key_int":42,"', ["$"], "parsing_key"),
        ('{"key_str": "val","key_int":42,"key_float"', ["$"], "expect_colon"),
        ('{"key_str": "val","key_int":42,"key_float":', ["$"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":', ["$"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14', ["$"], "parsing_float"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,', ["$"], "expect_key"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":', ["$"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":t', ["$"], "parsing_boolean"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true', ["$"], "parsing_boolean"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":n', ["$"], "parsing_null"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,', ["$"], "expect_key"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,', ["$"], "expect_key"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream', ["$"], "parsing_key"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream', ["$"], "parsing_string"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":', ["$"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{', ["$", "object"], "parsing_object"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"', ["$", "object"], "parsing_object"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str"', ["$", "object"], "parsing_object"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"', ["$", "object"], "parsing_object"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"}', ["$"], "expect_comma_or_eoc"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},', ["$"], "expect_key"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":', ["$"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":[', ["$", "array"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["', ["$", "array"], "parsing_string"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1"', ["$", "array"], "expect_comma_or_eoc"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1" \t\n', ["$", "array"], "expect_comma_or_eoc"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1",', ["$", "array"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1", \t\n', ["$", "array"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2",', ["$", "array"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3', ["$", "array"], "parsing_string"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"', ["$", "array"], "expect_comma_or_eoc"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"]', ["$"], "expect_comma_or_eoc"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],', ["$"], "expect_key"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[', ["$", "array"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42', ["$", "array"], "parsing_integer"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,', ["$", "array"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3', ["$", "array"], "parsing_float"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14', ["$", "array"], "parsing_float"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,', ["$", "array"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4]', ["$"], "expect_comma_or_eoc"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true', ["$", "array"], "parsing_boolean"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false', ["$", "array"], "parsing_boolean"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true]', ["$"], "expect_comma_or_eoc"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,nul', ["$", "array"], "parsing_null"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null]', ["$"], "expect_comma_or_eoc"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_nested":[{', ["$", "array", "object"], "parsing_object"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_nested":[{"key_s', ["$", "array", "object"], "parsing_object"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_nested":[{"key_str":"nested1"}', ["$", "array"], "expect_comma_or_eoc"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_nested":[{"key_str":"nested1"},', ["$", "array"], "expect_value"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_nested":[{"key_str":"nested1"},{"key_str":"nes', ["$", "array", "object"], "parsing_object"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}', ["$", "array"], "expect_comma_or_eoc"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}]', ["$"], "expect_comma_or_eoc"),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}]}', [], "end"),
    ],
)
# fmt: on
@pytest.mark.anyio
async def test_json_demux__parse_correct_stream__assert_state(
    stream: str, expected_stack: List[Mode], expected_state: State
):
    class SObject(JMux):
        class SNested(JMux):
            key_str: AwaitableValue[str]

        key_str: AwaitableValue[str]
        key_int: AwaitableValue[int]
        key_float: AwaitableValue[float]
        key_bool: AwaitableValue[bool]
        key_none: AwaitableValue[NoneType]
        key_stream: StreamableValues[str]
        key_nested: AwaitableValue[SNested]

        arr_str: StreamableValues[str]
        arr_int: StreamableValues[int]
        arr_float: StreamableValues[float]
        arr_bool: StreamableValues[bool]
        arr_none: StreamableValues[NoneType]
        arr_nested: StreamableValues[SNested]

    s_object = SObject()

    for ch in stream:
        await s_object.feed_char(ch)

    assert s_object._pda.state == expected_state
    assert s_object._pda._stack == expected_stack


# fmt: off
@pytest.mark.parametrize(
    "stream,MaybeExpectedError",
    [
        ("b", UnexpectedCharacterError),
        ("{", None),
        ("{p", UnexpectedCharacterError),
        ('{"', None),
        ('{""', EmptyKeyError),
        ('{"no_actual_key"', MissingAttributeError),
        ('{"key_str"', None),
        ('{"key_str": ""', None),
        ('{"key_str": "val","key_int":4p', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":4t', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":420', None),
        ('{"key_str": "val","key_int":-420', None),
        ('{"key_str": "val","key_int":-4.20', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":1e+', None),
        ('{"key_str": "val","key_int":42,"key_float":0', None),
        ('{"key_str": "val","key_int":42,"key_float":p', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":1e+,', ParsePrimitiveError),
        ('{"key_str": "val","key_int":42,"key_float":-3.14e10,', None),
        ('{"key_str": "val","key_int":42,"key_float":-2.5E3,', None),
        ('{"key_str": "val","key_int":42,"key_float":1E+10,', None),
        ('{"key_str": "val","key_int":42,"key_float":NaN', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":Infinity', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":-', None),
        ('{"key_str": "val","key_int":42,"key_float":+', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":-1', None),
        ('{"key_str": "val","key_int":42,"key_float":--1', None),
        ('{"key_str": "val","key_int":42,"key_float":--1,', ParsePrimitiveError),
        ('{"key_str": "val","key_int":42,"key_float":.', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":1.', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":t', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":T', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":trub', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":tf', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":trueee', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":f', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":F', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":ft', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":falsb', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":n', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":nope', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":nulll', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":p', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":n', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":4', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{p', UnexpectedCharacterError), # Means all recursive calls throw errors as expected
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":{', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":p', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":[[', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":[]', None), # Allow empty arrays
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":[nu', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1",}', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":4,', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[4.', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42,', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42,[', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[-42,', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42,+43]', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42,-43]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":3', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":{', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":"', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3k', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[0', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14,314]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3,1,4]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14,31.4]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":"', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":t', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":r', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true,false,true]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":n', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":f', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_nested":[]', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_nested":[3', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_nested":[p', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_nested":[{p', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_nested":[{"key_str":3', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_nested":[{"key_str":', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}]}', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}]}}', ObjectAlreadyClosedError),
    ],
)
# fmt: on
@pytest.mark.anyio
async def test_json_demux__parse_incorrect_stream__assert_error(
    stream: str, MaybeExpectedError: Type[Exception] | None
):
    class SObject(JMux):
        class SNested(JMux):
            key_str: AwaitableValue[str]

        key_str: AwaitableValue[str]
        key_int: AwaitableValue[int]
        key_float: AwaitableValue[float]
        key_bool: AwaitableValue[bool]
        key_none: AwaitableValue[NoneType]
        key_stream: StreamableValues[str]
        key_nested: AwaitableValue[SNested]

        arr_str: StreamableValues[str]
        arr_int: StreamableValues[int]
        arr_float: StreamableValues[float]
        arr_bool: StreamableValues[bool]
        arr_none: StreamableValues[NoneType]
        arr_nested: StreamableValues[SNested]

    s_object = SObject()

    if MaybeExpectedError:
        with pytest.raises(MaybeExpectedError):
            for ch in stream:
                await s_object.feed_char(ch)
    else:
        for ch in stream:
            await s_object.feed_char(ch)



# fmt: off
@pytest.mark.parametrize(
    "stream,MaybeExpectedError",
    [
        ("b", UnexpectedCharacterError),
        ("{", None),
        ("{p", UnexpectedCharacterError),
        ('{"', None),
        ('{""', EmptyKeyError),
        ('{"no_actual_key"', MissingAttributeError),
        ('{"key_str"', None),
        ('{"key_str": ""', None),
        ('{"key_str": n', None),
        ('{"key_str": t', UnexpectedCharacterError),
        ('{"key_str": null', None),
        ('{"key_str": "val","key_int":4p', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":n', None),
        ('{"key_str": "val","key_int":r', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":null', None),
        ('{"key_str": "val","key_int":null,', None),
        ('{"key_str": "val","key_int":420', None),
        ('{"key_str": "val","key_int":-420', None),
        ('{"key_str": "val","key_int":42,"key_float":0', None),
        ('{"key_str": "val","key_int":42,"key_float":n', None),
        ('{"key_str": "val","key_int":42,"key_float":l', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":null', None),
        ('{"key_str": "val","key_int":42,"key_float":null,', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":t', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":r', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":n', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":null', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":null,', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_nested":{', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_nested":n', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_nested":k', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_nested":null', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_nested":null,', None),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_nested":{p', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_nested":{n', UnexpectedCharacterError),
        ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_nested":{"key_str":"nested"},', None),
    ],
)
# fmt: on
@pytest.mark.anyio
async def test_json_demux__parse_incorrect_stream_with_optionals__assert_error(
    stream: str, MaybeExpectedError: Type[Exception] | None
):
    class SObject(JMux):
        class SNested(JMux):
            key_str: AwaitableValue[str]

        key_str: AwaitableValue[str | NoneType]
        key_int: AwaitableValue[int | NoneType]
        key_float: AwaitableValue[float | NoneType]
        key_bool: AwaitableValue[bool | NoneType]
        key_nested: AwaitableValue[SNested | NoneType]

    s_object = SObject()

    if MaybeExpectedError:
        with pytest.raises(MaybeExpectedError):
            for ch in stream:
                await s_object.feed_char(ch)
    else:
        for ch in stream:
            await s_object.feed_char(ch)
