from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional, Annotated
from uuid import uuid4
from pydantic import NonNegativeInt, PositiveInt, PositiveFloat
from http import HTTPStatus

class ItemCreate(BaseModel):
    name: str
    price: float
    deleted: bool = False


class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

    @staticmethod
    def from_item(item: ItemCreate, id) -> 'Item':
        return Item(
            id=id,
            name=item.name,
            price=item.price,
            deleted=item.deleted,
        )


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class Cart(BaseModel):
    id: int
    items: List[CartItem]
    price: float = 0.0