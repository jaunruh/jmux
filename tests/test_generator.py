from enum import Enum
from textwrap import dedent
from typing import Annotated

import pytest

from jmux.base import StreamableBaseModel, Streamed
from jmux.generator import generate_jmux_code, get_jmux_type


def expect_multiline(text: str) -> str:
    return dedent(text).strip() + "\n"


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SimpleModel(StreamableBaseModel):
    name: str
    age: int
    score: float
    active: bool


class StreamedStringModel(StreamableBaseModel):
    content: Annotated[str, Streamed]


class ListModel(StreamableBaseModel):
    items: list[str]
    numbers: list[int]


class NestedInnerModel(StreamableBaseModel):
    value: str


class NestedOuterModel(StreamableBaseModel):
    inner: NestedInnerModel


class EnumModel(StreamableBaseModel):
    status: Status


class OptionalModel(StreamableBaseModel):
    maybe_name: str | None


class ListNestedModel(StreamableBaseModel):
    items: list[NestedInnerModel]


@pytest.mark.parametrize(
    "annotation,expected",
    [
        (str, "AwaitableValue[str]"),
        (int, "AwaitableValue[int]"),
        (float, "AwaitableValue[float]"),
        (bool, "AwaitableValue[bool]"),
        (Annotated[str, Streamed], "StreamableValues[str]"),
        (list[str], "StreamableValues[str]"),
        (list[int], "StreamableValues[int]"),
        (Status, "AwaitableValue[Status]"),
        (str | None, "AwaitableValue[str | None]"),
    ],
)
def test_get_jmux_type(annotation, expected):
    result = get_jmux_type(annotation)
    assert result == expected


def test_get_jmux_type_nested_model():
    result = get_jmux_type(NestedInnerModel)
    assert result == "AwaitableValue[NestedInnerModelJMux]"


def test_get_jmux_type_list_nested_model():
    result = get_jmux_type(list[NestedInnerModel])
    assert result == "StreamableValues[NestedInnerModelJMux]"


def test_generate_jmux_code_simple_model():
    code = generate_jmux_code([SimpleModel])
    assert code == expect_multiline("""
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class SimpleModelJMux(JMux):
            name: AwaitableValue[str]
            age: AwaitableValue[int]
            score: AwaitableValue[float]
            active: AwaitableValue[bool]
    """)


def test_generate_jmux_code_streamed_string():
    code = generate_jmux_code([StreamedStringModel])
    assert code == expect_multiline("""
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class StreamedStringModelJMux(JMux):
            content: StreamableValues[str]
    """)


def test_generate_jmux_code_list_model():
    code = generate_jmux_code([ListModel])
    assert code == expect_multiline("""
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class ListModelJMux(JMux):
            items: StreamableValues[str]
            numbers: StreamableValues[int]
    """)


def test_generate_jmux_code_enum_model():
    code = generate_jmux_code([EnumModel])
    assert code == expect_multiline("""
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        from test_generator import Status

        class EnumModelJMux(JMux):
            status: AwaitableValue[Status]
    """)


def test_generate_jmux_code_optional_model():
    code = generate_jmux_code([OptionalModel])
    assert code == expect_multiline("""
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class OptionalModelJMux(JMux):
            maybe_name: AwaitableValue[str | None]
    """)


def test_generate_jmux_code_nested_model():
    code = generate_jmux_code([NestedOuterModel, NestedInnerModel])
    assert code == expect_multiline("""
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class NestedInnerModelJMux(JMux):
            value: AwaitableValue[str]

        class NestedOuterModelJMux(JMux):
            inner: AwaitableValue[NestedInnerModelJMux]
    """)


def test_generate_jmux_code_list_nested_model():
    code = generate_jmux_code([ListNestedModel, NestedInnerModel])
    assert code == expect_multiline("""
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class NestedInnerModelJMux(JMux):
            value: AwaitableValue[str]

        class ListNestedModelJMux(JMux):
            items: StreamableValues[NestedInnerModelJMux]
    """)


def test_generate_jmux_code_empty_list():
    code = generate_jmux_code([])
    assert code == expect_multiline("""
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux
    """)
