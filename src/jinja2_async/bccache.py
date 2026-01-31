import typing as t

from jinja2.bccache import Bucket, BytecodeCache
from jinja2.bccache import FileSystemBytecodeCache as JinjaFileSystemBytecodeCache
from jinja2.bccache import MemcachedBytecodeCache as JinjaMemcachedBytecodeCache

if t.TYPE_CHECKING:
    from .environment import AsyncEnvironment


class AsyncBytecodeCache(BytecodeCache):
    async def load_bytecode_async(self, bucket: Bucket) -> None:
        """Subclasses have to override this method to load bytecode into a
        bucket asynchronously.  If they are not able to find code in the
        cache for the bucket, it must not do anything.
        Unless overridden; this copies the behaviour of load_bytecode.
        """
        return self.load_bytecode(bucket)

    async def dump_bytecode_async(self, bucket: Bucket) -> None:
        """Subclasses have to override this method to write the bytecode
        from a bucket back to the cache asynchronously.  If it is unable to
        do so it must not fail silently but raise an exception.
        Unless overridden; this copies the behaviour of dump_bytecode.
        """
        return self.dump_bytecode(bucket)

    async def get_bucket_async(
        self,
        environment: "AsyncEnvironment",
        name: str,
        filename: str | None,
        source: str,
    ) -> Bucket:
        """Asynchronously return a cache bucket for the given template.  All
        arguments are mandatory but filename may be `None`.
        """
        key = self.get_cache_key(name, filename)
        checksum = self.get_source_checksum(source)
        bucket = Bucket(environment, key, checksum)
        await self.load_bytecode_async(bucket)
        return bucket

    async def set_bucket_async(self, bucket: Bucket) -> None:
        """Asynchronously put the bucket into the cache."""
        await self.dump_bytecode_async(bucket)


class FileSystemBytecodeCache(JinjaFileSystemBytecodeCache, AsyncBytecodeCache):
    pass


class MemcachedBytecodeCache(JinjaMemcachedBytecodeCache, AsyncBytecodeCache):
    pass


# =============================================================================
# Redis Bytecode Cache (optional dependency)
# =============================================================================

try:
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True

    class RedisBytecodeCache(AsyncBytecodeCache):
        """Async bytecode cache using Redis.

        Stores compiled template bytecode in Redis for fast retrieval
        across multiple processes or servers.

        Args:
            client: An async Redis client instance (redis.asyncio.Redis).
                If not provided, connection parameters must be supplied.
            host: Redis server hostname (default: "localhost").
            port: Redis server port (default: 6379).
            db: Redis database number (default: 0).
            password: Redis authentication password (optional).
            prefix: Key prefix for all cached templates (default: "jinja2:").
            timeout: Connection timeout in seconds (default: 5.0).
            ttl: Time-to-live for cached bytecode in seconds (optional).
                If None, cached bytecode never expires.

        Example:
            # Using connection parameters
            cache = RedisBytecodeCache(
                host="localhost",
                port=6379,
                prefix="myapp:templates:",
                ttl=3600,  # 1 hour
            )
            env = AsyncEnvironment(bytecode_cache=cache)

            # Using existing client
            import redis.asyncio as redis
            client = redis.Redis(host="localhost", port=6379)
            cache = RedisBytecodeCache(client=client)
            env = AsyncEnvironment(bytecode_cache=cache)
        """

        def __init__(
            self,
            client: "aioredis.Redis | None" = None,
            host: str = "localhost",
            port: int = 6379,
            db: int = 0,
            password: str | None = None,
            prefix: str = "jinja2:",
            timeout: float = 5.0,
            ttl: int | None = None,
        ) -> None:
            super().__init__()
            self.prefix = prefix
            self.ttl = ttl
            self._owns_client = client is None

            if client is not None:
                self._client = client
            else:
                self._client = aioredis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    socket_timeout=timeout,
                    socket_connect_timeout=timeout,
                )

        def _make_key(self, bucket: Bucket) -> str:
            """Generate a Redis key for the given bucket."""
            return f"{self.prefix}{bucket.key}"

        async def load_bytecode_async(self, bucket: Bucket) -> None:
            """Load bytecode from Redis into the bucket."""
            key = self._make_key(bucket)
            try:
                data = await self._client.get(key)
                if data is not None:
                    bucket.bytecode_from_string(data)
            except Exception:
                # Silently fail on connection errors - cache misses are acceptable
                pass

        async def dump_bytecode_async(self, bucket: Bucket) -> None:
            """Dump bytecode from the bucket to Redis."""
            key = self._make_key(bucket)
            data = bucket.bytecode_to_string()
            try:
                if self.ttl is not None:
                    await self._client.setex(key, self.ttl, data)
                else:
                    await self._client.set(key, data)
            except Exception:
                # Silently fail on connection errors
                pass

        def load_bytecode(self, bucket: Bucket) -> None:
            """Synchronous load - not recommended but available for compatibility."""
            # For sync access, we need to create a sync client
            import redis

            sync_client = redis.Redis(
                host=self._client.connection_pool.connection_kwargs.get(
                    "host", "localhost"
                ),
                port=self._client.connection_pool.connection_kwargs.get("port", 6379),
                db=self._client.connection_pool.connection_kwargs.get("db", 0),
                password=self._client.connection_pool.connection_kwargs.get("password"),
            )
            try:
                key = self._make_key(bucket)
                data = sync_client.get(key)
                if data is not None:
                    bucket.bytecode_from_string(data)
            except Exception:
                pass
            finally:
                sync_client.close()

        def dump_bytecode(self, bucket: Bucket) -> None:
            """Synchronous dump - not recommended but available for compatibility."""
            import redis

            sync_client = redis.Redis(
                host=self._client.connection_pool.connection_kwargs.get(
                    "host", "localhost"
                ),
                port=self._client.connection_pool.connection_kwargs.get("port", 6379),
                db=self._client.connection_pool.connection_kwargs.get("db", 0),
                password=self._client.connection_pool.connection_kwargs.get("password"),
            )
            try:
                key = self._make_key(bucket)
                data = bucket.bytecode_to_string()
                if self.ttl is not None:
                    sync_client.setex(key, self.ttl, data)
                else:
                    sync_client.set(key, data)
            except Exception:
                pass
            finally:
                sync_client.close()

        async def clear_async(self) -> None:
            """Clear all cached bytecode with the configured prefix."""
            try:
                pattern = f"{self.prefix}*"
                cursor = 0
                while True:
                    cursor, keys = await self._client.scan(
                        cursor=cursor, match=pattern, count=100
                    )
                    if keys:
                        await self._client.delete(*keys)
                    if cursor == 0:
                        break
            except Exception:
                pass

        async def close(self) -> None:
            """Close the Redis connection if owned by this cache."""
            if self._owns_client:
                await self._client.aclose()

except ImportError:
    REDIS_AVAILABLE = False
    RedisBytecodeCache = None  # type: ignore[misc, assignment]
