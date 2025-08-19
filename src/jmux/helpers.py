from types import NoneType
from typing import Set, Tuple, Type, get_args, get_origin

from jmux.error import ParsePrimitiveError
from jmux.types import TYPES_LIKE_NONE, TYPES_LIKE_UNION


def str_to_bool(s: str) -> bool:
    if s == "true":
        return True
    elif s == "false":
        return False
    else:
        raise ParsePrimitiveError(
            f"Cannot convert string '{s}' to boolean. Expected 'true' or 'false', got"
            f" '{s}'."
        )


def extract_types_from_generic_alias(UnknownType: Type) -> Tuple[Set[Type], Set[Type]]:
    Origin: Type | None = get_origin(UnknownType)
    if Origin is None:
        return {UnknownType}, set()
    if Origin in TYPES_LIKE_UNION:
        deconstructed = deconstruct_flat_type(UnknownType)
        maybe_list_types = [
            subtypes for subtypes in deconstructed if get_origin(subtypes) is list
        ]
        if len(maybe_list_types) == 1:
            list_based_type = maybe_list_types[0]
            non_list_types = deconstructed - {list_based_type}
            main_type, subtype = extract_types_from_generic_alias(list_based_type)
            return non_list_types | main_type, subtype
        return deconstructed, set()

    type_args = get_args(UnknownType)
    if len(type_args) != 1:
        raise TypeError(
            f"Only single type generics can be deconstruct with this function, "
            f"got {type_args}."
        )

    Generic: Type = type_args[0]
    type_set = deconstruct_flat_type(Generic)
    if len(type_set) == 1:
        return {Origin}, type_set
    if len(type_set) != 2:
        raise TypeError(
            f"Union type must have exactly two types in its union, "
            f"got {get_args(Generic)}."
        )
    if NoneType not in get_args(Generic):
        raise TypeError(
            "Union type must include NoneType if it is used as a generic argument."
        )
    return {Origin}, type_set


def deconstruct_flat_type(UnknownType: Type) -> Set[Type]:
    Origin: Type | None = get_origin(UnknownType)
    if UnknownType in TYPES_LIKE_NONE:
        return {NoneType}
    if Origin is None:
        return {UnknownType}
    if Origin in TYPES_LIKE_UNION:
        type_args = get_args(UnknownType)
        return set(type_args)
    raise TypeError(
        f"Unknown type {UnknownType} is not a Union or optional type, "
        "only only those types and their syntactic sugar are supported "
        "for flat deconstruction."
    )


def get_main_type(type_set: Set[Type]) -> Type:
    type_set_copy: Set[Type] = type_set.copy()
    if NoneType in type_set_copy and len(type_set_copy) == 2:
        type_set_copy.remove(NoneType)
    if len(type_set_copy) != 1:
        raise TypeError(
            f"Expected exactly one type, got {type_set_copy}. If you want to allow "
            "NoneType, use Union[int, NoneType]."
        )
    return type_set_copy.pop()
