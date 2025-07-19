# JMux: A Python package for demultiplexing a JSON string into multiple awaitable variables.

JMux is a powerful Python package that allows you to demultiplex a JSON stream into multiple awaitable variables. It is specifically designed for asynchronous applications that interact with Large Language Models (LLMs) using libraries like `litellm`. When an LLM streams a JSON response, `jmux` enables you to parse and use parts of the JSON object _before_ the complete response has been received, significantly improving responsiveness.

## Features

- **Asynchronous by Design**: Built on top of `asyncio`, JMux is perfect for modern, high-performance Python applications.
- **Pydantic Integration**: Validate your `JMux` classes against Pydantic models to ensure type safety and consistency.
- **Awaitable and Streamable Sinks**: Use `AwaitableValue` for single values and `StreamableValues` for streams of values.
- **Robust Error Handling**: JMux provides a comprehensive set of exceptions to handle parsing errors and other issues.
- **Lightweight and Zero-dependency**: JMux has no external dependencies, making it easy to integrate into any project.

## Installation

You can install JMux from PyPI using pip:

```bash
pip install jmux
```

## Usage with LLMs (e.g., `litellm`)

The primary use case for `jmux` is to process streaming JSON responses from LLMs. This allows you to react to parts of the data as it arrives, rather than waiting for the entire JSON object to be transmitted.

Here’s a conceptual example of how you might integrate `jmux` with an LLM call, such as one made with `litellm`:

```python
import asyncio
from pydantic import BaseModel
from jmux import JMux, AwaitableValue, StreamableValues
# litellm is used conceptually here
# from litellm import acompletion

# 1. Define the Pydantic model for the expected JSON response
class LlmResponse(BaseModel):
    thought: str
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

### `jmux.JMux`

The abstract base class for creating JSON demultiplexers.

#### `JMux.assert_conforms_to(pydantic_model: Type[BaseModel]) -> None`

Asserts that the JMux class conforms to a given Pydantic model.

#### `async JMux.feed_char(ch: str) -> None`

Feeds a character to the JMux parser.

#### `async JMux.feed_chunks(chunks: str) -> None`

Feeds a string of characters to the JMux parser.

### `jmux.AwaitableValue[T]`

A class that represents a value that will be available in the future.

### `jmux.StreamableValues[T]`

A class that represents a stream of values that can be asynchronously iterated over.

## License

This project is licensed under the terms of the MIT license. See the [LICENSE](LICENSE) file for details.
