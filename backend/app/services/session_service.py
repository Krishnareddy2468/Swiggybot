"""
Session Service - Manages user conversation sessions and state
"""
from typing import List
from app.models.schemas import UserSession, ConversationState, CartItem
import logging

logger = logging.getLogger(__name__)


class SessionService:
    """Manages user sessions with conversation context"""

    def __init__(self):
        self._sessions: dict[str, UserSession] = {}

    def get_session(self, user_id: str, user_name: str = None) -> UserSession:
        """Get or create a user session"""
        if user_id not in self._sessions:
            self._sessions[user_id] = UserSession(
                user_id=user_id,
                user_name=user_name,
            )
            logger.info(f"Created new session for user: {user_id}")
        else:
            if user_name:
                self._sessions[user_id].user_name = user_name
        return self._sessions[user_id]

    def update_state(self, user_id: str, state: ConversationState):
        """Update the conversation state"""
        session = self.get_session(user_id)
        session.state = state
        logger.info(f"User {user_id} state changed to: {state.value}")

    def set_search_results(self, user_id: str, results: list):
        """Store search results in session"""
        session = self.get_session(user_id)
        session.search_results = results

    def set_selected_restaurant(self, user_id: str, restaurant_id: str):
        """Set the selected restaurant"""
        session = self.get_session(user_id)
        session.selected_restaurant_id = restaurant_id

    def add_to_cart(self, user_id: str, item: CartItem):
        """Add an item to the cart"""
        session = self.get_session(user_id)
        # Check if item already exists in cart
        for existing in session.cart:
            if existing.item_id == item.item_id:
                existing.quantity += item.quantity
                return
        session.cart.append(item)

    def remove_from_cart(self, user_id: str, item_name: str) -> bool:
        """Remove an item from the cart by name"""
        session = self.get_session(user_id)
        for i, item in enumerate(session.cart):
            if item_name.lower() in item.name.lower():
                session.cart.pop(i)
                return True
        return False

    def update_cart_quantity(self, user_id: str, item_name: str, quantity: int) -> bool:
        """Update quantity of a cart item"""
        session = self.get_session(user_id)
        for item in session.cart:
            if item_name.lower() in item.name.lower():
                if quantity <= 0:
                    return self.remove_from_cart(user_id, item_name)
                item.quantity = quantity
                return True
        return False

    def clear_cart(self, user_id: str):
        """Clear the cart"""
        session = self.get_session(user_id)
        session.cart = []

    def get_cart(self, user_id: str) -> List[CartItem]:
        """Get current cart items"""
        session = self.get_session(user_id)
        return session.cart

    def get_cart_total(self, user_id: str) -> int:
        """Calculate cart subtotal"""
        session = self.get_session(user_id)
        return sum(item.price * item.quantity for item in session.cart)

    def set_address(self, user_id: str, address: str):
        """Set delivery address"""
        session = self.get_session(user_id)
        session.pending_address = address

    def set_current_order(self, user_id: str, order_id: str):
        """Set the current order ID"""
        session = self.get_session(user_id)
        session.current_order_id = order_id

    def add_to_history(self, user_id: str, role: str, content: str):
        """Add a message to conversation history"""
        session = self.get_session(user_id)
        session.conversation_history.append({
            "role": role,
            "content": content,
        })
        # Keep last 20 messages for context
        if len(session.conversation_history) > 20:
            session.conversation_history = session.conversation_history[-20:]

    def set_last_bot_message(self, user_id: str, message: str):
        """Store the last bot message for context"""
        session = self.get_session(user_id)
        session.last_bot_message = message

    def reset_session(self, user_id: str):
        """Reset session to initial state (keep user info)"""
        session = self.get_session(user_id)
        session.state = ConversationState.IDLE
        session.search_results = []
        session.selected_restaurant_id = None
        session.cart = []
        session.pending_address = None
        session.current_order_id = None
        session.conversation_history = []
        session.last_bot_message = None
        session.menu_items_map = {}
        logger.info(f"Session reset for user: {user_id}")

    def get_all_sessions(self) -> dict:
        """Get all active sessions (for admin/debugging)"""
        return {
            uid: {
                "user_name": s.user_name,
                "state": s.state.value,
                "cart_items": len(s.cart),
                "current_order": s.current_order_id,
            }
            for uid, s in self._sessions.items()
        }


# Singleton instance
session_service = SessionService()
