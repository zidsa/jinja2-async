from .bccache import AsyncBytecodeCache, FileSystemBytecodeCache, MemcachedBytecodeCache
from .compiler import AsyncCodeGenerator
from .environment import AsyncEnvironment, AsyncTemplate
from .loaders import (
    AsyncBaseLoader,
    ChoiceLoader,
    DictLoader,
    FileSystemLoader,
    FunctionLoader,
    ModuleLoader,
    PackageLoader,
    PrefixLoader,
)
from .sandbox import AsyncSandboxedEnvironment

__all__ = [
    "AsyncCodeGenerator",
    "AsyncEnvironment",
    "AsyncTemplate",
    "AsyncSandboxedEnvironment",
    "AsyncBytecodeCache",
    "AsyncBaseLoader",
    "FileSystemBytecodeCache",
    "MemcachedBytecodeCache",
    "ChoiceLoader",
    "DictLoader",
    "FileSystemLoader",
    "FunctionLoader",
    "ModuleLoader",
    "PackageLoader",
    "PrefixLoader",
]

# Optional: Redis bytecode cache
try:
    from .bccache import (  # noqa: F401
        REDIS_AVAILABLE,
        RedisBytecodeCache,
    )

    __all__.extend(["RedisBytecodeCache", "REDIS_AVAILABLE"])
except ImportError:
    REDIS_AVAILABLE = False

# Optional: SQLAlchemy loader
try:
    from .db_loaders import (  # noqa: F401
        SQLALCHEMY_AVAILABLE,
        SQLAlchemyLoader,
        SQLAlchemyTemplateBase,
    )

    __all__.extend(
        ["SQLAlchemyLoader", "SQLAlchemyTemplateBase", "SQLALCHEMY_AVAILABLE"]
    )
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# Optional: Peewee loader
try:
    from .db_loaders import (  # noqa: F401
        PEEWEE_AVAILABLE,
        PeeweeLoader,
        PeeweeTemplateModel,
    )

    __all__.extend(["PeeweeLoader", "PeeweeTemplateModel", "PEEWEE_AVAILABLE"])
except ImportError:
    PEEWEE_AVAILABLE = False

# Optional: Django loader
try:
    from .db_loaders import (  # noqa: F401
        DJANGO_AVAILABLE,
        DjangoLoader,
        DjangoTemplateModel,
    )

    __all__.extend(["DjangoLoader", "DjangoTemplateModel", "DJANGO_AVAILABLE"])
except ImportError:
    DJANGO_AVAILABLE = False

# Optional: InfluxDB loader
try:
    from .db_loaders import (  # noqa: F401
        INFLUXDB_AVAILABLE,
        InfluxDBLoader,
    )

    __all__.extend(["InfluxDBLoader", "INFLUXDB_AVAILABLE"])
except ImportError:
    INFLUXDB_AVAILABLE = False
