from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatMessage, ChatResponse
from app.services.gemini_agent import gemini_agent
from app.services.session_service import session_service
from app.services.order_service import order_service
from app.services.restaurant_service import restaurant_service
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(chat: ChatMessage):
    """main chat endpoint - processes user message and returns bot response"""
    try:
        response = await gemini_agent.process_message(
            user_id=chat.user_id,
            message=chat.message,
            user_name=chat.user_name,
        )

        session = session_service.get_session(chat.user_id)

        # grab restaurant info if one is selected
        restaurant_data = None
        if session.selected_restaurant_id:
            rest = restaurant_service.get_restaurant_by_id(session.selected_restaurant_id)
            if rest:
                restaurant_data = {
                    "id": rest["id"],
                    "name": rest["name"],
                    "image": rest["image"],
                    "rating": rest["rating"],
                    "delivery_time": rest["delivery_time"],
                }

        order_data = None
        if session.current_order_id:
            order = order_service.get_order(session.current_order_id)
            if order:
                order_data = order.model_dump()

        # kick off order tracking sim if order was just placed
        if session.current_order_id:
            order = order_service.get_order(session.current_order_id)
            if order and order.status.value == "confirmed":
                asyncio.create_task(
                    order_service.simulate_order_progress(session.current_order_id)
                )

        return ChatResponse(
            response=response,
            state=session.state.value,
            cart_items=[item.model_dump() for item in session.cart],
            restaurant=restaurant_data,
            order=order_data,
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{user_id}")
async def get_session(user_id: str):
    session = session_service.get_session(user_id)
    restaurant_data = None
    if session.selected_restaurant_id:
        rest = restaurant_service.get_restaurant_by_id(session.selected_restaurant_id)
        if rest:
            restaurant_data = {
                "id": rest["id"],
                "name": rest["name"],
                "image": rest["image"],
                "rating": rest["rating"],
            }

    return {
        "user_id": session.user_id,
        "state": session.state.value,
        "restaurant": restaurant_data,
        "cart_items": [item.model_dump() for item in session.cart],
        "current_order_id": session.current_order_id,
    }


@router.post("/reset/{user_id}")
async def reset_session(user_id: str):
    session_service.reset_session(user_id)
    return {"message": "Session reset successfully"}
