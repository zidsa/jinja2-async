from jinja2.compiler import CodeGenerator as JinjaCodeGenerator
from jinja2.compiler import CompilerExit, Frame, nodes


class CodeGenerator(JinjaCodeGenerator):
    def choose_async_env(
        self, async_value: str = "await ", sync_value: str = ""
    ) -> str:
        return sync_value

    def visit_Extends(self, node: nodes.Extends, frame: Frame) -> None:
        """Calls the extender."""
        if not frame.toplevel:
            self.fail("cannot use extend from a non top-level scope", node.lineno)

        if self.extends_so_far > 0:
            if not self.has_known_extends:
                self.writeline("if parent_template is not None:")
                self.indent()
            self.writeline('raise TemplateRuntimeError("extended multiple times")')

            if self.has_known_extends:
                raise CompilerExit()
            else:
                self.outdent()

        self.writeline(
            f"parent_template = {self.choose_async_env()}environment.get_template(",
            node,
        )
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")
        self.writeline("for name, parent_block in parent_template.blocks.items():")
        self.indent()
        self.writeline("context.blocks.setdefault(name, []).append(parent_block)")
        self.outdent()

        if frame.rootlevel:
            self.has_known_extends = True

        self.extends_so_far += 1

    def visit_Include(self, node: nodes.Include, frame: Frame) -> None:
        """Handles includes."""
        if node.ignore_missing:
            self.writeline("try:")
            self.indent()

        func_name = "get_or_select_template"
        if isinstance(node.template, nodes.Const):
            if isinstance(node.template.value, str):
                func_name = "get_template"
            elif isinstance(node.template.value, (tuple, list)):
                func_name = "select_template"
        elif isinstance(node.template, (nodes.Tuple, nodes.List)):
            func_name = "select_template"

        self.writeline(
            f"template = {self.choose_async_env()}environment.{func_name}(", node
        )
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")
        if node.ignore_missing:
            self.outdent()
            self.writeline("except TemplateNotFound:")
            self.indent()
            self.writeline("pass")
            self.outdent()
            self.writeline("else:")
            self.indent()


class AsyncCodeGenerator(CodeGenerator):
    def choose_async(self, async_value: str = "async ", sync_value: str = "") -> str:
        return async_value  # AsyncEnvironment is always async

    def choose_async_env(
        self, async_value: str = "await ", sync_value: str = ""
    ) -> str:
        return async_value
