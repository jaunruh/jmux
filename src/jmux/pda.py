from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

Context = TypeVar("Context")
State = TypeVar("State")


class PushDownAutomata(Generic[Context, State]):
    def __init__(self, start_state: State) -> None:
        self._stack: List[Context] = []
        self._state: State = start_state

    @property
    def state(self) -> State:
        return self._state

    @property
    def stack(self) -> List[Context]:
        return self._stack

    @property
    def top(self) -> Optional[Context]:
        if not self._stack:
            return None
        return self._stack[-1]

    def set_state(self, new_state: State) -> None:
        self._state = new_state

    def push(self, mode: Context) -> None:
        self._stack.append(mode)

    def pop(self) -> Context:
        if not self._stack:
            raise IndexError("PDA stack is empty.")
        return self._stack.pop()
