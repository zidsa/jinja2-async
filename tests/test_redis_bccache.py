"""Tests for Redis bytecode cache."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from jinja2.bccache import Bucket


@pytest.fixture
def mock_bucket():
    """Create a mock bucket for testing."""
    bucket = MagicMock(spec=Bucket)
    bucket.key = "test_template_key"
    bucket.bytecode_to_string.return_value = b"compiled_bytecode_data"
    return bucket


@pytest.mark.asyncio
async def test_redis_cache_load_bytecode_async_hit(mock_bucket):
    """Test loading bytecode from Redis when it exists."""
    pytest.importorskip("redis")

    from jinja2_async.bccache import RedisBytecodeCache

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=b"cached_bytecode")

    cache = RedisBytecodeCache(client=mock_client, prefix="test:")

    await cache.load_bytecode_async(mock_bucket)

    mock_client.get.assert_called_once_with("test:test_template_key")
    mock_bucket.bytecode_from_string.assert_called_once_with(b"cached_bytecode")


@pytest.mark.asyncio
async def test_redis_cache_load_bytecode_async_miss(mock_bucket):
    """Test loading bytecode from Redis when it doesn't exist."""
    pytest.importorskip("redis")

    from jinja2_async.bccache import RedisBytecodeCache

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)

    cache = RedisBytecodeCache(client=mock_client, prefix="test:")

    await cache.load_bytecode_async(mock_bucket)

    mock_client.get.assert_called_once_with("test:test_template_key")
    mock_bucket.bytecode_from_string.assert_not_called()


@pytest.mark.asyncio
async def test_redis_cache_dump_bytecode_async(mock_bucket):
    """Test dumping bytecode to Redis."""
    pytest.importorskip("redis")

    from jinja2_async.bccache import RedisBytecodeCache

    mock_client = AsyncMock()
    mock_client.set = AsyncMock()

    cache = RedisBytecodeCache(client=mock_client, prefix="test:")

    await cache.dump_bytecode_async(mock_bucket)

    mock_client.set.assert_called_once_with(
        "test:test_template_key", b"compiled_bytecode_data"
    )


@pytest.mark.asyncio
async def test_redis_cache_dump_bytecode_async_with_ttl(mock_bucket):
    """Test dumping bytecode to Redis with TTL."""
    pytest.importorskip("redis")

    from jinja2_async.bccache import RedisBytecodeCache

    mock_client = AsyncMock()
    mock_client.setex = AsyncMock()

    cache = RedisBytecodeCache(client=mock_client, prefix="test:", ttl=3600)

    await cache.dump_bytecode_async(mock_bucket)

    mock_client.setex.assert_called_once_with(
        "test:test_template_key", 3600, b"compiled_bytecode_data"
    )


@pytest.mark.asyncio
async def test_redis_cache_clear_async():
    """Test clearing all cached bytecode."""
    pytest.importorskip("redis")

    from jinja2_async.bccache import RedisBytecodeCache

    mock_client = AsyncMock()
    # Simulate scan returning keys then completing
    mock_client.scan = AsyncMock(
        side_effect=[
            (123, [b"test:key1", b"test:key2"]),
            (0, [b"test:key3"]),
        ]
    )
    mock_client.delete = AsyncMock()

    cache = RedisBytecodeCache(client=mock_client, prefix="test:")

    await cache.clear_async()

    assert mock_client.scan.call_count == 2
    assert mock_client.delete.call_count == 2


@pytest.mark.asyncio
async def test_redis_cache_close():
    """Test closing the Redis connection."""
    pytest.importorskip("redis")

    from jinja2_async.bccache import RedisBytecodeCache

    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()

    # When client is provided, cache doesn't own it
    cache1 = RedisBytecodeCache(client=mock_client)
    await cache1.close()
    mock_client.aclose.assert_not_called()


@pytest.mark.asyncio
async def test_redis_cache_connection_error_handling(mock_bucket):
    """Test that connection errors are handled gracefully."""
    pytest.importorskip("redis")

    from jinja2_async.bccache import RedisBytecodeCache

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=ConnectionError("Connection refused"))
    mock_client.set = AsyncMock(side_effect=ConnectionError("Connection refused"))

    cache = RedisBytecodeCache(client=mock_client)

    # Should not raise, just silently fail
    await cache.load_bytecode_async(mock_bucket)
    await cache.dump_bytecode_async(mock_bucket)


@pytest.mark.asyncio
async def test_redis_cache_with_environment():
    """Test Redis cache integration with AsyncEnvironment."""
    pytest.importorskip("redis")

    from jinja2_async import AsyncEnvironment, DictLoader
    from jinja2_async.bccache import RedisBytecodeCache

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)  # Cache miss
    mock_client.set = AsyncMock()

    cache = RedisBytecodeCache(client=mock_client, prefix="templates:")

    env = AsyncEnvironment(
        loader=DictLoader({"test.html": "Hello {{ name }}!"}),
        bytecode_cache=cache,
        cache_size=0,  # Disable template cache to hit bytecode cache
    )

    # First render - should compile and cache
    template = await env.get_template_async("test.html")
    result = await template.render_async(name="World")
    assert result == "Hello World!"

    # Verify cache was written
    assert mock_client.set.called


def test_redis_cache_make_key():
    """Test key generation with prefix."""
    pytest.importorskip("redis")

    from jinja2_async.bccache import RedisBytecodeCache

    mock_client = AsyncMock()

    cache = RedisBytecodeCache(client=mock_client, prefix="myapp:jinja:")

    mock_bucket = MagicMock()
    mock_bucket.key = "template_hash_123"

    key = cache._make_key(mock_bucket)
    assert key == "myapp:jinja:template_hash_123"


def test_redis_availability_flag():
    """Test that REDIS_AVAILABLE flag is set."""
    from jinja2_async import bccache

    assert hasattr(bccache, "REDIS_AVAILABLE")
    # If redis is installed, it should be True
    try:
        import redis.asyncio  # noqa: F401

        assert bccache.REDIS_AVAILABLE is True
    except ImportError:
        assert bccache.REDIS_AVAILABLE is False
