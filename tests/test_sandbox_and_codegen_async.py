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


@pytest.mark.asyncio
async def test_codegen_import_template_as_module() -> None:
    """Test {% import 'template' as t %} generates correct async code."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro hello(name) %}Hello {{ name }}!{% endmacro %}",
                "main.html": "{% import 'macros.html' as m %}{{ m.hello('World') }}",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "Hello World!"


@pytest.mark.asyncio
async def test_codegen_import_with_context() -> None:
    """Test {% import 'template' as t with context %} passes context correctly."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro greet() %}Hello {{ name }}!{% endmacro %}",
                "main.html": "{% import 'macros.html' as m with context %}{{ m.greet() }}",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async(name="Context") == "Hello Context!"


@pytest.mark.asyncio
async def test_codegen_from_import_named_macro() -> None:
    """Test {% from 'template' import macro %} generates correct async code."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": (
                    "{% macro hello(name) %}Hello {{ name }}!{% endmacro %}"
                    "{% macro goodbye(name) %}Goodbye {{ name }}!{% endmacro %}"
                ),
                "main.html": "{% from 'macros.html' import hello %}{{ hello('World') }}",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "Hello World!"


@pytest.mark.asyncio
async def test_codegen_from_import_with_alias() -> None:
    """Test {% from 'template' import macro as alias %} works correctly."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro hello(name) %}Hello {{ name }}!{% endmacro %}",
                "main.html": "{% from 'macros.html' import hello as greet %}{{ greet('Alias') }}",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "Hello Alias!"


@pytest.mark.asyncio
async def test_codegen_from_import_multiple_macros() -> None:
    """Test {% from 'template' import a, b %} imports multiple macros."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": (
                    "{% macro hello(name) %}Hello {{ name }}{% endmacro %}"
                    "{% macro goodbye(name) %}Goodbye {{ name }}{% endmacro %}"
                ),
                "main.html": "{% from 'macros.html' import hello, goodbye %}{{ hello('A') }} {{ goodbye('B') }}",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "Hello A Goodbye B"


@pytest.mark.asyncio
async def test_codegen_from_import_with_context() -> None:
    """Test {% from 'template' import macro with context %} passes context."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro greet() %}Hello {{ name }}!{% endmacro %}",
                "main.html": "{% from 'macros.html' import greet with context %}{{ greet() }}",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async(name="WithContext") == "Hello WithContext!"


