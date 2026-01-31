"""
Database template loaders for jinja2-async.

These loaders require optional dependencies:
- SQLAlchemy: pip install jinja2-async[sqlalchemy]
- Peewee: pip install jinja2-async[peewee]
- Django: pip install jinja2-async[django]
- InfluxDB: pip install jinja2-async[influxdb]
"""

import typing as t
from datetime import UTC, datetime

from jinja2 import Environment
from jinja2.exceptions import TemplateNotFound

from .loaders import AsyncBaseLoader

if t.TYPE_CHECKING:
    from .environment import AsyncEnvironment


# =============================================================================
# SQLAlchemy Loader
# =============================================================================

try:
    from sqlalchemy import DateTime, String, Text, select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

    SQLALCHEMY_AVAILABLE = True

    class SQLAlchemyTemplateBase(DeclarativeBase):
        """Base class for SQLAlchemy template models.

        Users should create their own model inheriting from this base
        with their own __tablename__ and any additional columns.

        Example:
            class Template(SQLAlchemyTemplateBase):
                __tablename__ = "templates"
        """

        name: Mapped[str] = mapped_column(String(255), primary_key=True)
        source: Mapped[str] = mapped_column(Text, nullable=False)
        updated_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(UTC)
        )

    class SQLAlchemyLoader(AsyncBaseLoader):
        """Async template loader for SQLAlchemy.

        Loads templates from a database table using SQLAlchemy's async session.

        Args:
            session_factory: An async callable that returns an AsyncSession.
                Can be an async_sessionmaker or any async context manager factory.
            model: The SQLAlchemy model class representing the template table.
                Must have 'name', 'source', and optionally 'updated_at' columns.
            auto_reload: If True, templates will be checked for updates.

        Example:
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

            engine = create_async_engine("postgresql+asyncpg://...")
            session_factory = async_sessionmaker(engine)

            loader = SQLAlchemyLoader(
                session_factory=session_factory,
                model=Template,
            )
            env = AsyncEnvironment(loader=loader)
        """

        def __init__(
            self,
            session_factory: t.Callable[[], t.AsyncContextManager[AsyncSession]],
            model: type[SQLAlchemyTemplateBase],
            auto_reload: bool = True,
        ) -> None:
            self.session_factory = session_factory
            self.model = model
            self.auto_reload = auto_reload

        async def get_source_async(
            self, environment: "AsyncEnvironment", template: str
        ) -> tuple[str, str | None, t.Callable[[], t.Awaitable[bool]] | None]:
            async with self.session_factory() as session:
                stmt = select(self.model).where(self.model.name == template)
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()

                if row is None:
                    raise TemplateNotFound(template)

                source = row.source
                updated_at = getattr(row, "updated_at", None)

            if self.auto_reload and updated_at is not None:
                last_updated = updated_at

                async def uptodate() -> bool:
                    async with self.session_factory() as sess:
                        stmt = select(self.model.updated_at).where(
                            self.model.name == template
                        )
                        result = await sess.execute(stmt)
                        current = result.scalar_one_or_none()
                        return current == last_updated

                return source, None, uptodate

            return source, None, None

        async def list_templates_async(self) -> list[str]:
            async with self.session_factory() as session:
                stmt = select(self.model.name)
                result = await session.execute(stmt)
                return [row[0] for row in result.fetchall()]

        def get_source(
            self, environment: Environment, template: str
        ) -> tuple[str, str | None, t.Callable[[], bool] | None]:
            raise RuntimeError(
                "SQLAlchemyLoader requires async context. "
                "Use get_source_async() or AsyncEnvironment."
            )

        def list_templates(self) -> list[str]:
            raise TypeError(
                "SQLAlchemyLoader requires async context. "
                "Use list_templates_async()."
            )

except ImportError:
    SQLALCHEMY_AVAILABLE = False
    SQLAlchemyLoader = None  # type: ignore[misc, assignment]
    SQLAlchemyTemplateBase = None  # type: ignore[misc, assignment]


