"""Tests for database template loaders."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from jinja2.exceptions import TemplateNotFound


# =============================================================================
# SQLAlchemy Loader Tests
# =============================================================================


@pytest.mark.asyncio
async def test_sqlalchemy_loader_get_source_async():
    """Test SQLAlchemy loader returns template source."""
    pytest.importorskip("sqlalchemy")

    from jinja2_async.db_loaders import SQLAlchemyLoader, SQLAlchemyTemplateBase

    # Create a mock model
    class MockTemplate(SQLAlchemyTemplateBase):
        __tablename__ = "templates"

    # Create mock session and result
    mock_row = MagicMock()
    mock_row.source = "Hello {{ name }}!"
    mock_row.updated_at = datetime.utcnow()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_row

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_factory = MagicMock(return_value=mock_session)

    loader = SQLAlchemyLoader(
        session_factory=mock_factory,
        model=MockTemplate,
    )

    # Mock environment
    env = MagicMock()

    source, filename, uptodate = await loader.get_source_async(env, "test.html")

    assert source == "Hello {{ name }}!"
    assert filename is None
    assert uptodate is not None  # auto_reload is True by default


@pytest.mark.asyncio
async def test_sqlalchemy_loader_template_not_found():
    """Test SQLAlchemy loader raises TemplateNotFound for missing templates."""
    pytest.importorskip("sqlalchemy")

    from jinja2_async.db_loaders import SQLAlchemyLoader, SQLAlchemyTemplateBase

    class MockTemplate(SQLAlchemyTemplateBase):
        __tablename__ = "templates_not_found"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_factory = MagicMock(return_value=mock_session)

    loader = SQLAlchemyLoader(
        session_factory=mock_factory,
        model=MockTemplate,
    )

    env = MagicMock()

    with pytest.raises(TemplateNotFound):
        await loader.get_source_async(env, "nonexistent.html")


@pytest.mark.asyncio
async def test_sqlalchemy_loader_list_templates_async():
    """Test SQLAlchemy loader lists all templates."""
    pytest.importorskip("sqlalchemy")

    from jinja2_async.db_loaders import SQLAlchemyLoader, SQLAlchemyTemplateBase

    class MockTemplate(SQLAlchemyTemplateBase):
        __tablename__ = "templates_list"

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("a.html",), ("b.html",), ("c.html",)]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_factory = MagicMock(return_value=mock_session)

    loader = SQLAlchemyLoader(
        session_factory=mock_factory,
        model=MockTemplate,
    )

    templates = await loader.list_templates_async()

    assert templates == ["a.html", "b.html", "c.html"]


def test_sqlalchemy_loader_sync_raises():
    """Test SQLAlchemy loader sync methods raise RuntimeError."""
    pytest.importorskip("sqlalchemy")

    from jinja2_async.db_loaders import SQLAlchemyLoader, SQLAlchemyTemplateBase

    class MockTemplate(SQLAlchemyTemplateBase):
        __tablename__ = "templates_sync"

    loader = SQLAlchemyLoader(
        session_factory=MagicMock(),
        model=MockTemplate,
    )

    env = MagicMock()

    with pytest.raises(RuntimeError, match="requires async context"):
        loader.get_source(env, "test.html")

    with pytest.raises(TypeError, match="requires async context"):
        loader.list_templates()


# =============================================================================
# Peewee Loader Tests
# =============================================================================


def test_peewee_loader_get_source():
    """Test Peewee loader returns template source."""
    pytest.importorskip("peewee")

    from jinja2_async.db_loaders import PeeweeLoader, PeeweeTemplateModel

    mock_row = MagicMock()
    mock_row.source = "Hello {{ name }}!"
    mock_row.updated_at = datetime.utcnow()

    # Create a mock model class
    MockModel = MagicMock(spec=PeeweeTemplateModel)
    MockModel.get.return_value = mock_row
    MockModel.name = MagicMock()

    loader = PeeweeLoader(model=MockModel)

    env = MagicMock()

    source, filename, uptodate = loader.get_source(env, "test.html")

    assert source == "Hello {{ name }}!"
    assert filename is None


def test_peewee_loader_template_not_found():
    """Test Peewee loader raises TemplateNotFound for missing templates."""
    peewee = pytest.importorskip("peewee")

    from jinja2_async.db_loaders import PeeweeLoader, PeeweeTemplateModel

    MockModel = MagicMock(spec=PeeweeTemplateModel)
    MockModel.get.side_effect = peewee.DoesNotExist()

    loader = PeeweeLoader(model=MockModel)

    env = MagicMock()

    with pytest.raises(TemplateNotFound):
        loader.get_source(env, "nonexistent.html")


def test_peewee_loader_list_templates():
    """Test Peewee loader lists all templates."""
    pytest.importorskip("peewee")

    from jinja2_async.db_loaders import PeeweeLoader, PeeweeTemplateModel

    mock_rows = [MagicMock(name="a.html"), MagicMock(name="b.html")]
    mock_rows[0].name = "a.html"
    mock_rows[1].name = "b.html"

    MockModel = MagicMock(spec=PeeweeTemplateModel)
    MockModel.select.return_value = mock_rows
    MockModel.name = MagicMock()

    loader = PeeweeLoader(model=MockModel)

    templates = loader.list_templates()

    assert templates == ["a.html", "b.html"]


# =============================================================================
# Django Loader Tests
# =============================================================================


def _configure_django_and_get_loader():
    """Configure Django settings and return DjangoLoader."""
    import importlib

    import django
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}},
            INSTALLED_APPS=[],
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        )
        django.setup()

    # Reload the module to pick up Django now that it's configured
    import jinja2_async.db_loaders

    importlib.reload(jinja2_async.db_loaders)
    return jinja2_async.db_loaders.DjangoLoader


@pytest.mark.asyncio
async def test_django_loader_get_source_async():
    """Test Django loader returns template source."""
    pytest.importorskip("django")
    DjangoLoader = _configure_django_and_get_loader()

    mock_row = MagicMock()
    mock_row.source = "Hello {{ name }}!"
    mock_row.updated_at = datetime.utcnow()

    MockModel = MagicMock()
    MockModel.objects = MagicMock()
    MockModel.objects.aget = AsyncMock(return_value=mock_row)
    MockModel.DoesNotExist = Exception

    loader = DjangoLoader(model=MockModel)

    env = MagicMock()

    source, filename, uptodate = await loader.get_source_async(env, "test.html")

    assert source == "Hello {{ name }}!"
    assert filename is None


@pytest.mark.asyncio
async def test_django_loader_template_not_found():
    """Test Django loader raises TemplateNotFound for missing templates."""
    pytest.importorskip("django")
    DjangoLoader = _configure_django_and_get_loader()

    class DoesNotExist(Exception):
        pass

    MockModel = MagicMock()
    MockModel.objects = MagicMock()
    MockModel.objects.aget = AsyncMock(side_effect=DoesNotExist())
    MockModel.DoesNotExist = DoesNotExist

    loader = DjangoLoader(model=MockModel)

    env = MagicMock()

    with pytest.raises(TemplateNotFound):
        await loader.get_source_async(env, "nonexistent.html")


# =============================================================================
# InfluxDB Loader Tests
# =============================================================================


@pytest.mark.asyncio
async def test_influxdb_loader_get_source_async():
    """Test InfluxDB loader returns template source."""
    pytest.importorskip("influxdb_client")

    from jinja2_async.db_loaders import InfluxDBLoader

    mock_record = MagicMock()
    mock_record.get_value.return_value = "Hello {{ name }}!"
    mock_record.get_time.return_value = datetime.utcnow()

    mock_table = MagicMock()
    mock_table.records = [mock_record]

    mock_query_api = MagicMock()
    mock_query_api.query = AsyncMock(return_value=[mock_table])

    mock_client = MagicMock()
    mock_client.query_api.return_value = mock_query_api
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "jinja2_async.db_loaders.InfluxDBClientAsync", return_value=mock_client
    ):
        loader = InfluxDBLoader(
            url="http://localhost:8086",
            token="test-token",
            org="test-org",
            bucket="templates",
        )

        env = MagicMock()

        source, filename, uptodate = await loader.get_source_async(env, "test.html")

        assert source == "Hello {{ name }}!"
        assert filename is None


@pytest.mark.asyncio
async def test_influxdb_loader_template_not_found():
    """Test InfluxDB loader raises TemplateNotFound for missing templates."""
    pytest.importorskip("influxdb_client")

    from jinja2_async.db_loaders import InfluxDBLoader

    mock_query_api = MagicMock()
    mock_query_api.query = AsyncMock(return_value=[])

    mock_client = MagicMock()
    mock_client.query_api.return_value = mock_query_api
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "jinja2_async.db_loaders.InfluxDBClientAsync", return_value=mock_client
    ):
        loader = InfluxDBLoader(
            url="http://localhost:8086",
            token="test-token",
            org="test-org",
            bucket="templates",
        )

        env = MagicMock()

        with pytest.raises(TemplateNotFound):
            await loader.get_source_async(env, "nonexistent.html")


# =============================================================================
# Availability Flag Tests
# =============================================================================


def test_availability_flags():
    """Test that availability flags are properly set."""
    from jinja2_async import db_loaders

    # These should always be defined
    assert hasattr(db_loaders, "SQLALCHEMY_AVAILABLE")
    assert hasattr(db_loaders, "PEEWEE_AVAILABLE")
    assert hasattr(db_loaders, "DJANGO_AVAILABLE")
    assert hasattr(db_loaders, "INFLUXDB_AVAILABLE")

    # Values should be boolean
    assert isinstance(db_loaders.SQLALCHEMY_AVAILABLE, bool)
    assert isinstance(db_loaders.PEEWEE_AVAILABLE, bool)
    assert isinstance(db_loaders.DJANGO_AVAILABLE, bool)
    assert isinstance(db_loaders.INFLUXDB_AVAILABLE, bool)
