from types import NoneType, UnionType
from typing import Set, Tuple, Type, get_args, get_origin


def is_json_whitespace(ch: str) -> bool:
    return ch in {" ", "\t", "\n", "\r"}


def extract_types_from_generic_alias(hint: Type) -> Tuple[Type, Set[Type]]:
    Origin: Type | None = get_origin(hint)
    if Origin is None:
        raise TypeError(
            "AwaitableValue must be initialized with a defined generic type."
        )
    type_args = get_args(hint)
    if len(type_args) != 1:
        raise TypeError(
            f"AwaitableValue must be initialized with a single generic type, got {type_args}."
        )
    Generic: Type = type_args[0]
    if Generic is None:
        raise TypeError("Generic type not defined.")
    type_set = deconstruct_type(Generic)
    if len(type_set) == 1:
        return Origin, type_set
    if len(type_set) != 2:
        raise TypeError(
            f"Union type must have exactly two types in its union, got {get_args(Generic)}."
        )
    if NoneType not in get_args(Generic):
        raise TypeError(
            "Union type must include NoneType if it is used as a generic argument."
        )
    return Origin, type_set


def deconstruct_type(UnknownType: Type) -> Set[Type]:
    Origin: Type | None = get_origin(UnknownType)
    if Origin is None:
        return {UnknownType}
    if Origin is not UnionType:
        return {Origin}
    type_args = get_args(UnknownType)
    return set(type_args)
