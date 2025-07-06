from typing import Sequence


class MissingAttributeError(Exception):
    def __init__(self, object_name: str, attribute: str) -> None:
        super().__init__(f"'{object_name}' is missing required attribute '{attribute}'")


class UnexpectedAttributeTypeError(Exception):
    def __init__(self, object_name: str, attribute: str, expected_type: str) -> None:
        super().__init__(
            f"'{object_name}' has attribute '{attribute}' with unexpected type. Attribute must conform to {expected_type}."
        )


class EmptyKeyError(Exception):
    def __init__(self, message: str | None = None) -> None:
        super().__init__("Key cannot be empty" + (f": {message}" if message else ""))
        self.message = message


class TypeEmitError(Exception):
    def __init__(self, expected_type: str, actual_type: str) -> None:
        super().__init__(
            f"Cannot emit to current sink. Type mismatch: expected {expected_type}, got {actual_type}"
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


class UnexpectedCharacterError(Exception):
    def __init__(
        self,
        character: str,
        pda_stack: Sequence[str],
        pda_state: str,
        message: str | None,
    ) -> None:
        super().__init__(
            f"Received unexpected character '{character}' in state '{pda_state}' with stack {pda_stack}"
            + (f": {message}" if message else "")
        )
