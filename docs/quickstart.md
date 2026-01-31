## Quickstart

### Installation

Install from PyPI:

```bash
python -m pip install jinja2-async
```

#### Optional Dependencies

```bash
# Database loaders
pip install jinja2-async[sqlalchemy]  # SQLAlchemy async support
pip install jinja2-async[peewee]      # Peewee ORM support
pip install jinja2-async[django]      # Django ORM support
pip install jinja2-async[influxdb]    # InfluxDB support

# Bytecode cache backends
pip install jinja2-async[redis]       # Redis bytecode cache

# Install all database loaders
pip install jinja2-async[databases]

# Install everything
pip install jinja2-async[all]
```

### Basic usage

Use `jinja2_async.AsyncEnvironment` with any of the async-capable loaders from `jinja2_async.loaders`.

Example with a filesystem loader:

```python
import asyncio

from jinja2_async import AsyncEnvironment, FileSystemLoader


async def main() -> None:
    env = AsyncEnvironment(loader=FileSystemLoader("templates"))

    # Note: AsyncEnvironment intentionally aliases `get_template` to an async
    # method, so it returns an awaitable.
    tmpl = await env.get_template("hello.html")
    rendered = await tmpl.render_async(name="World")
    print(rendered)


asyncio.run(main())
```

### Async function loader

If you'd like to resolve templates dynamically, `jinja2_async.FunctionLoader` supports an async `load_func` as well:

```python
import asyncio

from jinja2_async import AsyncEnvironment, FunctionLoader


async def load_template(name: str) -> str | None:
    if name == "hello.txt":
        return "Hello {{ name }}!"
    return None


async def main() -> None:
    env = AsyncEnvironment(loader=FunctionLoader(load_template))
    tmpl = await env.get_template("hello.txt")
    print(await tmpl.render_async(name="Async"))


asyncio.run(main())
```

### Database Loaders

#### SQLAlchemy Loader

Load templates from a database using SQLAlchemy's async support:

```python
import asyncio

from sqlalchemy import String, Text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from jinja2_async import AsyncEnvironment, SQLAlchemyLoader, SQLAlchemyTemplateBase


# Define your template model
class Template(SQLAlchemyTemplateBase):
    __tablename__ = "templates"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)


async def main() -> None:
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    loader = SQLAlchemyLoader(session_factory=session_factory, model=Template)
    env = AsyncEnvironment(loader=loader)

    tmpl = await env.get_template("email/welcome.html")
    print(await tmpl.render_async(user="Alice"))


asyncio.run(main())
```

#### Peewee Loader

Load templates using Peewee ORM (sync, wrapped for async compatibility):

```python
import asyncio

from peewee import SqliteDatabase

from jinja2_async import AsyncEnvironment, PeeweeLoader, PeeweeTemplateModel


db = SqliteDatabase("templates.db")


class Template(PeeweeTemplateModel):
    class Meta:
        database = db
        table_name = "templates"


async def main() -> None:
    loader = PeeweeLoader(model=Template)
    env = AsyncEnvironment(loader=loader)

    tmpl = await env.get_template("hello.html")
    print(await tmpl.render_async(name="World"))


asyncio.run(main())
```

#### Django Loader

Load templates from Django ORM (requires Django 4.1+ for async support):

```python
# models.py
from jinja2_async import DjangoTemplateModel


class Template(DjangoTemplateModel):
    class Meta:
        db_table = "jinja_templates"


# views.py
from jinja2_async import AsyncEnvironment, DjangoLoader

from .models import Template


async def render_template(request):
    loader = DjangoLoader(model=Template)
    env = AsyncEnvironment(loader=loader)

    tmpl = await env.get_template("email/notification.html")
    return await tmpl.render_async(user=request.user)
```

#### InfluxDB Loader

Load templates from InfluxDB (useful for versioned/time-series template storage):

```python
import asyncio

from jinja2_async import AsyncEnvironment, InfluxDBLoader


async def main() -> None:
    loader = InfluxDBLoader(
        url="http://localhost:8086",
        token="my-token",
        org="my-org",
        bucket="templates",
        measurement="jinja_templates",
    )
    env = AsyncEnvironment(loader=loader)

    tmpl = await env.get_template("report.html")
    print(await tmpl.render_async(data=report_data))


asyncio.run(main())
```

### Redis Bytecode Cache

Cache compiled templates in Redis for faster loading across processes:

```python
import asyncio

from jinja2_async import AsyncEnvironment, FileSystemLoader, RedisBytecodeCache


async def main() -> None:
    # Create Redis bytecode cache
    cache = RedisBytecodeCache(
        host="localhost",
        port=6379,
        prefix="myapp:templates:",
        ttl=3600,  # Cache for 1 hour
    )

    env = AsyncEnvironment(
        loader=FileSystemLoader("templates"),
        bytecode_cache=cache,
    )

    # First load compiles and caches
    tmpl = await env.get_template("hello.html")
    print(await tmpl.render_async(name="World"))

    # Subsequent loads use cached bytecode
    tmpl2 = await env.get_template("hello.html")
    print(await tmpl2.render_async(name="Cache"))

    # Clean up
    await cache.close()


asyncio.run(main())
```

You can also use an existing Redis client:

```python
import redis.asyncio as redis

from jinja2_async import RedisBytecodeCache


client = redis.Redis(host="localhost", port=6379)
cache = RedisBytecodeCache(client=client, prefix="app:")
```

