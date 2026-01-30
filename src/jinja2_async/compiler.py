import re

from jinja2.compiler import CodeGenerator as JinjaCodeGenerator

# Matches template lookup calls with optional assignment prefix or await prefix
# Groups: (1) assignment like "template = ", (2) await prefix, (3) method name
_TEMPLATE_CALL_RE = re.compile(
    r"((?:template|parent_template)\s*=\s*)?"
    r"(await\s+)?"
    r"environment\.(get_template|select_template|get_or_select_template)\("
)

# Matches the closing pattern for import statements ending with ).
# This handles: ", 'template_name')." from _import_common
_IMPORT_CLOSE_RE = re.compile(r"\)\.$")


class AsyncCodeGenerator(JinjaCodeGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Track depth of import-style template calls that need extra closing paren
        self._import_paren_depth = 0

    def choose_async(self, async_value: str = "async ", sync_value: str = "") -> str:
        return async_value

    def _rewrite(self, s: str) -> str:
        def replace(m: re.Match) -> str:
            assign, await_prefix, method = m.groups()
            if assign:
                # Assignment pattern: template = environment.get_template(
                # -> template = await environment.get_template_async(
                return f"{assign}await environment.{method}_async("
            elif await_prefix:
                # Import pattern: await environment.get_template(
                # -> await (await environment.get_template_async(
                # Track that we need to close the extra paren later
                self._import_paren_depth += 1
                return f"await (await environment.{method}_async("
            else:
                # Bare call
                return f"await environment.{method}_async("

        s = _TEMPLATE_CALL_RE.sub(replace, s)

        # Handle closing pattern for import statements: "). at end of string
        # We need to add extra ) to close the (await ...) wrapper
        if self._import_paren_depth > 0 and _IMPORT_CLOSE_RE.search(s):
            s = _IMPORT_CLOSE_RE.sub(")).", s)
            self._import_paren_depth -= 1

        return s

    def write(self, x: str) -> None:
        super().write(self._rewrite(x))

    def writeline(self, x: str = "", node=None, extra=0) -> None:
        super().writeline(self._rewrite(x), node, extra)
