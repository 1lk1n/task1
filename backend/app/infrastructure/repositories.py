from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import Product
from app.infrastructure.models import ProductRecord


def _to_domain(record: ProductRecord) -> Product:
    return Product(id=record.id, title=record.title, image_key=record.image_key, created_at=record.created_at)


class SqlAlchemyProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_newest_first(self) -> list[Product]:
        result = await self._session.scalars(select(ProductRecord).order_by(ProductRecord.id.desc()))
        return [_to_domain(record) for record in result]

    async def get(self, product_id: int) -> Product | None:
        record = await self._session.get(ProductRecord, product_id)
        return _to_domain(record) if record is not None else None

    async def get_by_idempotency_key(self, idempotency_key: str) -> Product | None:
        record = await self._session.scalar(
            select(ProductRecord).where(ProductRecord.idempotency_key == idempotency_key)
        )
        return _to_domain(record) if record is not None else None

    async def add(self, title: str, image_key: str, idempotency_key: str) -> Product:
        # ON CONFLICT DO NOTHING: when two replicas handle the same request at once, one inserts
        # and the other reads the row the first one wrote, instead of failing on the unique key.
        statement = (
            insert(ProductRecord)
            .values(title=title, image_key=image_key, idempotency_key=idempotency_key)
            .on_conflict_do_nothing(index_elements=[ProductRecord.idempotency_key])
            .returning(ProductRecord)
        )
        record = await self._session.scalar(statement)
        if record is None:
            record = await self._session.scalar(
                select(ProductRecord).where(ProductRecord.idempotency_key == idempotency_key)
            )
        await self._session.commit()
        return _to_domain(record)