# =============================================================================
# Peewee Loader (sync with async wrapper)
# =============================================================================

try:
    import peewee
    from peewee import DateTimeField, Model, TextField

    PEEWEE_AVAILABLE = True

    class PeeweeTemplateModel(Model):
        """Base class for Peewee template models.

        Users should create their own model inheriting from this
        and configure Meta.database and Meta.table_name.

        Example:
            db = SqliteDatabase('templates.db')

            class Template(PeeweeTemplateModel):
                class Meta:
                    database = db
                    table_name = 'templates'
        """

        name = TextField(primary_key=True)
        source = TextField()
        updated_at = DateTimeField(null=True)

    class PeeweeLoader(AsyncBaseLoader):
        """Template loader for Peewee ORM.

        Note: Peewee is synchronous, so this loader wraps sync calls.
        For true async database access, consider using SQLAlchemy with asyncpg.

        Args:
            model: The Peewee model class representing the template table.
                Must have 'name', 'source', and optionally 'updated_at' fields.
            auto_reload: If True, templates will be checked for updates.

        Example:
            from peewee import SqliteDatabase

            db = SqliteDatabase('templates.db')

            class Template(PeeweeTemplateModel):
                class Meta:
                    database = db

            loader = PeeweeLoader(model=Template)
            env = AsyncEnvironment(loader=loader)
        """

        def __init__(
            self,
            model: type[PeeweeTemplateModel],
            auto_reload: bool = True,
        ) -> None:
            self.model = model
            self.auto_reload = auto_reload

        def get_source(
            self, environment: Environment, template: str
        ) -> tuple[str, str | None, t.Callable[[], bool] | None]:
            try:
                row = self.model.get(self.model.name == template)
            except peewee.DoesNotExist as e:
                raise TemplateNotFound(template) from e

            source = row.source
            updated_at = getattr(row, "updated_at", None)

            if self.auto_reload and updated_at is not None:
                last_updated = updated_at

                def uptodate() -> bool:
                    try:
                        current = self.model.get(self.model.name == template)
                        return current.updated_at == last_updated
                    except peewee.DoesNotExist:
                        return False

                return source, None, uptodate

            return source, None, None

        def list_templates(self) -> list[str]:
            return [row.name for row in self.model.select(self.model.name)]

except ImportError:
    PEEWEE_AVAILABLE = False
    PeeweeLoader = None  # type: ignore[misc, assignment]
    PeeweeTemplateModel = None  # type: ignore[misc, assignment]


# =============================================================================
# Django Loader
# =============================================================================

