from asyncio import Event, Queue
from typing import AsyncGenerator, Literal, Protocol, Type, cast, runtime_checkable

type SinkType = Literal["StreamableValues", "AwaitableValue"]


class UnderlyingGenericMixin[T]:
    def get_underlying_generic(self) -> Type[T]:
        # `__orig_class__` is only set after the `__init__` method is called
        if not hasattr(self, "__orig_class__"):
            raise TypeError(
                "AwaitableValue must be initialized with a defined generic type."
            )

        Origin = getattr(self, "__orig_class__")
        if len(Origin.__args__) != 1:
            raise TypeError(
                f"AwaitableValue must be initialized with a single generic type, got {Origin.__args__}."
            )
        Generic: Type[T] = Origin.__args__[0]
        return Generic


@runtime_checkable
class IAsyncSink[T](Protocol):
    def get_underlying_generic(self) -> Type[T]:
        """Return the underlying generic type of the sink."""
        ...

    async def put(self, item: T):
        """Put an item into the sink."""
        ...

    async def close(self):
        """Close the sink."""
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

    async def put(self, item: T):
        if self._closed:
            raise ValueError("Cannot put item into a closed sink.")
        self._last_item = item
        await self._queue.put(item)

    async def close(self):
        self._closed = True
        await self._queue.put(None)

    def get_current(self) -> T:
        if self._last_item is None:
            raise ValueError("StreamableValues has not received any items yet.")
        return self._last_item

    def get_sink_type(self) -> SinkType:
        return "StreamableValues"

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
        self._value_set = False
        self._event = Event()
        self._value: T | None = None

    async def put(self, value: T):
        if self._value:
            raise ValueError("AwaitableValue can only be set once.")
        self._value_set = True
        self._value = value
        self._event.set()

    async def close(self):
        pass

    def get_current(self) -> T:
        if not self._value:
            raise ValueError("AwaitableValue has not been set yet.")
        return self._value

    def get_sink_type(self) -> SinkType:
        return "AwaitableValue"

    def __await__(self):
        return self._wait().__await__()

    async def _wait(self) -> T:
        await self._event.wait()
        if self._value is None and not self._value_set:
            raise ValueError("No value has been put into the sink.")
        return cast(T, self._value)
