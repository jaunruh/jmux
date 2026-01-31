from jmux.awaitable import AwaitableValue
from jmux.demux import JMux


class TestModelJMux(JMux):
    name: AwaitableValue[str]
    age: AwaitableValue[int]
