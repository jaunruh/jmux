from enum import Enum
from typing import Sequence


class MissingAttributeError(Exception):
    def __init__(self, object_name: str, attribute: str) -> None:
        super().__init__(f"'{object_name}' is missing required attribute '{attribute}'")


class UnexpectedAttributeTypeError(Exception):
    def __init__(self, object_name: str, attribute: str, expected_type: str) -> None:
        super().__init__(
            f"'{object_name}' has attribute '{attribute}' with unexpected type. "
            f"Attribute must conform to {expected_type}."
        )


class EmptyKeyError(Exception):
    def __init__(self, message: str | None = None) -> None:
        super().__init__("Key cannot be empty" + (f": {message}" if message else ""))
        self.message = message


class TypeEmitError(Exception):
    def __init__(self, expected_type: str, actual_type: str) -> None:
        super().__init__(
            f"Cannot emit to current sink. Type mismatch: expected {expected_type}, "
            f"got {actual_type}"
        )
        self.expected_type = expected_type
        self.actual_type = actual_type


class NoCurrentSinkError(Exception):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            "No current sink available" + (f": {message}" if message else "")
        )


class ParsePrimitiveError(Exception):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            "Failed to parse primitive value" + (f": {message}" if message else "")
        )


class NothingEmittedError(Exception):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            "Nothing was emitted to the sink" + (f": {message}" if message else "")
        )
        self.message = message


class SinkClosedError(Exception):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            "Sink is closed and cannot accept new items"
            + (f": {message}" if message else "")
        )
        self.message = message


class NotAllObjectPropertiesSetError(Exception):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            "Not all properties were set before closing the sink respective stream"
            + (f": {message}" if message else "")
        )


class ObjectAlreadyClosedError(Exception):
    def __init__(self, object_name: str, message: str | None = None) -> None:
        super().__init__(
            f"Object '{object_name}' is already closed"
            + (f": {message}" if message else "")
        )


class ObjectMissmatchedError(Exception):
    def __init__(
        self,
        jmux_model: str,
        pydantic_model: str,
        attribute: str,
        message: str | None = None,
    ) -> None:
        super().__init__(
            f"JMux object '{jmux_model}' and '{pydantic_model}' are missmatched on "
            f"attribute '{attribute}'" + (f": {message}" if message else "")
        )


class ForbiddenTypeHintsError(Exception):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            "Forbidden type hints used in object definition"
            + (f": {message}" if message else "")
        )


class UnexpectedCharacterError(Exception):
    def __init__(
        self,
        character: str,
        pda_stack: Sequence[Enum] | str,
        pda_state: Enum | str,
        message: str | None,
    ) -> None:
        pda_stack_str = [
            item.value if isinstance(item, Enum) else item for item in pda_stack
        ]
        pda_state_str = pda_state.value if isinstance(pda_state, Enum) else pda_state
        super().__init__(
            f"Received unexpected character '{character}' in state '{pda_state_str}' "
            f"with stack {pda_stack_str}" + (f": {message}" if message else "")
        )


class StreamParseError(Exception):
    def __init__(self, message: str | None = None) -> None:
        super().__init__("Failed to parse stream" + (f": {message}" if message else ""))
        self.message = message


class UnexpectedStateError(Exception):
    def __init__(
        self,
        pda_stack: Sequence[Enum] | str,
        pda_state: Enum | str,
        message: str | None = None,
    ) -> None:
        pda_stack_str = [
            item.value if isinstance(item, Enum) else item for item in pda_stack
        ]
        pda_state_str = pda_state.value if isinstance(pda_state, Enum) else pda_state
        super().__init__(
            f"Unexpected state '{pda_state_str}' with stack {pda_stack_str}"
            + (f": {message}" if message else "")
        )
