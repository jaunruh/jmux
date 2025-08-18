from enum import Enum
from types import NoneType
from typing import List, Type

import pytest

from jmux.awaitable import AwaitableValue, StreamableValues
from jmux.demux import JMux
from jmux.error import (
    EmptyKeyError,
    MissingAttributeError,
    ObjectAlreadyClosedError,
    ParsePrimitiveError,
    UnexpectedCharacterError,
)
from jmux.types import Mode, State

# fmt: off
parse_correct_stream__params = [
    ("", [], State.START),
    ("{", [Mode.ROOT], State.EXPECT_KEY),
    ("{ ", [Mode.ROOT], State.EXPECT_KEY),
    ('{"', [Mode.ROOT], State.PARSING_KEY),
    ('{"key_', [Mode.ROOT], State.PARSING_KEY),
    ('{"key_str', [Mode.ROOT], State.PARSING_KEY),
    ('{"key_str"', [Mode.ROOT], State.EXPECT_COLON),
    ('{"key_str":', [Mode.ROOT], State.EXPECT_VALUE),
    ('{"key_str": ', [Mode.ROOT], State.EXPECT_VALUE),
    ('{"key_str": \t\n', [Mode.ROOT], State.EXPECT_VALUE),
    ('{"key_str": "', [Mode.ROOT], State.PARSING_STRING),
    ('{"key_str": "val', [Mode.ROOT], State.PARSING_STRING),
    ('{"key_str": "val"', [Mode.ROOT], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val" \t\n', [Mode.ROOT], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val",', [Mode.ROOT], State.EXPECT_KEY),
    ('{"key_str": "val","key_int', [Mode.ROOT], State.PARSING_KEY),
    ('{"key_str": "val","key_int"', [Mode.ROOT], State.EXPECT_COLON),
    ('{"key_str": "val","key_int":', [Mode.ROOT], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int": \t\n', [Mode.ROOT], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":4', [Mode.ROOT], State.PARSING_INTEGER),
    ('{"key_str": "val","key_int":42', [Mode.ROOT], State.PARSING_INTEGER),
    ('{"key_str": "val","key_int":42,', [Mode.ROOT], State.EXPECT_KEY),
    ('{"key_str": "val","key_int":42,"', [Mode.ROOT], State.PARSING_KEY),
    ('{"key_str": "val","key_int":42,"key_float"', [Mode.ROOT], State.EXPECT_COLON),
    ('{"key_str": "val","key_int":42,"key_float":', [Mode.ROOT], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":', [Mode.ROOT], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14', [Mode.ROOT], State.PARSING_FLOAT),
    ('{"key_str": "val","key_int":42,"key_float":3.14,', [Mode.ROOT], State.EXPECT_KEY),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":', [Mode.ROOT], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":t', [Mode.ROOT], State.PARSING_BOOLEAN),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true', [Mode.ROOT], State.PARSING_BOOLEAN),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":n', [Mode.ROOT], State.PARSING_NULL),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,', [Mode.ROOT], State.EXPECT_KEY),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,', [Mode.ROOT], State.EXPECT_KEY),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream', [Mode.ROOT], State.PARSING_KEY),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream', [Mode.ROOT], State.PARSING_STRING),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum', [Mode.ROOT], State.PARSING_KEY),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"val', [Mode.ROOT], State.PARSING_STRING),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1"', [Mode.ROOT], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":', [Mode.ROOT], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{', [Mode.ROOT, Mode.OBJECT], State.PARSING_OBJECT),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"', [Mode.ROOT, Mode.OBJECT], State.PARSING_OBJECT),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str"', [Mode.ROOT, Mode.OBJECT], State.PARSING_OBJECT),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"', [Mode.ROOT, Mode.OBJECT], State.PARSING_OBJECT),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"}', [Mode.ROOT], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},', [Mode.ROOT], State.EXPECT_KEY),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":', [Mode.ROOT], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":[', [Mode.ROOT, Mode.ARRAY], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["', [Mode.ROOT, Mode.ARRAY], State.PARSING_STRING),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"', [Mode.ROOT, Mode.ARRAY], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1" \t\n', [Mode.ROOT, Mode.ARRAY], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1",', [Mode.ROOT, Mode.ARRAY], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1", \t\n', [Mode.ROOT, Mode.ARRAY], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2",', [Mode.ROOT, Mode.ARRAY], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3', [Mode.ROOT, Mode.ARRAY], State.PARSING_STRING),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"', [Mode.ROOT, Mode.ARRAY], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"]', [Mode.ROOT], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],', [Mode.ROOT], State.EXPECT_KEY),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[', [Mode.ROOT, Mode.ARRAY], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42', [Mode.ROOT, Mode.ARRAY], State.PARSING_INTEGER),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,', [Mode.ROOT, Mode.ARRAY], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3', [Mode.ROOT, Mode.ARRAY], State.PARSING_FLOAT),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14', [Mode.ROOT, Mode.ARRAY], State.PARSING_FLOAT),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,', [Mode.ROOT, Mode.ARRAY], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4]', [Mode.ROOT], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true', [Mode.ROOT, Mode.ARRAY], State.PARSING_BOOLEAN),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false', [Mode.ROOT, Mode.ARRAY], State.PARSING_BOOLEAN),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true]', [Mode.ROOT], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,nul', [Mode.ROOT, Mode.ARRAY], State.PARSING_NULL),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null]', [Mode.ROOT], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":[', [Mode.ROOT, Mode.ARRAY], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["val', [Mode.ROOT, Mode.ARRAY], State.PARSING_STRING),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["value1"', [Mode.ROOT, Mode.ARRAY], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["value1","value2"', [Mode.ROOT, Mode.ARRAY], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["value1","value2"]', [Mode.ROOT], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["value1","value2"],"arr_nested":[{', [Mode.ROOT, Mode.ARRAY, Mode.OBJECT], State.PARSING_OBJECT),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["value1","value2"],"arr_nested":[{"key_s', [Mode.ROOT, Mode.ARRAY, Mode.OBJECT], State.PARSING_OBJECT),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":"nested1"}', [Mode.ROOT, Mode.ARRAY], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":"nested1"},', [Mode.ROOT, Mode.ARRAY], State.EXPECT_VALUE),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":"nested1"},{"key_str":"nes', [Mode.ROOT, Mode.ARRAY, Mode.OBJECT], State.PARSING_OBJECT),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}', [Mode.ROOT, Mode.ARRAY], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}]', [Mode.ROOT], State.EXPECT_COMMA_OR_EOC),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,"key_none":null,"key_stream":"stream","key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1","val2","val3"],"arr_int":[42,43],"arr_float":[3.14,31.4],"arr_bool":[true,false,true],"arr_none":[null,null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}]}', [], State.END),
]
# fmt: on


