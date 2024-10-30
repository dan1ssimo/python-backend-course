from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt, PositiveFloat
from typing import List, Dict, Optional, Annotated
from http import HTTPStatus
from schemas import ItemCreate, ItemPatch, Item, CartItem, Cart

app = FastAPI()

items: Dict[int, Item] = {}
carts: Dict[int, Cart] = {}

# CRUD для товаров
@app.post("/item", response_model=Item, status_code=HTTPStatus.CREATED)
def create_item(item_data: ItemCreate):
    item_id = len(items) + 1
    new_item = Item.from_item(item_data, item_id)
    items[item_id] = new_item
    return new_item


@app.get("/item/{id}", response_model=Item)
def get_item(id: int):
    item = items.get(id)
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item


@app.get("/item", response_model=List[Item])
def get_items(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[Optional[PositiveFloat], Query()] = None,
    max_price: Annotated[Optional[PositiveFloat], Query()] = None,
    show_deleted: Annotated[bool, Query()] = False,
):
    filtered_items = [
        item for item in items.values()
        if (show_deleted or not item.deleted) and
           (min_price is None or item.price >= min_price) and
           (max_price is None or item.price <= max_price)
    ]
    return filtered_items[offset : offset + limit]


@app.put("/item/{id}", response_model=Item)
def update_item(id: int, item_data: ItemCreate):
    item = items.get(id)
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    updated_item = Item.from_item(item_data, id)
    items[id] = updated_item
    return updated_item


@app.patch("/item/{id}", response_model=Item)
def patch_item(id: int, item_data: ItemPatch):
    item = items.get(id)
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED, detail="Item not found")

    updated_item = item.model_copy(update=item_data.model_dump())
    items[id] = updated_item
    return updated_item


@app.delete("/item/{id}", response_model=Item)
def delete_item(id: int):
    item = items.get(id)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    item.deleted = True
    return item



@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response):
    cart_id = len(carts) + 1
    new_cart = Cart(id=cart_id, items=[])
    carts[cart_id] = new_cart
    response.headers["Location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@app.get("/cart/{id}", response_model=Cart)
def get_cart(id: int):
    cart = carts.get(id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    return cart


@app.get("/cart", response_model=List[Cart])
def get_carts(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[Optional[PositiveFloat], Query()] = None,
    max_price: Annotated[Optional[PositiveFloat], Query()] = None,
    min_quantity: Annotated[Optional[NonNegativeInt], Query()] = None,
    max_quantity: Annotated[Optional[NonNegativeInt], Query()] = None,
):
    filtered_carts = []
    for i, cart in enumerate(carts.values()):
        if not (offset <= i < offset + limit):
            continue

        cart_total_quantity = sum(item.quantity for item in cart.items)
        if (
            (min_price is not None and cart.price < min_price) or
            (max_price is not None and cart.price > max_price) or
            (min_quantity is not None and cart_total_quantity < min_quantity) or
            (max_quantity is not None and cart_total_quantity > max_quantity)
        ):
            continue

        filtered_carts.append(cart)

    return filtered_carts


@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart)
def add_item_to_cart(cart_id: int, item_id: int):
    cart = carts.get(cart_id)
    item = items.get(item_id)

    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    for cart_item in cart.items:
        if cart_item.id == item.id:
            cart_item.quantity += 1
            cart.price += item.price
            return cart

    cart.items.append(CartItem(id=item.id, name=item.name, quantity=1, available=True))
    cart.price += item.price
    return cart
