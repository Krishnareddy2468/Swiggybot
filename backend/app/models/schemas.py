"""
Pydantic models for the restaurant order bot
"""
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class ConversationState(str, Enum):
    """State machine for conversation flow"""
    IDLE = "idle"
    SEARCHING = "searching"
    RESTAURANT_SELECTED = "restaurant_selected"
    BROWSING_MENU = "browsing_menu"
    ORDERING = "ordering"
    AWAITING_ADDRESS = "awaiting_address"
    CONFIRMING_ORDER = "confirming_order"
    ORDER_PLACED = "order_placed"
    TRACKING = "tracking"


class OrderStatus(str, Enum):
    """Order status progression"""
    PLACED = "placed"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class CartItem(BaseModel):
    """Item in the shopping cart"""
    item_id: str
    name: str
    size: Optional[str] = None
    price: int
    quantity: int
    is_veg: bool


class Order(BaseModel):
    """Order model"""
    order_id: str
    user_id: str
    restaurant_id: str
    restaurant_name: str
    items: List[CartItem]
    subtotal: int
    tax: int
    delivery_fee: int
    total: int
    address: str
    payment_method: str = "Cash on Delivery"
    status: OrderStatus = OrderStatus.PLACED
    estimated_delivery: str = ""
    delivery_partner: Optional[str] = None
    delivery_partner_phone: Optional[str] = None
    created_at: str = ""


class UserSession(BaseModel):
    """User session for maintaining conversation context"""
    user_id: str
    user_name: Optional[str] = None
    state: ConversationState = ConversationState.IDLE
    current_location: Optional[str] = None
    search_results: list = []
    selected_restaurant_id: Optional[str] = None
    cart: List[CartItem] = []
    pending_address: Optional[str] = None
    current_order_id: Optional[str] = None
    conversation_history: list = []
    last_bot_message: Optional[str] = None
    menu_items_map: dict = {}  # maps number -> menu item for quick selection


class ChatMessage(BaseModel):
    """Chat message model for API"""
    message: str
    user_id: str = "web_user"
    user_name: Optional[str] = "Guest"


class ChatResponse(BaseModel):
    """Chat response model for API"""
    response: str
    state: str
    cart_items: list = []
    restaurant: Optional[dict] = None
    order: Optional[dict] = None


class AIIntent(BaseModel):
    """Parsed intent from AI"""
    intent: str
    entities: dict = {}
    confidence: float = 0.0
