from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProductRecord(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_products_idempotency_key"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    image_key: Mapped[str] = mapped_column(String(512))
    # Who asked to create it, e.g. "tg:<chat_id>:<message_id>": a repeated request finds the existing row.
    idempotency_key: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
