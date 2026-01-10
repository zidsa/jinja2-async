import pytest
from jinja2.bccache import Bucket

from jinja2_async import AsyncBytecodeCache, AsyncEnvironment, DictLoader


class InMemoryAsyncBytecodeCache(AsyncBytecodeCache):
    def __init__(self) -> None:
        super().__init__()
        self._store: dict[str, object] = {}
        self.loads = 0
        self.dumps = 0

    async def load_bytecode_async(self, bucket: Bucket) -> None:
        self.loads += 1
        code = self._store.get(bucket.key)

        if code is not None:
            bucket.code = code

    async def dump_bytecode_async(self, bucket: Bucket) -> None:
        self.dumps += 1
        assert bucket.code is not None
        self._store[bucket.key] = bucket.code


@pytest.mark.asyncio
async def test_loader_uses_async_bytecode_cache_to_skip_recompile() -> None:
    cache = InMemoryAsyncBytecodeCache()
    # Disable the environment-level template cache so we hit the loader twice.
    env = AsyncEnvironment(
        loader=DictLoader({"a.txt": "A={{ a }}"}), bytecode_cache=cache, cache_size=0
    )

    compile_calls = 0
    real_compile = env.compile

    def compile_spy(*args, **kwargs):
        nonlocal compile_calls
        compile_calls += 1
        return real_compile(*args, **kwargs)

    env.compile = compile_spy  # type: ignore[method-assign]

    t1 = await env.get_template_async("a.txt")
    assert await t1.render_async(a=1) == "A=1"

    t2 = await env.get_template_async("a.txt")
    assert await t2.render_async(a=2) == "A=2"

    # First load compiles and dumps into cache. Second load should avoid compile.
    assert compile_calls == 1
    assert cache.dumps == 1
    assert cache.loads == 2
