from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def create_engine(database_url: str) -> AsyncEngine:
    # One pool per process; with N replicas the database sees N small pools.
    return create_async_engine(database_url, pool_size=5, max_overflow=5, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: objects stay readable after commit without lazy loading,
    # which would need implicit IO in async code.
    return async_sessionmaker(engine, expire_on_commit=False)
