from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Product:
    id: int
    title: str
    image_key: str
    created_at: datetime


class DomainError(Exception):
    """Base class for errors the API turns into client-facing responses."""


class InvalidProduct(DomainError):
    pass


class ProductNotFound(DomainError):
    pass
