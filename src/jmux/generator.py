from __future__ import annotations

import ast
import importlib.util
import sys
from enum import Enum
from pathlib import Path
from types import ModuleType, NoneType
from typing import Annotated, Any, get_args, get_origin, get_type_hints

from pydantic import BaseModel

from jmux.base import StreamableBaseModel, Streamed


def extract_models_from_source(
    source: str,
    module_name: str = "__jmux_extract__",
) -> list[type[StreamableBaseModel]]:
    if not _source_imports_streamable_base_model(source):
        return []

    module = _exec_source_as_module(source, module_name)
    if module is None:
        return []

    return _extract_models_from_module(module)


def find_streamable_models(root_path: Path) -> list[type[StreamableBaseModel]]:
    models: list[type[StreamableBaseModel]] = []
    root_path = root_path.resolve()

    for py_file in root_path.rglob("*.py"):
        source = _read_file_safe(py_file)
        if source is None:
            continue

        if not _source_imports_streamable_base_model(source):
            continue

        module = _import_module_from_path(py_file, root_path)
        if module is None:
            continue

        models.extend(_extract_models_from_module(module))

    return models


def _extract_models_from_module(
    module: ModuleType,
) -> list[type[StreamableBaseModel]]:
    models: list[type[StreamableBaseModel]] = []
    for name in dir(module):
        obj = getattr(module, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, StreamableBaseModel)
            and obj is not StreamableBaseModel
        ):
            models.append(obj)
    return models


def _read_file_safe(py_file: Path) -> str | None:
    try:
        return py_file.read_text()
    except (OSError, UnicodeDecodeError):
        return None


