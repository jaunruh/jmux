from asyncio import Event, Queue
from enum import Enum
from types import NoneType
from typing import (
    AsyncGenerator,
    Protocol,
    Set,
    Type,
    cast,
    runtime_checkable,
)

from jmux.error import NothingEmittedError, SinkClosedError
from jmux.helpers import extract_types_from_generic_alias


class SinkType(Enum):
    STREAMABLE_VALUES = "StreamableValues"
    AWAITABLE_VALUE = "AwaitableValue"


class UnderlyingGenericMixin[T]:
    def get_underlying_generics(self) -> Set[Type[T]]:
        # `__orig_class__` is only set after the `__init__` method is called
        if not hasattr(self, "__orig_class__"):
            raise TypeError(
                "AwaitableValue must be initialized with a defined generic type."
            )

        Origin = getattr(self, "__orig_class__")
        _, type_set = extract_types_from_generic_alias(Origin)
        return type_set

    def get_underlying_main_generic(self) -> Type[T]:
        underlying_generics = self.get_underlying_generics()
        if len(underlying_generics) == 1:
            return underlying_generics.pop()
        remaining = {g for g in underlying_generics if g is not NoneType}
        return remaining.pop()


@runtime_checkable
class IAsyncSink[T](Protocol):
    def get_underlying_generics(self) -> Set[Type[T]]:
        """Return the underlying generic type of the sink."""
        ...

    def get_underlying_main_generic(self) -> Type[T]:
        """Return the underlying non-NoneType generic type of the sink."""
        ...

    async def put(self, item: T):
        """Put an item into the sink."""
        ...

    async def close(self):
        """Close the sink."""
        ...

    async def ensure_closed(self):
        """Ensure the sink is closed."""
        ...

    def get_current(self) -> T:
        """Get the current value from the sink."""
        ...

    def get_sink_type(self) -> SinkType:
        """Get the type of the sink."""
        ...


class StreamableValues[T](UnderlyingGenericMixin[T]):
    def __init__(self):
        self._queue = Queue[T | None]()
        self._last_item: T | None = None
        self._closed = False

    def get_underlying_generics(self) -> Set[Type[T]]:
        generic = super().get_underlying_generics()
        if len(generic) != 1:
            raise TypeError("StreamableValues must have exactly one underlying type.")
        return generic

    async def put(self, item: T):
        if self._closed:
            raise ValueError("Cannot put item into a closed sink.")
        self._last_item = item
        await self._queue.put(item)

    async def close(self):
        if self._closed:
            raise SinkClosedError(
                f"SinkType {self.get_sink_type()}[{self.get_underlying_main_generic()}] is already closed."
            )
        self._closed = True
        await self._queue.put(None)

    async def ensure_closed(self):
        if self._closed:
            return
        await self.close()

    def get_current(self) -> T:
        if self._last_item is None:
            raise ValueError("StreamableValues has not received any items yet.")
        return self._last_item

    def get_sink_type(self) -> SinkType:
        return SinkType.STREAMABLE_VALUES

    def __aiter__(self):
        return self._stream()

    async def _stream(self) -> AsyncGenerator[T, None]:
        while True:
            item = await self._queue.get()
            if item is None and self._closed:
                break
            if item is None:
                raise ValueError("Received None item, but the sink is not closed.")
            yield item


class AwaitableValue[T](UnderlyingGenericMixin[T]):
    def __init__(self):
        self._is_closed = False
        self._event = Event()
        self._value: T | None = None

    async def put(self, value: T):
        if self._value is not None or self._is_closed or self._event.is_set():
            raise ValueError("AwaitableValue can only be set once.")
        self._value = value
        self._event.set()

    async def close(self):
        if self._is_closed:
            raise SinkClosedError(
                f"SinkType {self.get_sink_type()}[{self.get_underlying_main_generic().__name__}] is already closed."
            )
        elif not self._event.is_set() and NoneType in self.get_underlying_generics():
            self._event.set()
        elif not self._event.is_set():
            raise NothingEmittedError(
                "Trying to close non-NoneType AwaitableValue without a value."
            )
        self._is_closed = True

    async def ensure_closed(self):
        if self._is_closed:
            return
        await self.close()

    def get_current(self) -> T:
        if self._value is None:
            raise ValueError("AwaitableValue has not been set yet.")
        return self._value

    def get_sink_type(self) -> SinkType:
        return SinkType.AWAITABLE_VALUE

    def __await__(self):
        return self._wait().__await__()

    async def _wait(self) -> T:
        await self._event.wait()
        if self._value is None and not self._event.is_set():
            raise ValueError("No value has been put into the sink.")
        return cast(T, self._value)
