from jinja2.sandbox import SandboxedEnvironment

from .environment import AsyncEnvironment


class AsyncSandboxedEnvironment(SandboxedEnvironment, AsyncEnvironment):
    """A sandboxed environment that supports async template loaders.
    The sandboxed environment works like the regular environment but
    tells the compiler to generate sandboxed code.  Additionally subclasses of
    this environment may override the methods that tell the runtime what
    attributes or functions are safe to access.

    If the template tries to access insecure code a :exc:`SecurityError` is
    raised.  However, also other exceptions may occur during the rendering so
    the caller has to ensure that all exceptions are caught.
    """

    sandboxed = True