try:
    from django.conf import settings as django_settings

    # Django requires settings to be configured before defining any Model class
    if not django_settings.configured:
        raise ImportError("Django settings not configured")

    from django.db import models

    DJANGO_AVAILABLE = True

    class DjangoTemplateModel(models.Model):
        """Abstract base class for Django template models.

        Users should create their own concrete model inheriting from this.

        Example:
            class Template(DjangoTemplateModel):
                class Meta:
                    db_table = 'templates'
        """

        name = models.CharField(max_length=255, primary_key=True)
        source = models.TextField()
        updated_at = models.DateTimeField(null=True, blank=True, auto_now=True)

        class Meta:
            abstract = True

    class DjangoLoader(AsyncBaseLoader):
        """Async template loader for Django ORM.

        Uses Django's async ORM support (Django 4.1+) for async queries.

        Args:
            model: The Django model class representing the template table.
                Must have 'name', 'source', and optionally 'updated_at' fields.
            auto_reload: If True, templates will be checked for updates.

        Example:
            class Template(DjangoTemplateModel):
                class Meta:
                    db_table = 'jinja_templates'

            loader = DjangoLoader(model=Template)
            env = AsyncEnvironment(loader=loader)
        """

        def __init__(
            self,
            model: type[DjangoTemplateModel],
            auto_reload: bool = True,
        ) -> None:
            self.model = model
            self.auto_reload = auto_reload

        async def get_source_async(
            self, environment: "AsyncEnvironment", template: str
        ) -> tuple[str, str | None, t.Callable[[], t.Awaitable[bool]] | None]:
            try:
                row = await self.model.objects.aget(name=template)
            except self.model.DoesNotExist as e:
                raise TemplateNotFound(template) from e

            source = row.source
            updated_at = getattr(row, "updated_at", None)

            if self.auto_reload and updated_at is not None:
                last_updated = updated_at
                model = self.model

                async def uptodate() -> bool:
                    try:
                        current = await model.objects.aget(name=template)
                        return current.updated_at == last_updated
                    except model.DoesNotExist:
                        return False

                return source, None, uptodate

            return source, None, None

        async def list_templates_async(self) -> list[str]:
            names = []
            async for row in self.model.objects.values_list("name", flat=True):
                names.append(row)
            return names

        def get_source(
            self, environment: Environment, template: str
        ) -> tuple[str, str | None, t.Callable[[], bool] | None]:
            try:
                row = self.model.objects.get(name=template)
            except self.model.DoesNotExist as e:
                raise TemplateNotFound(template) from e

            source = row.source
            updated_at = getattr(row, "updated_at", None)

            if self.auto_reload and updated_at is not None:
                last_updated = updated_at
                model = self.model

                def uptodate() -> bool:
                    try:
                        current = model.objects.get(name=template)
                        return current.updated_at == last_updated
                    except model.DoesNotExist:
                        return False

                return source, None, uptodate

            return source, None, None

        def list_templates(self) -> list[str]:
            return list(self.model.objects.values_list("name", flat=True))

except ImportError:
    DJANGO_AVAILABLE = False
    DjangoLoader = None  # type: ignore[misc, assignment]
    DjangoTemplateModel = None  # type: ignore[misc, assignment]


# =============================================================================
# InfluxDB Loader
# =============================================================================

