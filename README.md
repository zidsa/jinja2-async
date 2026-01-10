## jinja2-async

`jinja2-async` is a small wrapper around [Jinja2](https://palletsprojects.com/p/jinja/) that provides async-aware loaders and an async-first environment API.

### Install

```bash
python -m pip install jinja2-async
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

