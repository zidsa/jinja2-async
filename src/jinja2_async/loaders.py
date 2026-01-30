import typing as t
from inspect import iscoroutinefunction

from jinja2.exceptions import TemplateNotFound
from jinja2.loaders import BaseLoader
from jinja2.loaders import ChoiceLoader as JinjaChoiceLoader
from jinja2.loaders import DictLoader as JinjaDictLoader
from jinja2.loaders import FileSystemLoader as JinjaFileSystemLoader
from jinja2.loaders import FunctionLoader as JinjaFunctionLoader
from jinja2.loaders import ModuleLoader as JinjaModuleLoader
from jinja2.loaders import PackageLoader as JinjaPackageLoader
from jinja2.loaders import PrefixLoader as JinjaPrefixLoader
from jinja2.utils import internalcode

if t.TYPE_CHECKING:
    from .environment import AsyncEnvironment, AsyncTemplate


class AsyncBaseLoader(BaseLoader):
    async def get_source_async(
        self, environment: "AsyncEnvironment", template: str
    ) -> tuple[str, str | None, t.Callable[[], t.Awaitable[bool] | bool] | None]:
        """Asynchronously get the template source, filename and reload helper
        for a template.
        It's passed the environment and template name and has to return a
        tuple in the form ``(source, filename, uptodate)`` or raise a
        `TemplateNotFound` error if it can't locate the template.

        The source part of the returned tuple must be the source of the
        template as a string. The filename should be the name of the
        file on the filesystem if it was loaded from there, otherwise
        ``None``. The filename is used by Python for the tracebacks
        if no loader extension is used.

        The last item in the tuple is the `uptodate` function.  If auto
        reloading is enabled it's always called to check if the template
        changed.  No arguments are passed so the function must store the
        old state somewhere (for example in a closure).  If it returns `False`
        the template will be reloaded.
        """
        return self.get_source(environment, template)

    async def list_templates_async(self) -> list[str]:
        """Asynchronously iterates over all templates.  If the loader does
        not support that it should raise a :exc:`TypeError` which is the
        default behavior.
        """
        return self.list_templates()

    async def load_async(
        self,
        environment: "AsyncEnvironment",
        name: str,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> "AsyncTemplate":
        """Asynchronously loads a template.  This method looks up the template
        in the cache or loads one by calling :meth:`get_source_async`.
        Subclasses should not override this method as loaders working on
        collections of other loaders (such as :class:`PrefixLoader` or
        :class:`ChoiceLoader`) will not call this method but
        `get_source_async` directly.
        """
        code = None
        if globals is None:
            globals = {}

        source, filename, uptodate = await self.get_source_async(environment, name)

        bcc = environment.bytecode_cache
        if bcc is not None:
            bucket = await bcc.get_bucket_async(environment, name, filename, source)
            code = bucket.code

        # if we don't have code so far (not cached, no longer up to
        # date) etc. we compile the template
        if code is None:
            code = environment.compile(source, name, filename)

        # if the bytecode cache is available and the bucket doesn't
        # have a code so far, we give the bucket the new code and put
        # it back to the bytecode cache.
        if bcc is not None and bucket.code is None:
            bucket.code = code
            await bcc.set_bucket_async(bucket)

        return environment.template_class.from_code(
            environment, code, globals, uptodate
        )


class FileSystemLoader(JinjaFileSystemLoader, AsyncBaseLoader):
    pass


class PackageLoader(JinjaPackageLoader, AsyncBaseLoader):
    pass


class DictLoader(JinjaDictLoader, AsyncBaseLoader):
    pass


class ModuleLoader(JinjaModuleLoader, AsyncBaseLoader):
    pass


class FunctionLoader(JinjaFunctionLoader, AsyncBaseLoader):
    load_func: t.Callable[
        [str],
        str
        | tuple[str, str | None, t.Callable[[], t.Awaitable[bool] | bool] | None]
        | None
        | t.Awaitable[
            str
            | tuple[str, str | None, t.Callable[[], t.Awaitable[bool] | bool] | None]
            | None
        ],
    ]

    async def get_source_async(
        self, environment: "AsyncEnvironment", template: str
    ) -> tuple[str, str | None, t.Callable[[], t.Awaitable[bool] | bool] | None]:
        if iscoroutinefunction(self.load_func):
            rv = await self.load_func(template)
        else:
            rv = self.load_func(template)

        if rv is None:
            raise TemplateNotFound(template)

        if isinstance(rv, str):
            return rv, None, None

        return rv


class PrefixLoader(JinjaPrefixLoader, AsyncBaseLoader):
    mapping: t.Mapping[str, AsyncBaseLoader]

    if t.TYPE_CHECKING:

        def get_loader(self, template: str) -> tuple[AsyncBaseLoader, str]: ...

    async def get_source_async(
        self, environment: "AsyncEnvironment", template: str
    ) -> tuple[str, str | None, t.Callable[[], t.Awaitable[bool] | bool] | None]:
        rv = self.get_loader(template)

        if rv is None:
            raise TemplateNotFound(template)

        loader, name = rv
        try:
            return await loader.get_source_async(environment, name)
        except TemplateNotFound as e:
            raise TemplateNotFound(template) from e

    @internalcode
    async def load_async(
        self,
        environment: "AsyncEnvironment",
        name: str,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> "AsyncTemplate":
        rv = self.get_loader(name)

        if rv is None:
            raise TemplateNotFound(name)

        loader, local_name = rv
        try:
            return await loader.load_async(environment, local_name, globals)
        except TemplateNotFound as e:
            raise TemplateNotFound(name) from e

    async def list_templates_async(self) -> list[str]:
        result = []
        for prefix, loader in self.mapping.items():
            for template in await loader.list_templates_async():
                result.append(prefix + self.delimiter + template)
        return result


class ChoiceLoader(JinjaChoiceLoader, AsyncBaseLoader):
    loaders: t.Sequence[AsyncBaseLoader]

    async def get_source_async(
        self, environment: "AsyncEnvironment", template: str
    ) -> tuple[str, str | None, t.Callable[[], t.Awaitable[bool] | bool] | None]:
        for loader in self.loaders:
            try:
                return await loader.get_source_async(environment, template)
            except TemplateNotFound:
                pass
        raise TemplateNotFound(template)

    @internalcode
    async def load_async(
        self,
        environment: "AsyncEnvironment",
        name: str,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> "AsyncTemplate":
        for loader in self.loaders:
            try:
                return await loader.load_async(environment, name, globals)
            except TemplateNotFound:
                pass
        raise TemplateNotFound(name)

    async def list_templates_async(self) -> list[str]:
        found = set()
        for loader in self.loaders:
            found.update(await loader.list_templates_async())
        return sorted(found)
