## jinja2-async

`jinja2-async` is a small wrapper around [Jinja2](https://palletsprojects.com/p/jinja/) that provides async-aware loaders and an async-first environment API.

### Install

```bash
python -m pip install jinja2-async
```

#### Optional Dependencies

Install with optional database loaders and caching backends:

```bash
# Database loaders
pip install jinja2-async[sqlalchemy]  # SQLAlchemy async support
pip install jinja2-async[peewee]      # Peewee ORM support
pip install jinja2-async[django]      # Django ORM support
pip install jinja2-async[influxdb]    # InfluxDB support

# Bytecode cache backends
pip install jinja2-async[redis]       # Redis bytecode cache

# Install all optional dependencies
pip install jinja2-async[all]
```

### Basic usage

```python
import asyncio

from jinja2_async import AsyncEnvironment, FileSystemLoader


async def main() -> None:
    env = AsyncEnvironment(loader=FileSystemLoader("templates"))

    # AsyncEnvironment intentionally aliases `get_template` to an async method,
    # so it returns an awaitable.
    tmpl = await env.get_template("hello.html")
    rendered = await tmpl.render_async(name="World")
    print(rendered)


asyncio.run(main())
```

### Documentation

The docs are plain Markdown under `docs/`:

- `docs/index.md`
- `docs/quickstart.md`
- `docs/api.md`

### Changelog

See `CHANGELOG.md`.

