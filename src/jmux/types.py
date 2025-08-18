from enum import Enum
from types import NoneType, UnionType
from typing import List, Set, Union


class State(Enum):
    START = "start"
    END = "end"
    ERROR = "error"
    # expect
    EXPECT_KEY = "expect_key"
    EXPECT_COLON = "expect_colon"
    EXPECT_VALUE = "expect_value"
    EXPECT_COMMA_OR_EOC = "expect_comma_or_eoc"
    # parsing
    PARSING_KEY = "parsing_key"
    PARSING_STRING = "parsing_string"
    PARSING_INTEGER = "parsing_integer"
    PARSING_FLOAT = "parsing_float"
    PARSING_BOOLEAN = "parsing_boolean"
    PARSING_NULL = "parsing_null"
    PARSING_OBJECT = "parsing_object"


PARSING_PRIMITIVE_STATES: Set[State] = {
    State.PARSING_INTEGER,
    State.PARSING_FLOAT,
    State.PARSING_BOOLEAN,
    State.PARSING_NULL,
}


class Mode(Enum):
    ROOT = "$"
    OBJECT = "object"
    ARRAY = "array"


OBJECT_OPEN = set("{")
OBJECT_CLOSE = set("}")
COLON = set(":")
ARRAY_OPEN = set("[")
ARRAY_CLOSE = set("]")
COMMA = set(",")
QUOTE = set('"')

NUMBER_OPEN = set("0123456789-")
BOOLEAN_OPEN = set("tf")
NULL_OPEN = set("n")

INTERGER_ALLOWED = set("0123456789")
FLOAT_ALLOWED = set("0123456789-+eE.")
BOOLEAN_ALLOWED = set("truefals")
NULL_ALLOWED = set("nul")

JSON_FALSE = "false"
JSON_TRUE = "true"
JSON_NULL = "null"
JSON_WHITESPACE = set(" \t\n\r")

TYPES_LIKE_UNION = {UnionType, Union}
TYPES_LIKE_NONE = {NoneType, None}
TYPES_LIKE_LIST = {List, list}
