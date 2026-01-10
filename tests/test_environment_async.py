import inspect

import pytest
from jinja2 import Template
from jinja2.exceptions import TemplateNotFound, TemplatesNotFound

from jinja2_async import AsyncEnvironment, FunctionLoader


@pytest.mark.asyncio
async def test_get_template_alias_returns_awaitable_and_renders() -> None:
    async def load_func(name: str) -> str | None:
        if name == "hello.txt":
            return "Hello {{ name }}!"
        return None

    env = AsyncEnvironment(loader=FunctionLoader(load_func))

    # AsyncEnvironment intentionally aliases sync Jinja APIs to async awaitables.
    maybe_awaitable = env.get_template("hello.txt")
    assert inspect.isawaitable(maybe_awaitable)

    tmpl = await maybe_awaitable
    assert isinstance(tmpl, Template)

    rendered = await tmpl.render_async(name="World")
    assert rendered == "Hello World!"


@pytest.mark.asyncio
async def test_get_template_async_raises_template_not_found() -> None:
    env = AsyncEnvironment(loader=FunctionLoader(lambda name: None))

    with pytest.raises(TemplateNotFound) as exc:
        await env.get_template_async("missing.txt")

    assert exc.value.name == "missing.txt"


@pytest.mark.asyncio
async def test_select_template_async_picks_first_available() -> None:
    def load_func(name: str) -> str | None:
        if name == "b.txt":
            return "B"
        return None

    env = AsyncEnvironment(loader=FunctionLoader(load_func))
    tmpl = await env.select_template_async(["a.txt", "b.txt", "c.txt"])
    assert await tmpl.render_async() == "B"


@pytest.mark.asyncio
async def test_select_template_async_raises_templates_not_found() -> None:
    env = AsyncEnvironment(loader=FunctionLoader(lambda name: None))

    with pytest.raises(TemplatesNotFound) as exc:
        await env.select_template_async(["a.txt", "b.txt"])

    assert exc.value.templates == ["a.txt", "b.txt"]
    assert exc.value.name == "b.txt"


@pytest.mark.asyncio
async def test_list_templates_async_filtering_and_argument_validation() -> None:
    env = AsyncEnvironment(
        loader=FunctionLoader(
            lambda name: {"a.html": "A", "b.txt": "B", "c.html": "C"}.get(name)
        )
    )

    # Monkeypatch loader list for this test to validate env filtering logic.
    async def list_templates_async() -> list[str]:
        return ["a.html", "b.txt", "c.html"]

    assert env.loader is not None
    env.loader.list_templates_async = list_templates_async  # type: ignore[method-assign]

    assert await env.list_templates_async(extensions={"html"}) == ["a.html", "c.html"]
    assert await env.list_templates_async(filter_func=lambda n: n.startswith("b")) == [
        "b.txt"
    ]

    with pytest.raises(TypeError):
        await env.list_templates_async(
            extensions={"html"},
            filter_func=lambda n: True,  # pragma: no cover
        )


@pytest.mark.asyncio
async def test_template_is_up_to_date_async_uses_sync_uptodate_callable() -> None:
    calls = 0

    def uptodate() -> bool:
        nonlocal calls
        calls += 1
        return False

    def load_func(name: str):
        if name == "x.txt":
            return "X", None, uptodate
        return None

    env = AsyncEnvironment(loader=FunctionLoader(load_func))
    tmpl = await env.get_template_async("x.txt")
    assert await tmpl.is_up_to_date_async is False
    assert calls == 1


@pytest.mark.asyncio
async def test_template_is_up_to_date_async_awaits_async_uptodate_callable() -> None:
    calls = 0

    async def uptodate_async() -> bool:
        nonlocal calls
        calls += 1
        return True

    def load_func(name: str):
        if name == "x.txt":
            return "X", None, uptodate_async
        return None

    env = AsyncEnvironment(loader=FunctionLoader(load_func))
    tmpl = await env.get_template_async("x.txt")
    assert await tmpl.is_up_to_date_async is True
    assert calls == 1
