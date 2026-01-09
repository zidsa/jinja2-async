from jinja2.sandbox import SandboxedEnvironment

from .environment import AsyncEnvironment


class AsyncSandboxedEnvironment(AsyncEnvironment, SandboxedEnvironment):
    """A sandboxed environment that supports async template loaders."""

    pass
