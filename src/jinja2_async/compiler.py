import re

from jinja2.compiler import CodeGenerator as JinjaCodeGenerator

_TEMPLATE_CALL_RE = re.compile(
    r"((?:template|parent_template)\s*=\s*)?"
    r"environment\.(get_template|select_template|get_or_select_template)\("
)


class AsyncCodeGenerator(JinjaCodeGenerator):
    def choose_async(self, async_value: str = "async ", sync_value: str = "") -> str:
        return async_value

    def _rewrite(self, s: str) -> str:
        def replace(m: re.Match) -> str:
            assign, method = m.groups()
            if assign:
                return f"{assign}await environment.{method}_async("
            return f"environment.{method}_async("

        return _TEMPLATE_CALL_RE.sub(replace, s)

    def write(self, x: str) -> None:
        super().write(self._rewrite(x))

    def writeline(self, x: str = "", node=None, extra=0) -> None:
        super().writeline(self._rewrite(x), node, extra)