def _source_imports_streamable_base_model(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "jmux" in node.module:
                for alias in node.names:
                    if alias.name == "StreamableBaseModel":
                        return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "jmux" in alias.name:
                    return True
    return False


def _exec_source_as_module(source: str, module_name: str) -> ModuleType | None:
    try:
        module = ModuleType(module_name)
        module.__dict__["__builtins__"] = __builtins__
        sys.modules[module_name] = module
        exec(compile(source, f"<{module_name}>", "exec"), module.__dict__)
        return module
    except Exception:
        if module_name in sys.modules:
            del sys.modules[module_name]
        return None


def _import_module_from_path(py_file: Path, root_path: Path) -> ModuleType | None:
    try:
        relative = py_file.relative_to(root_path)
        module_name = str(relative.with_suffix("")).replace("/", ".").replace("\\", ".")

        if root_path not in [Path(p) for p in sys.path]:
            sys.path.insert(0, str(root_path))

        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def _is_streamed_marker(obj: Any) -> bool:
    if obj is Streamed:
        return True
    if isinstance(obj, type) and obj.__name__ == "Streamed":
        return True
    return False


def _get_resolved_annotations(model: type[StreamableBaseModel]) -> dict[str, Any]:
    try:
        globalns = getattr(sys.modules.get(model.__module__, None), "__dict__", {})
        return get_type_hints(model, globalns=globalns, include_extras=True)
    except Exception:
        return model.__annotations__


def generate_jmux_code(models: list[type[StreamableBaseModel]]) -> str:
    lines = [
        "from enum import Enum",
        "from typing import Union",
        "",
        "from jmux.awaitable import AwaitableValue, StreamableValues",
        "from jmux.demux import JMux",
        "",
    ]

    enum_imports = _collect_enum_imports(models)
    if enum_imports:
        lines.extend(enum_imports)
        lines.append("")

    nested_models = _collect_nested_models(models)
    all_models = _topological_sort(models, nested_models)

    for model in all_models:
        class_lines = _generate_class(model)
        lines.extend(class_lines)
        lines.append("")

    return "\n".join(lines)


def _collect_enum_imports(models: list[type[StreamableBaseModel]]) -> list[str]:
    enums: set[type[Enum]] = set()
    for model in models:
        resolved = _get_resolved_annotations(model)
        for field_name in model.model_fields:
            annotation = resolved.get(field_name)
            if annotation is None:
                continue
            _collect_enums_from_type(annotation, enums)

    imports = []
    for enum_type in enums:
        module = enum_type.__module__
        name = enum_type.__name__
        imports.append(f"from {module} import {name}")
    return sorted(imports)


def _collect_enums_from_type(annotation: Any, enums: set[type[Enum]]) -> None:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Annotated:
        if args:
            _collect_enums_from_type(args[0], enums)
        return

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        enums.add(annotation)
        return

    if origin is list and args:
        _collect_enums_from_type(args[0], enums)


def _collect_nested_models(
    models: list[type[StreamableBaseModel]],
) -> set[type[StreamableBaseModel]]:
    nested: set[type[StreamableBaseModel]] = set()
    for model in models:
        resolved = _get_resolved_annotations(model)
        for field_name in model.model_fields:
            annotation = resolved.get(field_name)
            if annotation is None:
                continue
            _collect_nested_from_type(annotation, nested)
    return nested


def _collect_nested_from_type(
    annotation: Any, nested: set[type[StreamableBaseModel]]
) -> None:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Annotated:
        if args:
            _collect_nested_from_type(args[0], nested)
        return

    if (
        isinstance(annotation, type)
        and issubclass(annotation, BaseModel)
        and issubclass(annotation, StreamableBaseModel)
        and annotation is not StreamableBaseModel
    ):
        nested.add(annotation)
        return

    if origin is list and args:
        _collect_nested_from_type(args[0], nested)


def _topological_sort(
    models: list[type[StreamableBaseModel]],
    nested: set[type[StreamableBaseModel]],
) -> list[type[StreamableBaseModel]]:
    all_models = set(models) | nested
    result: list[type[StreamableBaseModel]] = []
    visited: set[type[StreamableBaseModel]] = set()

    def visit(model: type[StreamableBaseModel]) -> None:
        if model in visited:
            return
        visited.add(model)
        resolved = _get_resolved_annotations(model)
        for field_name in model.model_fields:
            annotation = resolved.get(field_name)
            if annotation is None:
                continue
            dep = _get_nested_model_dependency(annotation)
            if dep and dep in all_models:
                visit(dep)
        result.append(model)

    for model in all_models:
        visit(model)

    return result


def _get_nested_model_dependency(annotation: Any) -> type[StreamableBaseModel] | None:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Annotated:
        if args:
            return _get_nested_model_dependency(args[0])
        return None

    if (
        isinstance(annotation, type)
        and issubclass(annotation, BaseModel)
        and issubclass(annotation, StreamableBaseModel)
        and annotation is not StreamableBaseModel
    ):
        return annotation

    if origin is list and args:
        return _get_nested_model_dependency(args[0])

    return None


def _generate_class(model: type[StreamableBaseModel]) -> list[str]:
    class_name = f"{model.__name__}JMux"
    lines = [f"class {class_name}(JMux):"]

    resolved = _get_resolved_annotations(model)
    has_fields = False
    for field_name in model.model_fields:
        annotation = resolved.get(field_name)
        if annotation is None:
            continue
        jmux_type = get_jmux_type(annotation)
        lines.append(f"    {field_name}: {jmux_type}")
        has_fields = True

    if not has_fields:
        lines.append("    pass")

    return lines


def get_jmux_type(annotation: Any) -> str:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Annotated:
        inner_type = args[0] if args else None
        metadata = args[1:] if len(args) > 1 else ()
        has_streamed = any(_is_streamed_marker(m) for m in metadata)

        if has_streamed and inner_type is str:
            return "StreamableValues[str]"

        return get_jmux_type(inner_type)

    if origin is list:
        inner = args[0] if args else Any
        inner_jmux = _get_inner_type_str(inner)
        return f"StreamableValues[{inner_jmux}]"

    if annotation is str:
        return "AwaitableValue[str]"

    if annotation is int:
        return "AwaitableValue[int]"

    if annotation is float:
        return "AwaitableValue[float]"

    if annotation is bool:
        return "AwaitableValue[bool]"

    if annotation is NoneType or annotation is None:
        return "AwaitableValue[None]"

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return f"AwaitableValue[{annotation.__name__}]"

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if issubclass(annotation, StreamableBaseModel):
            return f"AwaitableValue[{annotation.__name__}JMux]"
        return f"AwaitableValue[{annotation.__name__}]"

    type_origin = get_origin(annotation)
    if type_origin is type(None | str):
        non_none_args = [a for a in args if a is not NoneType and a is not None]
        if len(non_none_args) == 1:
            inner = _get_inner_type_str(non_none_args[0])
            return f"AwaitableValue[{inner} | None]"
        return f"AwaitableValue[{annotation}]"

    return f"AwaitableValue[{annotation}]"


def _get_inner_type_str(annotation: Any) -> str:
    if annotation is str:
        return "str"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is bool:
        return "bool"
    if annotation is NoneType or annotation is None:
        return "None"
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation.__name__
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if issubclass(annotation, StreamableBaseModel):
            return f"{annotation.__name__}JMux"
        return annotation.__name__
    return str(annotation)
