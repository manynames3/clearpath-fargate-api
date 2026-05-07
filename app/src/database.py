from collections.abc import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.config import fetch_json_secret, generate_iam_auth_token, get_settings
from src.models import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_database_url() -> str:
    settings = get_settings()
    if settings.database_url:
        return settings.database_url

    if not settings.db_secret_arn or not settings.db_proxy_endpoint:
        raise RuntimeError("Set DATABASE_URL or both DB_SECRET_ARN and DB_PROXY_ENDPOINT")

    secret = fetch_json_secret(settings.db_secret_arn, settings.aws_region)
    username = settings.db_user or secret.get("username")
    if not username:
        raise RuntimeError("Database username is not configured")

    token = generate_iam_auth_token(settings.db_proxy_endpoint, username, settings.aws_region)
    return str(
        URL.create(
            drivername="postgresql+asyncpg",
            username=username,
            password=token,
            host=settings.db_proxy_endpoint,
            port=5432,
            database=settings.db_name,
        )
    )


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        url = _build_database_url()
        connect_args = {}
        if url.startswith("postgresql+asyncpg"):
            connect_args["ssl"] = True

        engine_kwargs = {
            "pool_pre_ping": True,
            "connect_args": connect_args,
        }
        if url.startswith("postgresql+asyncpg"):
            engine_kwargs.update({"pool_size": 5, "max_overflow": 10, "pool_recycle": 840})

        _engine = create_async_engine(url, **engine_kwargs)

        if settings.db_proxy_endpoint and url.startswith("postgresql+asyncpg"):

            @event.listens_for(_engine.sync_engine, "do_connect")
            def _provide_iam_token(_dialect, _conn_rec, _cargs, cparams):
                cparams["password"] = generate_iam_auth_token(
                    settings.db_proxy_endpoint,
                    settings.db_user,
                    settings.aws_region,
                )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session


async def init_db() -> None:
    settings = get_settings()
    if settings.skip_db_init:
        return

    if settings.local_create_tables:
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return

    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))


async def create_all_for_tests() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def reset_engine_for_tests() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
