import pytest


@pytest.fixture(params=["asyncio", "trio"])
def anyio_backend(request):
    return request.param
