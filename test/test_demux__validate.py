# import pytest
# from jmux.demux import JMux
# from jmux.types import AwaitableValue
# from pydantic import BaseModel


# @pytest.mark.anyio
# async def test_json_demux__validate_pydantic():
#     class SimpleJMux(JMux):
#         key_int: AwaitableValue[int]

#     class SimplePydantic(BaseModel):
#         key_int: int

#     conforms = SimpleJMux.conforms_to(SimplePydantic)
#     assert conforms is True, "JMux should conform to the Pydantic model"
