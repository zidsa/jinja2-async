import pytest
from jinja2.exceptions import TemplateNotFound

from jinja2_async import (
    AsyncEnvironment,
    ChoiceLoader,
    DictLoader,
    FunctionLoader,
    PrefixLoader,
)


@pytest.mark.asyncio
async def test_function_loader_supports_async_load_func_string_return() -> None:
    async def load_func(name: str) -> str | None:
        if name == "x.txt":
            return "X={{ x }}"
        return None

    env = AsyncEnvironment(loader=FunctionLoader(load_func))
    tmpl = await env.get_template_async("x.txt")
    assert await tmpl.render_async(x=42) == "X=42"


@pytest.mark.asyncio
async def test_function_loader_raises_template_not_found() -> None:
    async def load_func(name: str) -> None:
        return None

    loader = FunctionLoader(load_func)
    env = AsyncEnvironment(loader=loader)

    with pytest.raises(TemplateNotFound) as exc:
        await loader.get_source_async(env, "missing.txt")

    assert exc.value.name == "missing.txt"


@pytest.mark.asyncio
async def test_prefix_loader_list_templates_async_prefixes_names() -> None:
    loader = PrefixLoader(
        {
            "a": DictLoader({"one.txt": "1", "two.txt": "2"}),
            "b": DictLoader({"three.txt": "3"}),
        }
    )
    env = AsyncEnvironment(loader=loader)

    names = await env.list_templates_async()
    assert set(names) == {"a/one.txt", "a/two.txt", "b/three.txt"}


@pytest.mark.asyncio
async def test_prefix_loader_translates_template_not_found_name() -> None:
    loader = PrefixLoader({"a": DictLoader({"one.txt": "1"})})
    env = AsyncEnvironment(loader=loader)

    with pytest.raises(TemplateNotFound) as exc:
        await env.get_template_async("a/missing.txt")

    # PrefixLoader should raise for the full prefixed name, not the local name.
    assert exc.value.name == "a/missing.txt"


@pytest.mark.asyncio
async def test_choice_loader_list_templates_async_unions_and_sorts() -> None:
    loader = ChoiceLoader(
        [
            DictLoader({"b.txt": "B", "a.txt": "A"}),
            DictLoader({"c.txt": "C", "a.txt": "A2"}),
        ]
    )
    env = AsyncEnvironment(loader=loader)

    assert await env.list_templates_async() == ["a.txt", "b.txt", "c.txt"]
