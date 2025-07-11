from enum import Enum
from typing import Set


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


PRIMITIVE_STATES: Set[State] = {
    State.PARSING_INTEGER,
    State.PARSING_FLOAT,
    State.PARSING_BOOLEAN,
    State.PARSING_NULL,
}


class Mode(Enum):
    ROOT = "$"
    OBJECT = "object"
    ARRAY = "array"
