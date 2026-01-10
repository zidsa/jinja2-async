import os
import typing as t
import weakref
from inspect import iscoroutinefunction

from jinja2 import Environment, Template, Undefined
from jinja2.environment import internalcode
from jinja2.exceptions import (
    TemplateNotFound,
    TemplatesNotFound,
    TemplateSyntaxError,
    UndefinedError,
)

from .compiler import AsyncCodeGenerator

if t.TYPE_CHECKING:
    from .bccache import AsyncBytecodeCache
    from .loaders import AsyncBaseLoader


class AsyncEnvironment(Environment):
    code_generator_class: type["AsyncCodeGenerator"] = AsyncCodeGenerator
    bytecode_cache: t.Optional["AsyncBytecodeCache"]
    template_class: type["AsyncTemplate"]
    loader: t.Optional["AsyncBaseLoader"]

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        kwargs["enable_async"] = True
        super().__init__(*args, **kwargs)

    async def compile_templates_async(
        self,
        target: t.Union[str, "os.PathLike[str]"],
        extensions: t.Collection[str] | None = None,
        filter_func: t.Callable[[str], bool] | None = None,
        zip: str | None = "deflated",
        log_function: t.Callable[[str], None] | None = None,
        ignore_errors: bool = True,
    ) -> None:
        """Asynchronously finds all the templates the loader can find, compiles them
        and stores them in `target`.  If `zip` is `None`, instead of in a
        zipfile, the templates will be stored in a directory.
        By default, a deflate zip algorithm is used. To switch to
        the stored algorithm, `zip` can be set to ``'stored'``.

        `extensions` and `filter_func` are passed to :meth:`list_templates_async`.
        Each template returned will be compiled to the target folder or
        zipfile.

        By default, template compilation errors are ignored.  In case a
        log function is provided, errors are logged.  If you want template
        syntax errors to abort the compilation you can set `ignore_errors`
        to `False` and you will get an exception on syntax errors.
        """
        from jinja2.loaders import ModuleLoader

        if log_function is None:

            def log_function(x: str) -> None:
                pass

        assert log_function is not None
        assert self.loader is not None, "No loader configured."

        def write_file(filename: str, data: str) -> None:
            if zip:
                info = ZipInfo(filename)
                info.external_attr = 0o755 << 16
                zip_file.writestr(info, data)
            else:
                with open(os.path.join(target, filename), "wb") as f:
                    f.write(data.encode("utf8"))

        if zip is not None:
            from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

            zip_file = ZipFile(
                target, "w", dict(deflated=ZIP_DEFLATED, stored=ZIP_STORED)[zip]
            )
            log_function(f"Compiling into Zip archive {target!r}")
        else:
            if not os.path.isdir(target):
                os.makedirs(target)
            log_function(f"Compiling into folder {target!r}")

        try:
            for name in await self.list_templates_async(extensions, filter_func):
                source, filename, _ = await self.loader.get_source_async(self, name)
                try:
                    code = self.compile(source, name, filename, True, True)
                except TemplateSyntaxError as e:
                    if not ignore_errors:
                        raise
                    log_function(f'Could not compile "{name}": {e}')
                    continue

                filename = ModuleLoader.get_module_filename(name)

                write_file(filename, code)
                log_function(f'Compiled "{name}" as {filename}')
        finally:
            if zip:
                zip_file.close()

        log_function("Finished compiling templates")

    async def list_templates_async(
        self,
        extensions: t.Collection[str] | None = None,
        filter_func: t.Callable[[str], bool] | None = None,
    ) -> list[str]:
        """Asynchronously returns a list of templates for this environment.
        This requires that the loader supports the loader's
        :meth:`~BaseLoader.list_templates_async` method.

        If there are other files in the template folder besides the
        actual templates, the returned list can be filtered.  There are two
        ways: either `extensions` is set to a list of file extensions for
        templates, or a `filter_func` can be provided which is a callable that
        is passed a template name and should return `True` if it should end up
        in the result list.

        If the loader does not support that, a :exc:`TypeError` is raised.
        """
        assert self.loader is not None, "No loader configured."
        names = await self.loader.list_templates_async()

        if extensions is not None:
            if filter_func is not None:
                raise TypeError(
                    "either extensions or filter_func can be passed, but not both"
                )

            def filter_func(x: str) -> bool:
                return "." in x and x.rsplit(".", 1)[1] in extensions

        if filter_func is not None:
            names = [name for name in names if filter_func(name)]

        return names

    @internalcode
    async def _load_template_async(
        self,
        name: str,
        globals: t.MutableMapping[str, t.Any] | None,
    ) -> "Template":
        if self.loader is None:
            raise TypeError("no loader for this environment specified")
        cache_key = (weakref.ref(self.loader), name)
        if self.cache is not None:
            template = self.cache.get(cache_key)
            if template is not None and (
                not self.auto_reload or await template.is_up_to_date_async
            ):
                if globals:
                    template.globals.update(globals)

                return template

        template = await self.loader.load_async(self, name, self.make_globals(globals))

        if self.cache is not None:
            self.cache[cache_key] = template
        return template

    @internalcode
    async def get_template_async(
        self,
        name: t.Union[str, "Template"],
        parent: str | None = None,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> "Template":
        """Asynchronously load a template by name with :attr:`loader` and return a
        :class:`Template`. If the template does not exist a
        :exc:`TemplateNotFound` exception is raised.

        :param name: Name of the template to load. When loading
            templates from the filesystem, "/" is used as the path
            separator, even on Windows.
        :param parent: The name of the parent template importing this
            template. :meth:`join_path` can be used to implement name
            transformations with this.
        :param globals: Extend the environment :attr:`globals` with
            these extra variables available for all renders of this
            template. If the template has already been loaded and
            cached, its globals are updated with any new items.
        """
        if isinstance(name, Template):
            return name
        if parent is not None:
            name = self.join_path(name, parent)

        return await self._load_template_async(name, globals)

    @internalcode
    async def select_template_async(
        self,
        names: t.Iterable[t.Union[str, "Template"]],
        parent: str | None = None,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> "Template":
        """Like :meth:`get_template_async`, but asynchronously tries loading
        multiple names. If none of the names can be loaded a
        :exc:`TemplatesNotFound` exception is raised.

        :param names: List of template names to try loading in order.
        :param parent: The name of the parent template importing this
            template. :meth:`join_path` can be used to implement name
            transformations with this.
        :param globals: Extend the environment :attr:`globals` with
            these extra variables available for all renders of this
            template. If the template has already been loaded and
            cached, its globals are updated with any new items.
        """
        if isinstance(names, Undefined):
            names._fail_with_undefined_error()

        if not names:
            raise TemplatesNotFound(
                message="Tried to select from an empty list of templates."
            )

        for name in names:
            if isinstance(name, Template):
                return name
            if parent is not None:
                name = self.join_path(name, parent)
            try:
                return await self._load_template_async(name, globals)
            except (TemplateNotFound, UndefinedError):
                pass
        raise TemplatesNotFound(names)  # type: ignore

    @internalcode
    async def get_or_select_template_async(
        self,
        template_name_or_list: t.Union[str, "Template", list[t.Union[str, "Template"]]],
        parent: str | None = None,
        globals: t.MutableMapping[str, t.Any] | None = None,
    ) -> "Template":
        """Use :meth:`select_template_async` if an iterable of template names
        is given, or :meth:`get_template_async` if one name is given.
        """
        if isinstance(template_name_or_list, (str, Undefined)):
            return await self.get_template_async(template_name_or_list, parent, globals)
        elif isinstance(template_name_or_list, Template):
            return template_name_or_list
        return await self.select_template_async(template_name_or_list, parent, globals)

    # Runtime aliases for async template loading. These intentionally change the
    # call contract compared to Environment (they return awaitables).
    get_template = get_template_async  # type: ignore[assignment]
    select_template = select_template_async  # type: ignore[assignment]
    get_or_select_template = get_or_select_template_async  # type: ignore[assignment]
    list_templates = list_templates_async  # type: ignore[assignment]


class AsyncTemplate(Template):
    environment_class: type[Environment] = AsyncEnvironment
    _uptodate: t.Callable[[], t.Awaitable[bool] | bool] | None

    @property
    async def is_up_to_date_async(self) -> bool:
        """If this variable is `False` there is a newer version available."""
        if self._uptodate is None:
            return True
        if iscoroutinefunction(self._uptodate):
            return await self._uptodate()
        return self._uptodate()


AsyncEnvironment.template_class = AsyncTemplate