@pytest.mark.asyncio
async def test_codegen_nested_import_in_included_template() -> None:
    """Test import inside an included template works correctly."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro hello(name) %}Hello {{ name }}!{% endmacro %}",
                "partial.html": "{% import 'macros.html' as m %}{{ m.hello(name) }}",
                "main.html": "{% include 'partial.html' %}",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async(name="Nested") == "Hello Nested!"


# ============================================================================
# Complex codegen test cases
# ============================================================================


@pytest.mark.asyncio
async def test_codegen_multiple_imports_same_template() -> None:
    """Test multiple import statements in the same template."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros_a.html": "{% macro a() %}A{% endmacro %}",
                "macros_b.html": "{% macro b() %}B{% endmacro %}",
                "main.html": (
                    "{% import 'macros_a.html' as ma %}"
                    "{% import 'macros_b.html' as mb %}"
                    "{{ ma.a() }}{{ mb.b() }}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "AB"


@pytest.mark.asyncio
async def test_codegen_import_with_extends_and_blocks() -> None:
    """Test import inside a template that extends another."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro badge(text) %}[{{ text }}]{% endmacro %}",
                "base.html": "Header {% block content %}base{% endblock %} Footer",
                "child.html": (
                    "{% extends 'base.html' %}"
                    "{% import 'macros.html' as m %}"
                    "{% block content %}{{ m.badge('child') }}{% endblock %}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("child.html")
    assert await tmpl.render_async() == "Header [child] Footer"


@pytest.mark.asyncio
async def test_codegen_macro_calling_other_macro() -> None:
    """Test macros that call other macros from the same import."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": (
                    "{% macro inner(x) %}<{{ x }}>{% endmacro %}"
                    "{% macro outer(x) %}[{{ inner(x) }}]{% endmacro %}"
                ),
                "main.html": "{% import 'macros.html' as m %}{{ m.outer('test') }}",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "[<test>]"


@pytest.mark.asyncio
async def test_codegen_cross_import_macro_calls() -> None:
    """Test macros from one import calling macros from another via context."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "utils.html": "{% macro wrap(content) %}[{{ content }}]{% endmacro %}",
                "formatters.html": (
                    "{% macro format(text) %}{{ wrap(text) }}{% endmacro %}"
                ),
                "main.html": (
                    "{% from 'utils.html' import wrap %}"
                    "{% import 'formatters.html' as fmt with context %}"
                    "{{ fmt.format('hello') }}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "[hello]"


@pytest.mark.asyncio
async def test_codegen_deeply_nested_inheritance_with_imports() -> None:
    """Test deep template inheritance chain with imports at each level."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro tag(t, c) %}<{{ t }}>{{ c }}</{{ t }}>{% endmacro %}",
                "level0.html": "{% block content %}L0{% endblock %}",
                "level1.html": (
                    "{% extends 'level0.html' %}"
                    "{% import 'macros.html' as m %}"
                    "{% block content %}{{ m.tag('div', 'L1') }}{% endblock %}"
                ),
                "level2.html": (
                    "{% extends 'level1.html' %}"
                    "{% block content %}{{ m.tag('span', 'L2') }}{% endblock %}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("level2.html")
    assert await tmpl.render_async() == "<span>L2</span>"


@pytest.mark.asyncio
async def test_codegen_dynamic_import_template_name() -> None:
    """Test import with dynamic template name from variable."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros_en.html": "{% macro greet() %}Hello{% endmacro %}",
                "macros_es.html": "{% macro greet() %}Hola{% endmacro %}",
                "main.html": "{% import lang_file as m %}{{ m.greet() }}!",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async(lang_file="macros_en.html") == "Hello!"
    assert await tmpl.render_async(lang_file="macros_es.html") == "Hola!"


@pytest.mark.asyncio
async def test_codegen_import_inside_macro() -> None:
    """Test that imports work correctly when used inside macro definitions."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "helpers.html": "{% macro double(x) %}{{ x }}{{ x }}{% endmacro %}",
                "main.html": (
                    "{% import 'helpers.html' as h %}"
                    "{% macro repeat(text) %}{{ h.double(text) }}{% endmacro %}"
                    "{{ repeat('ab') }}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "abab"


@pytest.mark.asyncio
async def test_codegen_import_with_loop() -> None:
    """Test import used inside a for loop."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro item(x) %}[{{ x }}]{% endmacro %}",
                "main.html": (
                    "{% import 'macros.html' as m %}"
                    "{% for i in items %}{{ m.item(i) }}{% endfor %}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async(items=[1, 2, 3]) == "[1][2][3]"


@pytest.mark.asyncio
async def test_codegen_import_with_conditional() -> None:
    """Test import used inside conditional blocks."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro show(x) %}{{ x }}{% endmacro %}",
                "main.html": (
                    "{% import 'macros.html' as m %}"
                    "{% if show_it %}{{ m.show('yes') }}{% else %}no{% endif %}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async(show_it=True) == "yes"
    assert await tmpl.render_async(show_it=False) == "no"


@pytest.mark.asyncio
async def test_codegen_mixed_import_and_from_import() -> None:
    """Test both import and from-import in the same template."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": (
                    "{% macro a() %}A{% endmacro %}"
                    "{% macro b() %}B{% endmacro %}"
                    "{% macro c() %}C{% endmacro %}"
                ),
                "main.html": (
                    "{% import 'macros.html' as m %}"
                    "{% from 'macros.html' import b %}"
                    "{{ m.a() }}{{ b() }}{{ m.c() }}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "ABC"


@pytest.mark.asyncio
async def test_codegen_import_with_set_and_namespace() -> None:
    """Test import combined with set statements and namespace."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro add(a, b) %}{{ a + b }}{% endmacro %}",
                "main.html": (
                    "{% import 'macros.html' as m %}"
                    "{% set ns = namespace(total=0) %}"
                    "{% set ns.total = m.add(1, 2) %}"
                    "Total: {{ ns.total }}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "Total: 3"


@pytest.mark.asyncio
async def test_codegen_include_with_import_in_included() -> None:
    """Test include where the included template has imports."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro x() %}X{% endmacro %}",
                "partial.html": "{% import 'macros.html' as m %}P{{ m.x() }}P",
                "main.html": "M{% include 'partial.html' %}M",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "MPXPM"


@pytest.mark.asyncio
async def test_codegen_multiple_renders_same_template() -> None:
    """Test that imports work correctly across multiple renders (caching)."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro greet(name) %}Hi {{ name }}{% endmacro %}",
                "main.html": "{% import 'macros.html' as m %}{{ m.greet(name) }}",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async(name="Alice") == "Hi Alice"
    assert await tmpl.render_async(name="Bob") == "Hi Bob"
    assert await tmpl.render_async(name="Charlie") == "Hi Charlie"


@pytest.mark.asyncio
async def test_codegen_sandbox_with_complex_imports() -> None:
    """Test sandboxed environment handles complex import scenarios."""
    env = AsyncSandboxedEnvironment(
        loader=DictLoader(
            {
                "utils.html": "{% macro safe(x) %}[{{ x }}]{% endmacro %}",
                "formatters.html": (
                    "{% macro fmt(items) %}"
                    "{% for i in items %}{{ safe(i) }}{% endfor %}"
                    "{% endmacro %}"
                ),
                "main.html": (
                    "{% from 'utils.html' import safe %}"
                    "{% import 'formatters.html' as f with context %}"
                    "{{ f.fmt(data) }}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async(data=[1, 2, 3]) == "[1][2][3]"


@pytest.mark.asyncio
async def test_codegen_import_with_recursive_macro() -> None:
    """Test imported macro that calls itself recursively."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": (
                    "{% macro tree(items, depth=0) %}"
                    "{% for item in items %}"
                    "{{ '  ' * depth }}{{ item.name }}\n"
                    "{% if item.children %}{{ tree(item.children, depth + 1) }}{% endif %}"
                    "{% endfor %}"
                    "{% endmacro %}"
                ),
                "main.html": "{% import 'macros.html' as m %}{{ m.tree(data) }}",
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    data = [
        {"name": "root", "children": [
            {"name": "child1", "children": []},
            {"name": "child2", "children": [
                {"name": "grandchild", "children": []}
            ]}
        ]}
    ]
    result = await tmpl.render_async(data=data)
    assert "root" in result
    assert "  child1" in result
    assert "  child2" in result
    assert "    grandchild" in result


@pytest.mark.asyncio
async def test_codegen_import_with_caller() -> None:
    """Test imported macro using caller()."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": (
                    "{% macro wrapper() %}"
                    "<wrapper>{{ caller() }}</wrapper>"
                    "{% endmacro %}"
                ),
                "main.html": (
                    "{% import 'macros.html' as m %}"
                    "{% call m.wrapper() %}content{% endcall %}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "<wrapper>content</wrapper>"


@pytest.mark.asyncio
async def test_codegen_from_import_nonexistent_macro() -> None:
    """Test from-import of a macro that doesn't exist renders as undefined."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro exists() %}yes{% endmacro %}",
                "main.html": (
                    "{% from 'macros.html' import nonexistent %}"
                    "{{ nonexistent() if nonexistent is defined else 'undefined' }}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("main.html")
    assert await tmpl.render_async() == "undefined"


@pytest.mark.asyncio
async def test_codegen_import_with_scoped_block() -> None:
    """Test import inside a scoped block."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros.html": "{% macro render(x) %}{{ x }}{% endmacro %}",
                "base.html": "{% block content scoped %}{% endblock %}",
                "child.html": (
                    "{% extends 'base.html' %}"
                    "{% block content %}"
                    "{% import 'macros.html' as m %}"
                    "{{ m.render(value) }}"
                    "{% endblock %}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("child.html")
    assert await tmpl.render_async(value="scoped") == "scoped"


@pytest.mark.asyncio
async def test_codegen_chained_extends_with_imports_at_each_level() -> None:
    """Test chained extends where each level imports different macros."""
    env = AsyncEnvironment(
        loader=DictLoader(
            {
                "macros_a.html": "{% macro a() %}A{% endmacro %}",
                "macros_b.html": "{% macro b() %}B{% endmacro %}",
                "macros_c.html": "{% macro c() %}C{% endmacro %}",
                "base.html": (
                    "{% import 'macros_a.html' as ma %}"
                    "{{ ma.a() }}{% block content %}{% endblock %}"
                ),
                "middle.html": (
                    "{% extends 'base.html' %}"
                    "{% import 'macros_b.html' as mb %}"
                    "{% block content %}{{ mb.b() }}{% block inner %}{% endblock %}{% endblock %}"
                ),
                "child.html": (
                    "{% extends 'middle.html' %}"
                    "{% import 'macros_c.html' as mc %}"
                    "{% block inner %}{{ mc.c() }}{% endblock %}"
                ),
            }
        )
    )

    tmpl = await env.get_template_async("child.html")
    assert await tmpl.render_async() == "ABC"
