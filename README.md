# JMux: A Python package for demultiplexing a JSON string into multiple awaitable variables.

JMux is a powerful Python package that allows you to demultiplex a JSON stream into multiple awaitable variables. It is specifically designed for asynchronous applications that interact with Large Language Models (LLMs) using libraries like `litellm`. When an LLM streams a JSON response, `jmux` enables you to parse and use parts of the JSON object _before_ the complete response has been received, significantly improving responsiveness.

## Inspiration

This package is inspired by `Snapshot Streaming` mentioned in the [`WWDC25: Meet the Foundation Models framework`](https://youtu.be/mJMvFyBvZEk?si=DVIvxzuJOA87lb7I&t=465) keynote by Apple.

## Features

- **Asynchronous by Design**: Built on top of `asyncio`, JMux is perfect for modern, high-performance Python applications.
- **Pydantic Integration**: Validate your `JMux` classes against Pydantic models to ensure type safety and consistency.
- **Awaitable and Streamable Sinks**: Use `AwaitableValue` for single values and `StreamableValues` for streams of values.
- **Robust Error Handling**: JMux provides a comprehensive set of exceptions to handle parsing errors and other issues.
- **Lightweight**: JMux has only a few external dependencies, making it easy to integrate into any project.

## Installation

You can install JMux from PyPI using pip:

```bash
pip install jmux
```

## Usage with LLMs (e.g., `litellm`)

The primary use case for `jmux` is to process streaming JSON responses from LLMs. This allows you to react to parts of the data as it arrives, rather than waiting for the entire JSON object to be transmitted. While this should be obvious, I should mention, that **the order in which the pydantic model defines the properties, defines which stream is filled first**.

Here’s a conceptual example of how you might integrate `jmux` with an LLM call, such as one made with `litellm`:

```python
import asyncio
from pydantic import BaseModel
from jmux import JMux, AwaitableValue, StreamableValues
# litellm is used conceptually here
# from litellm import acompletion

# 1. Define the Pydantic model for the expected JSON response
class LlmResponse(BaseModel):
    thought: str # **This property is filled first**
    tool_code: str

# 2. Define the corresponding JMux class
class LlmResponseMux(JMux):
    thought: AwaitableValue[str]
    tool_code: StreamableValues[str] # Stream the code as it's generated

# 3. Validate that the JMux class matches the Pydantic model
LlmResponseMux.assert_conforms_to(LlmResponse)

# A mock function that simulates a streaming LLM call
async def mock_llm_stream():
    json_stream = '{"thought": "I need to write some code.", "tool_code": "print(\'Hello, World!\')"}'
    for char in json_stream:
        yield char
        await asyncio.sleep(0.01) # Simulate network latency

# Main function to orchestrate the call and processing
async def process_llm_response():
    jmux_instance = LlmResponseMux()

    # This task will consume the LLM stream and feed it to jmux
    async def feed_stream():
        async for chunk in mock_llm_stream():
            await jmux_instance.feed_chunks(chunk)

    # These tasks will consume the demultiplexed data from jmux
    async def consume_thought():
        thought = await jmux_instance.thought
        print(f"LLM's thought received: '{thought}'")
        # You can act on the thought immediately
        # without waiting for the tool_code to finish streaming.

    async def consume_tool_code():
        print("Receiving tool code...")
        full_code = ""
        async for code_fragment in jmux_instance.tool_code:
            full_code += code_fragment
            print(f"  -> Received fragment: {code_fragment}")
        print(f"Full tool code received: {full_code}")

    # Run all tasks concurrently
    await asyncio.gather(
        feed_stream(),
        consume_thought(),
        consume_tool_code()
    )

if __name__ == "__main__":
    asyncio.run(process_llm_response())
```

## Example Implementation

<details>
<summary>Python Code</summary>

```python
def create_json_streaming_completion[T: BaseModel, J: IJsonDemuxer](
        self,
        messages: List[ILlmMessage],
        ReturnType: Type[T],
        JMux: Type[J],
        retries: int = 3,
    ) -> StreamResponseTuple[T, J]:
        try:
            JMux.assert_conforms_to(ReturnType)
            litellm_messages = self._convert_messages(messages)
            jmux_instance: J = JMux()

            async def stream_feeding_llm_call() -> T:
                nonlocal jmux_instance
                buffer = ""
                stream: CustomStreamWrapper = await self._router.acompletion( # see litellm `router`
                    model=self._internal_model_name.value,
                    messages=litellm_messages,
                    stream=True,
                    num_retries=retries,
                    response_format=ReturnType,
                    **self._maybe_google_credentials_param,
                    **self._model_params.model_dump(exclude_none=True),
                    **self._additional_params,
                )

                async for chunk in stream:
                    content_fragment: str | None = None

                    tool_calls = chunk.choices[0].delta.tool_calls
                    if tool_calls:
                        content_fragment = tool_calls[0].function.arguments
                    elif chunk.choices[0].delta.content:
                        content_fragment = chunk.choices[0].delta.content

                    if content_fragment:
                        try:
                            buffer += content_fragment
                            await jmux_instance.feed_chunks(content_fragment)
                        except Exception as e:
                            logger.warning(f"error in JMux feed_chunks: {e}")
                            raise e

                return ReturnType.model_validate_json(buffer)

            awaitable_llm_result = create_task(stream_feeding_llm_call())
            return (awaitable_llm_result, jmux_instance)
        except Exception as e:
            logger.warning(f"error in create_json_streaming_completion: {e}")
            raise e
```

The code above shows an example implementation that uses a `litellm` router for `acompletion`.

You can either `await awaitable_llm_result` if you need the full result, or use `await jmux_instance.your_awaitable_value` or `async for ele in jmux_instance.your_streamable_values` to access partial results.

</details>

## Basic Usage

Here is a simple example of how to use JMux to parse a JSON stream:

```python
import asyncio
from enum import Enum
from types import NoneType
from pydantic import BaseModel

from jmux import JMux, AwaitableValue, StreamableValues

# 1. Define your JMux class
class SObject(JMux):
    class SNested(JMux):
        key_str: AwaitableValue[str]

    class SEnum(Enum):
        VALUE1 = "value1"
        VALUE2 = "value2"

    key_str: AwaitableValue[str]
    key_int: AwaitableValue[int]
    key_float: AwaitableValue[float]
    key_bool: AwaitableValue[bool]
    key_none: AwaitableValue[NoneType]
    key_stream: StreamableValues[str]
    key_enum: AwaitableValue[SEnum]
    key_nested: AwaitableValue[SNested]

# 2. (Optional) Define a Pydantic model for validation
class PObject(BaseModel):
    class PNested(BaseModel):
        key_str: str

    class PEnum(Enum):
        VALUE1 = "value1"
        VALUE2 = "value2"

    key_str: str
    key_int: int
    key_float: float
    key_bool: bool
    key_none: NoneType
    key_stream: str
    key_enum: PEnum
    key_nested: PNested

# 3. Validate the JMux class against the Pydantic model
SObject.assert_conforms_to(PObject)

# 4. Create an instance of your JMux class
s_object = SObject()

# 5. Feed the JSON stream to the JMux instance
async def main():
    json_stream = '{"key_str": "hello", "key_int": 42, "key_float": 3.14, "key_bool": true, "key_none": null, "key_stream": "world", "key_enum": "value1", "key_nested": {"key_str": "nested"}}'

    async def produce():
        for char in json_stream:
            await s_object.feed_char(char)

    async def consume():
        key_str = await s_object.key_str
        print(f"key_str: {key_str}")

        key_int = await s_object.key_int
        print(f"key_int: {key_int}")

        key_float = await s_object.key_float
        print(f"key_float: {key_float}")

        key_bool = await s_object.key_bool
        print(f"key_bool: {key_bool}")

        key_none = await s_object.key_none
        print(f"key_none: {key_none}")

        key_stream = ""
        async for char in s_object.key_stream:
            key_stream += char
        print(f"key_stream: {key_stream}")

        key_enum = await s_object.key_enum
        print(f"key_enum: {key_enum}")

        key_nested = await s_object.key_nested
        nested_key_str = await key_nested.key_str
        print(f"nested_key_str: {nested_key_str}")

    await asyncio.gather(produce(), consume())

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### Abstract Calss `jmux.JMux`

The abstract base class for creating JSON demultiplexers.

> `JMux.assert_conforms_to(pydantic_model: Type[BaseModel]) -> None`

Asserts that the JMux class conforms to a given Pydantic model.

> `async JMux.feed_char(ch: str) -> None`

Feeds a character to the JMux parser.

> `async JMux.feed_chunks(chunks: str) -> None`

Feeds a string of characters to the JMux parser.

### Class `jmux.AwaitableValue[T]`

A class that represents a value that will be available in the future. You are awaiting the full value and do not get partial results.

Allowed types here are (they can all be combined with `Optional`):

- `int`, `float`, `str`, `bool`, `NoneType`
- `JMux`
- `Enum`

In all cases, the corresponding `pydantic.BaseModel` should **not** be `list`

### Class `jmux.StreamableValues[T]`

A class that represents a stream of values that can be asynchronously iterated over.

Allowed types are listed below and should all be wrapped in a `list` on the pydantic model:

- `int`, `float`, `str`, `bool`, `NoneType`
- `JMux`
- `Enum`

Additionally the following type is supported without being wrapped into `list`:

- `str`

This allows you to fully stream strings directly to a sink.

## License

This project is licensed under the terms of the MIT license. See the [LICENSE](LICENSE) file for details.

## Planned Improvements

- Add support for older Python versions

## Contributions

As you might see, this repo has only been created recently and so far I am the only developer working on it. If you want to contribute, reach out via `johannes@unruh.ai` or `johannes.a.unruh@gmail.com`.

If you have suggestions or find any errors in my implementation, feel free to create an issue or also reach out via email.
