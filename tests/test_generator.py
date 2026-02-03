from enum import Enum
from textwrap import dedent
from typing import Annotated, Optional, Union

import pytest

from jmux.base import StreamableBaseModel, Streamed
from jmux.generator import extract_models_from_source, generate_jmux_code, get_jmux_type


def dedent_strip(text: str) -> str:
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
        (Union[str, None], "AwaitableValue[str | None]"),
        (Optional[str], "AwaitableValue[str | None]"),
        (NestedInnerModel, "AwaitableValue[NestedInnerModelJMux]"),
        (list[NestedInnerModel], "StreamableValues[NestedInnerModelJMux]"),
    ],
)
def test_get_jmux_type(annotation, expected):
    assert get_jmux_type(annotation) == expected


def test_extract_no_import():
    source = dedent_strip(
        """
        class Foo:
            pass
        """
    )
    assert extract_models_from_source(source) == []


def test_extract_syntax_error():
    assert extract_models_from_source("class Foo( invalid syntax") == []


def test_extract_simple():
    source = dedent_strip(
        """
        from jmux import StreamableBaseModel

        class MyModel(StreamableBaseModel):
            name: str
            age: int
        """
    )
    models = extract_models_from_source(source)
    assert len(models) == 1
    assert models[0].__name__ == "MyModel"
    assert set(models[0].model_fields.keys()) == {"name", "age"}


def test_extract_multiple_models():
    source = dedent_strip(
        """
        from jmux import StreamableBaseModel

        class First(StreamableBaseModel):
            a: str

        class Second(StreamableBaseModel):
            b: int

        class NotAModel:
            c: float
        """
    )
    models = extract_models_from_source(source)
    assert len(models) == 2
    assert {m.__name__ for m in models} == {"First", "Second"}


def test_extract_with_streamed():
    source = dedent_strip(
        """
        from typing import Annotated
        from jmux import StreamableBaseModel, Streamed

        class StreamedModel(StreamableBaseModel):
            content: Annotated[str, Streamed]
            title: str
        """
    )
    models = extract_models_from_source(source)
    assert len(models) == 1
    assert models[0].__name__ == "StreamedModel"
    assert set(models[0].model_fields.keys()) == {"content", "title"}


def test_extract_with_list():
    source = dedent_strip(
        """
        from jmux import StreamableBaseModel

        class ListModel(StreamableBaseModel):
            items: list[str]
            tags: list[int]
        """
    )
    models = extract_models_from_source(source)
    assert len(models) == 1
    assert models[0].__name__ == "ListModel"


def test_extract_with_optional():
    source = dedent_strip(
        """
        from jmux import StreamableBaseModel

        class OptionalModel(StreamableBaseModel):
            maybe_name: str | None
            required: str
        """
    )
    models = extract_models_from_source(source)
    assert len(models) == 1
    assert models[0].__name__ == "OptionalModel"


def test_extract_nested_models():
    source = dedent_strip(
        """
        from jmux import StreamableBaseModel

        class Inner(StreamableBaseModel):
            value: str

        class Outer(StreamableBaseModel):
            inner: Inner
        """
    )
    models = extract_models_from_source(source)
    assert len(models) == 2
    assert {m.__name__ for m in models} == {"Inner", "Outer"}


def test_generate_jmux_code_empty_list():
    assert generate_jmux_code([]) == dedent_strip(
        """
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux
        """
    )


def test_generate_jmux_code_simple_model():
    code = generate_jmux_code([SimpleModel])
    assert code == dedent_strip(
        """
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class SimpleModelJMux(JMux):
            name: AwaitableValue[str]
            age: AwaitableValue[int]
            score: AwaitableValue[float]
            active: AwaitableValue[bool]
        """
    )


def test_generate_jmux_code_streamed_string():
    code = generate_jmux_code([StreamedStringModel])
    assert code == dedent_strip(
        """
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class StreamedStringModelJMux(JMux):
            content: StreamableValues[str]
        """
    )


def test_generate_jmux_code_list_model():
    code = generate_jmux_code([ListModel])
    assert code == dedent_strip(
        """
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class ListModelJMux(JMux):
            items: StreamableValues[str]
            numbers: StreamableValues[int]
        """
    )


def test_generate_jmux_code_enum_model():
    code = generate_jmux_code([EnumModel])
    assert code == dedent_strip(
        """
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        from test_generator import Status

        class EnumModelJMux(JMux):
            status: AwaitableValue[Status]
        """
    )


def test_generate_jmux_code_optional_model():
    code = generate_jmux_code([OptionalModel])
    assert code == dedent_strip(
        """
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class OptionalModelJMux(JMux):
            maybe_name: AwaitableValue[str | None]
        """
    )


def test_generate_jmux_code_nested_model():
    code = generate_jmux_code([NestedOuterModel, NestedInnerModel])
    assert code == dedent_strip(
        """
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class NestedInnerModelJMux(JMux):
            value: AwaitableValue[str]

        class NestedOuterModelJMux(JMux):
            inner: AwaitableValue[NestedInnerModelJMux]
        """
    )


def test_generate_jmux_code_list_nested_model():
    code = generate_jmux_code([ListNestedModel, NestedInnerModel])
    assert code == dedent_strip(
        """
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux

        class NestedInnerModelJMux(JMux):
            value: AwaitableValue[str]

        class ListNestedModelJMux(JMux):
            items: StreamableValues[NestedInnerModelJMux]
        """
    )


def test_generate_jmux_code_enum_imports():
    code = generate_jmux_code([])
    assert code == dedent_strip(
        """
        from enum import Enum
        from typing import Union

        from jmux.awaitable import AwaitableValue, StreamableValues
        from jmux.demux import JMux
        """
    )
