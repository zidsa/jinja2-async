import pytest
from jinja2.exceptions import TemplateRuntimeError

from jinja2_async import (
    AsyncCodeGenerator,
    AsyncEnvironment,
    AsyncSandboxedEnvironment,
    DictLoader,
)


def test_async_code_generator_choose_async_returns_async_value() -> None:
    """Verify choose_async always returns the async variant to force async codegen."""
    generator = AsyncCodeGenerator.__new__(AsyncCodeGenerator)
    assert generator.choose_async() == "async "
    assert generator.choose_async("ASYNC ", "SYNC ") == "ASYNC "
    assert generator.choose_async(sync_value="ignored") == "async "


@pytest.mark.asyncio
async def test_codegen_extends_and_include_render_async() -> None:
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "base.html": "{% block body %}base{% endblock %}",
                "partial.html": "inc:{{ value }}",
                "child.html": (
                    "{% extends 'base.html' %}"
                    "{% block body %}child({% include 'partial.html' %}){% endblock %}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("child.html")
    assert await tmpl.render_async(value=42) == "child(inc:42)"


@pytest.mark.asyncio
async def test_codegen_include_without_context_uses_default_module_async() -> None:
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "partial.html": "P",
                "main.html": "A{% include 'partial.html' without context %}B",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async(ignored="x") == "APB"


@pytest.mark.asyncio
async def test_codegen_include_ignore_missing_does_not_raise() -> None:
    env = AsyncEnvironment(
        loader=DictLoader(
            {"main.html": "A{% include 'missing.html' ignore missing %}B"}
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "AB"


@pytest.mark.asyncio
async def test_codegen_include_selects_first_available_from_list() -> None:
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "partial.html": "P",
                "main.html": "A{% include ['missing.html', 'partial.html'] %}B",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "APB"


@pytest.mark.asyncio
async def test_codegen_extends_dynamic_parent_name() -> None:
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "base_a.html": "[A:{% block body %}base{% endblock %}]",
                "base_b.html": "[B:{% block body %}base{% endblock %}]",
                "child.html": "{% extends base %}{% block body %}child{% endblock %}",
            }
        )
    )

    tmpl = await env.get_template_async("child.html")
    assert await tmpl.render_async(base="base_a.html") == "[A:child]"
    assert await tmpl.render_async(base="base_b.html") == "[B:child]"


@pytest.mark.asyncio
async def test_codegen_extends_twice_errors() -> None:
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "a.html": "{% block body %}A{% endblock %}",
                "b.html": "{% block body %}B{% endblock %}",
                "bad.html": "{% extends 'a.html' %}{% extends 'b.html' %}",
            }
        )
    )

    with pytest.raises(TemplateRuntimeError):
        tmpl = await env.get_template_async("bad.html")
        await tmpl.render_async()


@pytest.mark.asyncio
async def test_sandboxed_environment_renders_extends_and_include_async() -> None:
    env = AsyncSandboxedEnvironment(
        loader=DictLoader(
            {
                "base.html": "{% block body %}base{% endblock %}",
                "partial.html": "inc:{{ value }}",
                "child.html": (
                    "{% extends 'base.html' %}"
                    "{% block body %}child({% include 'partial.html' %}){% endblock %}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("child.html")
    assert await tmpl.render_async(value=7) == "child(inc:7)"


@pytest.mark.asyncio
async def test_sandbox_include_ignore_missing_does_not_raise() -> None:
    env = AsyncSandboxedEnvironment(
        loader=DictLoader(
            {"main.html": "A{% include 'missing.html' ignore missing %}B"}
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "AB"


@pytest.mark.asyncio
async def test_sandbox_blocks_unsafe_attribute_access() -> None:
    env = AsyncSandboxedEnvironment(
        loader=DictLoader({"unsafe.html": "{{ f.__globals__ }}"}), autoescape=False
    )

    tmpl = await env.get_template_async("unsafe.html")

    # In Jinja's sandbox, unsafe access is blocked and rendered as undefined.
    assert await tmpl.render_async(f=lambda: None) == ""


@pytest.mark.asyncio
async def test_sandbox_blocks_unsafe_loop_range() -> None:
    env = AsyncSandboxedEnvironment(
        loader=DictLoader(
            {"unsafe.html": "{% for i in range(1000000000) %}{{i}}{% endfor %}"}
        ),
        autoescape=False,
    )

    tmpl = await env.get_template_async("unsafe.html")

    with pytest.raises(OverflowError):
        await tmpl.render_async()