try:
    from influxdb_client import InfluxDBClient
    from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

    INFLUXDB_AVAILABLE = True

    class InfluxDBLoader(AsyncBaseLoader):
        """Async template loader for InfluxDB.

        Stores templates as points in an InfluxDB bucket with the template
        name as a tag and source as a field.

        Args:
            url: InfluxDB server URL.
            token: Authentication token.
            org: Organization name.
            bucket: Bucket name where templates are stored.
            measurement: Measurement name for template points (default: "templates").
            auto_reload: If True, templates will be checked for updates.

        Example:
            loader = InfluxDBLoader(
                url="http://localhost:8086",
                token="my-token",
                org="my-org",
                bucket="templates",
            )
            env = AsyncEnvironment(loader=loader)

        Data Model:
            Templates are stored as InfluxDB points:
            - measurement: "templates" (configurable)
            - tag: name=<template_name>
            - field: source=<template_source>
            - timestamp: used for versioning/uptodate checks
        """

        def __init__(
            self,
            url: str,
            token: str,
            org: str,
            bucket: str,
            measurement: str = "templates",
            auto_reload: bool = True,
        ) -> None:
            self.url = url
            self.token = token
            self.org = org
            self.bucket = bucket
            self.measurement = measurement
            self.auto_reload = auto_reload

        async def get_source_async(
            self, environment: "AsyncEnvironment", template: str
        ) -> tuple[str, str | None, t.Callable[[], t.Awaitable[bool]] | None]:
            async with InfluxDBClientAsync(
                url=self.url, token=self.token, org=self.org
            ) as client:
                query_api = client.query_api()
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: -100y)
                    |> filter(fn: (r) => r["_measurement"] == "{self.measurement}")
                    |> filter(fn: (r) => r["name"] == "{template}")
                    |> filter(fn: (r) => r["_field"] == "source")
                    |> last()
                '''
                tables = await query_api.query(query)

                if not tables or not tables[0].records:
                    raise TemplateNotFound(template)

                record = tables[0].records[0]
                source = record.get_value()
                timestamp = record.get_time()

            if self.auto_reload and timestamp is not None:
                last_timestamp = timestamp

                measurement = self.measurement

                async def uptodate() -> bool:
                    async with InfluxDBClientAsync(
                        url=self.url, token=self.token, org=self.org
                    ) as client:
                        query_api = client.query_api()
                        query = f'''
                        from(bucket: "{self.bucket}")
                            |> range(start: -100y)
                            |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                            |> filter(fn: (r) => r["name"] == "{template}")
                            |> filter(fn: (r) => r["_field"] == "source")
                            |> last()
                        '''
                        tables = await query_api.query(query)
                        if not tables or not tables[0].records:
                            return False
                        current_timestamp = tables[0].records[0].get_time()
                        return current_timestamp == last_timestamp

                return source, None, uptodate

            return source, None, None

        async def list_templates_async(self) -> list[str]:
            async with InfluxDBClientAsync(
                url=self.url, token=self.token, org=self.org
            ) as client:
                query_api = client.query_api()
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: -100y)
                    |> filter(fn: (r) => r["_measurement"] == "{self.measurement}")
                    |> filter(fn: (r) => r["_field"] == "source")
                    |> distinct(column: "name")
                '''
                tables = await query_api.query(query)

                names = set()
                for table in tables:
                    for record in table.records:
                        name = record.values.get("name")
                        if name:
                            names.add(name)

                return sorted(names)

        def get_source(
            self, environment: Environment, template: str
        ) -> tuple[str, str | None, t.Callable[[], bool] | None]:
            with InfluxDBClient(
                url=self.url, token=self.token, org=self.org
            ) as client:
                query_api = client.query_api()
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: -100y)
                    |> filter(fn: (r) => r["_measurement"] == "{self.measurement}")
                    |> filter(fn: (r) => r["name"] == "{template}")
                    |> filter(fn: (r) => r["_field"] == "source")
                    |> last()
                '''
                tables = query_api.query(query)

                if not tables or not tables[0].records:
                    raise TemplateNotFound(template)

                record = tables[0].records[0]
                source = record.get_value()
                timestamp = record.get_time()

            if self.auto_reload and timestamp is not None:
                last_timestamp = timestamp
                loader = self
                measurement = self.measurement

                def uptodate() -> bool:
                    with InfluxDBClient(
                        url=loader.url, token=loader.token, org=loader.org
                    ) as client:
                        query_api = client.query_api()
                        query = f'''
                        from(bucket: "{loader.bucket}")
                            |> range(start: -100y)
                            |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                            |> filter(fn: (r) => r["name"] == "{template}")
                            |> filter(fn: (r) => r["_field"] == "source")
                            |> last()
                        '''
                        tables = query_api.query(query)
                        if not tables or not tables[0].records:
                            return False
                        current_timestamp = tables[0].records[0].get_time()
                        return current_timestamp == last_timestamp

                return source, None, uptodate

            return source, None, None

        def list_templates(self) -> list[str]:
            with InfluxDBClient(
                url=self.url, token=self.token, org=self.org
            ) as client:
                query_api = client.query_api()
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: -100y)
                    |> filter(fn: (r) => r["_measurement"] == "{self.measurement}")
                    |> filter(fn: (r) => r["_field"] == "source")
                    |> distinct(column: "name")
                '''
                tables = query_api.query(query)

                names = set()
                for table in tables:
                    for record in table.records:
                        name = record.values.get("name")
                        if name:
                            names.add(name)

                return sorted(names)

except ImportError:
    INFLUXDB_AVAILABLE = False
    InfluxDBLoader = None  # type: ignore[misc, assignment]


__all__ = [
    "SQLALCHEMY_AVAILABLE",
    "PEEWEE_AVAILABLE",
    "DJANGO_AVAILABLE",
    "INFLUXDB_AVAILABLE",
    "SQLAlchemyLoader",
    "SQLAlchemyTemplateBase",
    "PeeweeLoader",
    "PeeweeTemplateModel",
    "DjangoLoader",
    "DjangoTemplateModel",
    "InfluxDBLoader",
]