@pytest.mark.parametrize(
    "stream,expected_stack,expected_state",
    parse_correct_stream__params,
)
@pytest.mark.anyio
async def test_json_demux__parse_correct_stream__assert_state(
    stream: str, expected_stack: List[Mode], expected_state: State
):
    class SObject(JMux):
        class SNested(JMux):
            key_str: AwaitableValue[str]

        class SEnum(Enum):
            VALUE1 = "value1"
            VALUE2 = "value2"

        key_str: AwaitableValue[str]
        key_int: AwaitableValue[int]
        key_float: AwaitableValue[float]
        key_bool: AwaitableValue[bool]
        key_none: AwaitableValue[NoneType]
        key_stream: StreamableValues[str]
        key_enum: AwaitableValue[SEnum]
        key_nested: AwaitableValue[SNested]

        arr_str: StreamableValues[str]
        arr_int: StreamableValues[int]
        arr_float: StreamableValues[float]
        arr_bool: StreamableValues[bool]
        arr_none: StreamableValues[NoneType]
        arr_enum: StreamableValues[SEnum]
        arr_nested: StreamableValues[SNested]

    s_object = SObject()

    for ch in stream:
        await s_object.feed_char(ch)

    assert s_object._pda.state == expected_state
    assert s_object._pda._stack == expected_stack


# fmt: off
parse_incorrect_stream__params = [
    ("b", UnexpectedCharacterError),
    ("\n", None),
    (" ", None),
    ("\t", None),
    ("{", None),
    ("{p", UnexpectedCharacterError),
    ('{"', None),
    ('{""', EmptyKeyError),
    ('{"no_actual_key"', MissingAttributeError),
    ('{"key_str"', None),
    ('{"key_str": ""', None),
    ('{"key_str": "" ', None),
    ('{"key_str": "val","key_int":4p', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":4t', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":420', None),
    ('{"key_str": "val","key_int":420 ', None),
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
    ('{"key_str": "val","key_int":42,"key_float":- ', ParsePrimitiveError),
    ('{"key_str": "val","key_int":42,"key_float":+', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":-1', None),
    ('{"key_str": "val","key_int":42,"key_float":-1 ', None),
    ('{"key_str": "val","key_int":42,"key_float":--1', None),
    ('{"key_str": "val","key_int":42,"key_float":--1,', ParsePrimitiveError),
    ('{"key_str": "val","key_int":42,"key_float":.', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":1.', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":t', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":t ', ParsePrimitiveError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":T', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":trub', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":tf', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":trueee', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true ', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":true,', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":f', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":F', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":ft', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":falsb', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":n', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":n ', ParsePrimitiveError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":nope', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":nulll', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null ', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":,', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"val', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"foo', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1"', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"foobar"', ParsePrimitiveError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":p', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":n', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":4', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{p', UnexpectedCharacterError), # Means all recursive calls throw errors as expected
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"} ', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":{', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":p', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":[[', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":[]', None), # Allow empty arrays
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":[nu', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1",}', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":4,', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[4.', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42,', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42,[', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[-42,', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42,+43]', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42,-43]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":3', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":{', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":"', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3k', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[0', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14,314]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3,1,4]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14,31.4]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":"', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":t', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":r', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true,false,true]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":n', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":f', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum"', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":[', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["val', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["foo', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1"', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["foobar"', ParsePrimitiveError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"],"arr_nested":[]', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"],"arr_nested":[3', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"],"arr_nested":[p', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"],"arr_nested":[{p', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":3', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}]}', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}]}\n', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}]} ', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}]}\t', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_none":null,"key_enum":"value1","key_nested":{"key_str":"nested"},"arr_str":["val1"],"arr_int":[42],"arr_float":[3.14],"arr_bool":[true],"arr_none":[null],"arr_enum":["value1","value2"],"arr_nested":[{"key_str":"nested1"},{"key_str":"nested2"}]}}', ObjectAlreadyClosedError),
]
# fmt: on


