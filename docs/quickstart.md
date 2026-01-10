## Quickstart

### Installation

Install from PyPI:

```bash
python -m pip install jinja2-async
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

