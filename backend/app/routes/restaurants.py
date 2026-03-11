from fastapi import APIRouter, HTTPException, Query
from app.services.restaurant_service import restaurant_service
from app.services.order_service import order_service
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/restaurants", tags=["Restaurants"])


@router.get("/")
async def search_restaurants(
    query: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    cuisine: Optional[str] = Query(None),
    veg_only: bool = Query(False),
):
    results = restaurant_service.search_restaurants(
        query=query or "", location=location or "",
        cuisine=cuisine or "", veg_only=veg_only,
    )
    # return simplified data without full menus (too heavy)
    return [
        {
            "id": r["id"], "name": r["name"], "cuisine": r["cuisine"],
            "rating": r["rating"], "total_ratings": r["total_ratings"],
            "delivery_time": r["delivery_time"], "delivery_fee": r["delivery_fee"],
            "cost_for_two": r["cost_for_two"], "is_veg": r["is_veg"],
            "location": r["location"], "address": r["address"],
            "offers": r.get("offers", []), "image": r["image"],
        }
        for r in results
    ]


@router.get("/locations")
async def get_locations():
    return restaurant_service.get_available_locations()


@router.get("/cuisines")
async def get_cuisines():
    return restaurant_service.get_cuisine_types()


@router.get("/{restaurant_id}")
async def get_restaurant(restaurant_id: str):
    restaurant = restaurant_service.get_restaurant_by_id(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


@router.get("/{restaurant_id}/menu")
async def get_menu(
    restaurant_id: str,
    category: Optional[str] = Query(None),
    veg_only: bool = Query(False),
):
    menu = restaurant_service.get_menu(restaurant_id, category=category, veg_only=veg_only)
    if menu is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return menu


@router.get("/{restaurant_id}/bestsellers")
async def get_bestsellers(restaurant_id: str):
    return restaurant_service.get_bestsellers(restaurant_id)


# order endpoints

@router.get("/orders/all")
async def get_all_orders():
    orders = order_service.get_all_orders()
    return [order.model_dump() for order in orders]


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = order_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.model_dump()


@router.get("/orders/user/{user_id}")
async def get_user_orders(user_id: str):
    orders = order_service.get_user_orders(user_id)
    return [order.model_dump() for order in orders]
