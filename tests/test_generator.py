from enum import Enum
from typing import Annotated

import pytest

from jmux.base import StreamableBaseModel, Streamed
from jmux.generator import generate_jmux_code, get_jmux_type


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
    assert "class SimpleModelJMux(JMux):" in code
    assert "name: AwaitableValue[str]" in code
    assert "age: AwaitableValue[int]" in code
    assert "score: AwaitableValue[float]" in code
    assert "active: AwaitableValue[bool]" in code


def test_generate_jmux_code_streamed_string():
    code = generate_jmux_code([StreamedStringModel])
    assert "class StreamedStringModelJMux(JMux):" in code
    assert "content: StreamableValues[str]" in code


def test_generate_jmux_code_list_model():
    code = generate_jmux_code([ListModel])
    assert "class ListModelJMux(JMux):" in code
    assert "items: StreamableValues[str]" in code
    assert "numbers: StreamableValues[int]" in code


def test_generate_jmux_code_enum_model():
    code = generate_jmux_code([EnumModel])
    assert "class EnumModelJMux(JMux):" in code
    assert "status: AwaitableValue[Status]" in code
    assert "import Status" in code


def test_generate_jmux_code_optional_model():
    code = generate_jmux_code([OptionalModel])
    assert "class OptionalModelJMux(JMux):" in code
    assert "maybe_name: AwaitableValue[str | None]" in code


def test_generate_jmux_code_nested_model():
    code = generate_jmux_code([NestedOuterModel, NestedInnerModel])
    assert "class NestedInnerModelJMux(JMux):" in code
    assert "class NestedOuterModelJMux(JMux):" in code
    assert "inner: AwaitableValue[NestedInnerModelJMux]" in code
    inner_index = code.index("class NestedInnerModelJMux")
    outer_index = code.index("class NestedOuterModelJMux")
    assert inner_index < outer_index


def test_generate_jmux_code_list_nested_model():
    code = generate_jmux_code([ListNestedModel, NestedInnerModel])
    assert "class ListNestedModelJMux(JMux):" in code
    assert "items: StreamableValues[NestedInnerModelJMux]" in code


def test_generate_jmux_code_imports():
    code = generate_jmux_code([SimpleModel])
    assert "from jmux.awaitable import AwaitableValue, StreamableValues" in code
    assert "from jmux.demux import JMux" in code


def test_generate_jmux_code_empty_list():
    code = generate_jmux_code([])
    assert "from jmux.awaitable import AwaitableValue, StreamableValues" in code
    assert "from jmux.demux import JMux" in code
    assert "class" not in code.split("JMux")[-1]