@pytest.mark.parametrize(
    "stream,MaybeExpectedError",
    parse_incorrect_stream__params,
)
@pytest.mark.anyio
async def test_json_demux__parse_stream__assert_error(
    stream: str, MaybeExpectedError: Type[Exception] | None
):
    class SObject(JMux):
        class SNested(JMux):
            key_str: AwaitableValue[str]

        class SEnum(Enum):
            VALUE1 = "value1"
            VALUE2 = "value2"

        key_str: AwaitableValue[str]
        key_int: AwaitableValue[int]
        key_float: AwaitableValue[float]
        key_bool: AwaitableValue[bool]
        key_none: AwaitableValue[NoneType]
        key_stream: StreamableValues[str]
        key_enum: AwaitableValue[SEnum]
        key_nested: AwaitableValue[SNested]

        arr_str: StreamableValues[str]
        arr_int: StreamableValues[int]
        arr_float: StreamableValues[float]
        arr_bool: StreamableValues[bool]
        arr_none: StreamableValues[NoneType]
        arr_enum: StreamableValues[SEnum]
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
parse_incorrect_stream_with_optionals__params = [
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
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":t', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":"', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":n', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":null,', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":"value1"', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":"value1","key_nested":{', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":"value1","key_nested":n', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":"value1","key_nested":k', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":"value1","key_nested":null', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":"value1","key_nested":null ', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":"value1","key_nested":null,', None),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":"value1","key_nested":{p', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":"value1","key_nested":{n', UnexpectedCharacterError),
    ('{"key_str": "val","key_int":42,"key_float":3.14,"key_bool":false,"key_enum":"value1","key_nested":{"key_str":"nested"},', None),
]
# fmt: on


@pytest.mark.parametrize(
    "stream,MaybeExpectedError",
    parse_incorrect_stream_with_optionals__params,
)
@pytest.mark.anyio
async def test_json_demux__parse_stream_with_optionals__assert_error(
    stream: str, MaybeExpectedError: Type[Exception] | None
):
    class SObject(JMux):
        class SNested(JMux):
            key_str: AwaitableValue[str]

        class SEnum(Enum):
            VALUE1 = "value1"
            VALUE2 = "value2"

        key_str: AwaitableValue[str | NoneType]
        key_int: AwaitableValue[int | NoneType]
        key_float: AwaitableValue[float | NoneType]
        key_bool: AwaitableValue[bool | NoneType]
        key_enum: AwaitableValue[SEnum | NoneType]
        key_nested: AwaitableValue[SNested | NoneType]

    s_object = SObject()

    if MaybeExpectedError:
        with pytest.raises(MaybeExpectedError):
            for ch in stream:
                await s_object.feed_char(ch)
    else:
        for ch in stream:
            await s_object.feed_char(ch)


# fmt: off
parse_correct_stream__double_nested__params = [
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"', None),
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"}', None),
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"}}', None),
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"}}}', None),
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"}, ', None),
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"}, "key_str":', None), # Simplified version of the trigger encountered in main repo
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"}, "key_str": t', UnexpectedCharacterError),
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"}, "key_str": "val', None),
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"}, "key_str": "val"}', None),
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"}, "key_str": "val"}}', None),
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"}, "key_str": null}}', None),
    ('{"key_first_nested": {"key_second_nested": {"key_str": "val"}, "key_str": null\n}}', None),
    ('{"key_first_nested": null}', None),
    ('{"key_first_nested": null\n}', None),
]
# fmt: on
@pytest.mark.parametrize(
    "stream,MaybeExpectedError",
    parse_correct_stream__double_nested__params,
)
@pytest.mark.anyio
async def test_json_demux__parse_stream__double_nested(
    stream: str, MaybeExpectedError: Type[Exception] | None
):
    class SObject(JMux):
        class SFirstNested(JMux):
            class SSecondNested(JMux):
                key_str: AwaitableValue[str]

            key_second_nested: AwaitableValue[SSecondNested | NoneType]
            key_str: AwaitableValue[str | NoneType]

        key_first_nested: AwaitableValue[SFirstNested | NoneType]

    s_object = SObject()

    if MaybeExpectedError:
        with pytest.raises(MaybeExpectedError):
            for ch in stream:
                await s_object.feed_char(ch)
    else:
        for ch in stream:
            await s_object.feed_char(ch)
