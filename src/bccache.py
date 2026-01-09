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
