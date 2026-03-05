"""
Gemini AI Agent - Core conversational AI that processes natural language
and orchestrates the food ordering flow using Google Gemini.

This is the brain of the bot. It:
1. Understands user intent from natural language
2. Manages conversation state transitions
3. Calls appropriate services (restaurant, order, session)
4. Generates natural, contextual responses
"""
import os
import json
import logging
import google.generativeai as genai
from app.models.schemas import ConversationState, CartItem
from app.services.restaurant_service import restaurant_service
from app.services.session_service import session_service
from app.services.order_service import order_service

logger = logging.getLogger(__name__)


class GeminiAgent:
    """AI Agent powered by Google Gemini for natural language food ordering"""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set! AI features will use fallback logic.")
            self.model = None
            return

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("Gemini AI Agent initialized successfully")

    def _build_system_prompt(self, session) -> str:
        """Build context-aware system prompt for Gemini"""
        restaurant_info = ""
        if session.selected_restaurant_id:
            rest = restaurant_service.get_restaurant_by_id(session.selected_restaurant_id)
            if rest:
                restaurant_info = f"""
Currently selected restaurant: {rest['name']}
Location: {rest['location']}
Cuisine: {', '.join(rest['cuisine'])}
Rating: {rest['rating']}
Delivery Time: {rest['delivery_time']}
Delivery Fee: ₹{rest['delivery_fee']}
"""
                # Add menu items as flat list for the AI to reference
                menu_items = []
                for cat, items in rest['menu'].items():
                    for item in items:
                        size_info = f" ({item.get('size', '')})" if item.get('size') else ""
                        menu_items.append(f"- {item['name']}{size_info}: ₹{item['price']} (ID: {item['id']}, {'Veg' if item['is_veg'] else 'Non-Veg'})")
                restaurant_info += f"\nAvailable menu items:\n" + "\n".join(menu_items)

        cart_info = ""
        if session.cart:
            cart_items = []
            for item in session.cart:
                size_info = f" ({item.size})" if item.size else ""
                cart_items.append(f"- {item.name}{size_info} x{item.quantity} = ₹{item.price * item.quantity}")
            cart_total = sum(i.price * i.quantity for i in session.cart)
            cart_info = f"\nCurrent cart:\n" + "\n".join(cart_items) + f"\nCart subtotal: ₹{cart_total}"

        order_info = ""
        if session.current_order_id:
            order = order_service.get_order(session.current_order_id)
            if order:
                order_info = f"\nCurrent order: {order.order_id}, Status: {order.status.value}, Total: ₹{order.total}"

        return f"""You are a friendly and helpful Swiggy food ordering assistant bot. You help customers order food from restaurants in Bangalore, India.

CURRENT STATE: {session.state.value}
{restaurant_info}
{cart_info}
{order_info}

YOUR TASK: Analyze the user's message and respond with a JSON object containing:
1. "intent" - One of: greet, search_restaurants, select_restaurant, show_menu, show_category, filter_veg, add_to_cart, remove_from_cart, show_cart, clear_cart, checkout, provide_address, confirm_order, cancel_order, track_order, order_status, help, start_over, ask_about_item, unknown
2. "entities" - A JSON object with extracted entities:
   - "location": location name if mentioned
   - "cuisine": cuisine type if mentioned  
   - "restaurant_name": restaurant name if mentioned
   - "restaurant_index": 1-based index if user selects by number
   - "items": list of objects with "name", "quantity" (default 1), "size" (if mentioned)
   - "address": delivery address if provided
   - "category": menu category if mentioned
   - "item_query": item name being asked about
   - "veg_only": true if user wants only veg items
3. "response_hint" - A brief natural language suggestion for how the bot should respond

IMPORTANT RULES:
- When user says a number (like "1", "2", "3") after seeing a restaurant list, the intent is "select_restaurant" with "restaurant_index"
- When user says a number after seeing a menu, it likely refers to ordering that item
- "Add", "order", "I want", "give me", "get me" → add_to_cart intent
- "remove", "delete", "cancel item" → remove_from_cart
- "cart", "my order", "what's in my cart" → show_cart
- "checkout", "place order", "confirm", "order now", "proceed" → checkout
- "yes", "confirm", "place it", "go ahead" during CONFIRMING_ORDER state → confirm_order
- "no", "cancel" during CONFIRMING_ORDER → cancel_order
- Parse quantities naturally: "2 margherita", "one farmhouse", "a garlic bread" etc.
- Location names: Madhapur, HITEC City, Gachibowli, Banjara Hills, etc.
- "menu", "show menu", "what do you have" → show_menu
- "hi", "hello", "hey", "start" → greet
- "help" → help
- "start over", "reset", "new order" → start_over
- "track", "where is my order", "order status" → track_order
- When the state is AWAITING_ADDRESS, treat most text input as an address (provide_address intent)
- When state is CONFIRMING_ORDER, "yes"/"confirm" → confirm_order, "no"/"cancel" → cancel_order

Respond ONLY with a valid JSON object, no markdown or code blocks.
"""

    async def process_message(self, user_id: str, message: str, user_name: str = None) -> str:
        """
        Process a user message and return the bot response.
        This is the main entry point for all user interactions.
        """
        session = session_service.get_session(user_id, user_name)

        # Add user message to history
        session_service.add_to_history(user_id, "user", message)

        # Get AI intent analysis
        intent_data = await self._analyze_intent(session, message)

        # Route to appropriate handler based on intent
        response = await self._handle_intent(user_id, intent_data, message)

        # Add bot response to history
        session_service.add_to_history(user_id, "assistant", response)
        session_service.set_last_bot_message(user_id, response)

        return response

    async def _analyze_intent(self, session, message: str) -> dict:
        """Use Gemini to analyze user intent"""
        if not self.model:
            return self._fallback_intent_analysis(session, message)

        try:
            system_prompt = self._build_system_prompt(session)

            # Build conversation context
            history_text = ""
            for msg in session.conversation_history[-6:]:
                role = "User" if msg["role"] == "user" else "Bot"
                history_text += f"{role}: {msg['content']}\n"

            prompt = f"""{system_prompt}

Recent conversation:
{history_text}

Current user message: "{message}"

Respond with JSON only:"""

            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # Clean up the response - remove markdown if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            if text.startswith("json"):
                text = text[4:].strip()

            result = json.loads(text)
            logger.info(f"AI Intent: {result.get('intent')} | Entities: {result.get('entities', {})}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return self._fallback_intent_analysis(session, message)
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._fallback_intent_analysis(session, message)

    def _fallback_intent_analysis(self, session, message: str) -> dict:
        """Fallback keyword-based intent detection (used when Gemini is unavailable)"""
        msg = message.lower().strip()
        words = set(msg.split())  # split into individual words for exact matching

        # state-based shortcuts - these take priority over everything
        if session.state == ConversationState.AWAITING_ADDRESS:
            return {"intent": "provide_address", "entities": {"address": message}}

        if session.state == ConversationState.CONFIRMING_ORDER:
            if words & {"yes", "confirm", "sure", "ok", "yep", "yeah"}:
                return {"intent": "confirm_order", "entities": {}}
            if words & {"no", "cancel", "nope", "nah"}:
                return {"intent": "cancel_order", "entities": {}}

        # if user is browsing a menu, most messages are probably item names
        # check this early so "1 shahi gulab jamun" doesn't match "hi" greeting
        if session.state in [ConversationState.BROWSING_MENU, ConversationState.ORDERING]:
            # checkout shortcuts still work
            if words & {"checkout", "proceed", "done"}:
                return {"intent": "checkout", "entities": {}}
            if words & {"cart"}:
                return {"intent": "show_cart", "entities": {}}
            if "veg only" in msg or "only veg" in msg:
                return {"intent": "filter_veg", "entities": {"veg_only": True}}
            if words & {"menu"}:
                return {"intent": "show_menu", "entities": {}}
            # anything else while browsing menu → treat as add to cart
            return {"intent": "add_to_cart", "entities": {"items": [{"name": msg, "quantity": 1}]}}

        # greetings - use word-level matching so "shahi" doesn't match "hi"
        if words & {"hi", "hello", "hey", "hola", "namaste"}:
            return {"intent": "greet", "entities": {}}

        # help
        if msg in ["help", "/help", "what can you do"]:
            return {"intent": "help", "entities": {}}

        # reset
        if any(phrase in msg for phrase in ["start over", "reset", "new order", "fresh start"]):
            return {"intent": "start_over", "entities": {}}

        # track order
        if any(phrase in msg for phrase in ["track", "order status", "where is my"]):
            return {"intent": "track_order", "entities": {}}

        # show cart
        if any(phrase in msg for phrase in ["cart", "my order", "my items"]):
            return {"intent": "show_cart", "entities": {}}

        # checkout
        if any(phrase in msg for phrase in ["checkout", "place order", "order now", "proceed"]):
            return {"intent": "checkout", "entities": {}}

        # menu
        if any(phrase in msg for phrase in ["menu", "what do you have", "what's available"]):
            return {"intent": "show_menu", "entities": {}}

        # veg filter
        if any(phrase in msg for phrase in ["veg only", "vegetarian", "only veg", "veg items"]):
            return {"intent": "filter_veg", "entities": {"veg_only": True}}

        # restaurant selection by number
        if msg.isdigit() and session.state in [ConversationState.SEARCHING, ConversationState.IDLE]:
            return {"intent": "select_restaurant", "entities": {"restaurant_index": int(msg)}}

        # search by location or cuisine
        from app.mock_data.swiggy_data import LOCATIONS, CUISINE_TYPES
        for loc in LOCATIONS:
            if loc.lower() in msg:
                return {"intent": "search_restaurants", "entities": {"location": loc}}
        for cuisine in CUISINE_TYPES:
            if cuisine.lower() in msg:
                return {"intent": "search_restaurants", "entities": {"cuisine": cuisine}}

        # add to cart keywords
        if any(phrase in msg for phrase in ["add", "order", "want", "give me", "get me", "i'll have"]):
            return {"intent": "add_to_cart", "entities": {"items": [{"name": msg, "quantity": 1}]}}

        # restaurant search keywords
        if words & {"restaurant", "restaurants", "show", "find", "search", "near"}:
            return {"intent": "search_restaurants", "entities": {"query": msg}}

        # fallback
        return {"intent": "search_restaurants", "entities": {"query": msg}}

    async def _handle_intent(self, user_id: str, intent_data: dict, original_message: str) -> str:
        """Route intent to the appropriate handler"""
        intent = intent_data.get("intent", "unknown")
        entities = intent_data.get("entities", {})
        session = session_service.get_session(user_id)

        handlers = {
            "greet": self._handle_greet,
            "search_restaurants": self._handle_search,
            "select_restaurant": self._handle_select_restaurant,
            "show_menu": self._handle_show_menu,
            "show_category": self._handle_show_category,
            "filter_veg": self._handle_filter_veg,
            "add_to_cart": self._handle_add_to_cart,
            "remove_from_cart": self._handle_remove_from_cart,
            "show_cart": self._handle_show_cart,
            "clear_cart": self._handle_clear_cart,
            "checkout": self._handle_checkout,
            "provide_address": self._handle_provide_address,
            "confirm_order": self._handle_confirm_order,
            "cancel_order": self._handle_cancel_order,
            "track_order": self._handle_track_order,
            "order_status": self._handle_track_order,
            "help": self._handle_help,
            "start_over": self._handle_start_over,
            "ask_about_item": self._handle_ask_about_item,
        }

        handler = handlers.get(intent, self._handle_unknown)
        return await handler(user_id, entities, original_message)

    async def _handle_greet(self, user_id: str, entities: dict, message: str) -> str:
        session = session_service.get_session(user_id)
        name = session.user_name or ""
        name_greeting = f", {name}" if name else ""
        return (
            f"👋 *Hello{name_greeting}! Welcome to Swiggy Order Bot!*\n\n"
            f"🍕🍔🍗🥘🍜\n\n"
            f"I'm your AI-powered food ordering assistant. I can help you:\n\n"
            f"🔍 Find restaurants near you\n"
            f"📋 Browse menus and discover dishes\n"
            f"🛒 Place orders with natural conversation\n"
            f"📦 Track your deliveries in real-time\n\n"
            f"*Just tell me what you're craving!* For example:\n"
            f"• \"Show me pizza places in Madhapur\"\n"
            f"• \"I want biryani\"\n"
            f"• \"Find restaurants near HITEC City\"\n\n"
            f"Type *help* anytime for more options. Let's get started! 🚀"
        )

    async def _handle_search(self, user_id: str, entities: dict, message: str) -> str:
        location = entities.get("location", "")
        cuisine = entities.get("cuisine", "")
        query = entities.get("query", entities.get("restaurant_name", ""))
        veg_only = entities.get("veg_only", False)

        results = restaurant_service.search_restaurants(
            query=query, location=location, cuisine=cuisine, veg_only=veg_only
        )

        session_service.set_search_results(user_id, results)
        session_service.update_state(user_id, ConversationState.SEARCHING)

        if not results:
            search_term = query or cuisine or location or message
            return (
                f"😕 Sorry, I couldn't find any restaurants matching \"{search_term}\".\n\n"
                f"Try searching by:\n"
                f"• Location: \"restaurants in Madhapur\"\n"
                f"• Cuisine: \"pizza places\" or \"biryani\"\n"
                f"• Name: \"Domino's\" or \"Meghana\"\n\n"
                f"📍 Available locations: {', '.join(restaurant_service.get_available_locations()[:8])}"
            )

        search_label = query or cuisine or location or "your search"
        msg = f"🍽️ *Here are the top restaurants for \"{search_label}\":*\n\n"
        for i, r in enumerate(results[:8]):
            veg_label = " 🟢 Pure Veg" if r["is_veg"] else ""
            msg += f"*{i + 1}. {r['image']} {r['name']}*{veg_label}\n"
            total_str = f"{r['total_ratings'] / 1000:.1f}k" if r['total_ratings'] >= 1000 else str(r['total_ratings'])
            msg += f"   ⭐ {r['rating']} ({total_str}+ ratings)\n"
            msg += f"   🕐 {r['delivery_time']} | 💰 ₹{r['cost_for_two']} for two\n"
            msg += f"   📍 {r['location']}\n"
            if r.get("offers"):
                msg += f"   🏷️ {r['offers'][0]}\n"
            msg += "\n"

        msg += "\n📝 *Reply with a restaurant number or name to see their menu!*"
        return msg

    async def _handle_select_restaurant(self, user_id: str, entities: dict, message: str) -> str:
        session = session_service.get_session(user_id)

        restaurant = None

        # Try by index
        index = entities.get("restaurant_index")
        if index and session.search_results:
            idx = int(index) - 1  # Convert to 0-based
            restaurant = restaurant_service.get_restaurant_by_index(idx, session.search_results)

        # Try by name
        if not restaurant:
            name = entities.get("restaurant_name", message)
            restaurant = restaurant_service.get_restaurant_by_name(name)

        if not restaurant:
            return "😕 I couldn't find that restaurant. Please try again with a number from the list or a restaurant name."

        session_service.set_selected_restaurant(user_id, restaurant["id"])
        session_service.update_state(user_id, ConversationState.BROWSING_MENU)

        return self._format_menu(restaurant, user_id=user_id)

    def _format_menu(self, restaurant: dict, category: str = None, veg_only: bool = False, user_id: str = None) -> str:
        """Format restaurant menu with numbered items for easy selection"""
        msg = f"📋 *Menu - {restaurant['image']} {restaurant['name']}*\n"
        msg += f"⭐ {restaurant['rating']} | 🕐 {restaurant['delivery_time']} | 🚚 Delivery: ₹{restaurant['delivery_fee']}\n"
        if restaurant.get("offers"):
            msg += f"🏷️ {restaurant['offers'][0]}\n"
        msg += "\n"

        menu = restaurant["menu"]
        if category:
            cat_lower = category.lower()
            for cat_name, items in menu.items():
                if cat_lower in cat_name.lower():
                    menu = {cat_name: items}
                    break

        item_num = 1
        items_map = {}  # number -> item data

        for cat_name, items in menu.items():
            if not items:
                continue
            if veg_only:
                items = [i for i in items if i["is_veg"]]
                if not items:
                    continue

            msg += f"━━━ *{cat_name}* ━━━\n"
            for item in items:
                veg_icon = "🟢" if item["is_veg"] else "🔴"
                bestseller = " ⭐ Bestseller" if item.get("bestseller") else ""
                size_info = f" ({item['size']})" if item.get("size") else ""
                msg += f"*{item_num}.* {veg_icon} *{item['name']}*{size_info}{bestseller}\n"
                msg += f"   ₹{item['price']} — {item['description']}\n\n"
                items_map[str(item_num)] = item
                item_num += 1

        # store the mapping in session so user can pick by number
        if user_id:
            session = session_service.get_session(user_id)
            session.menu_items_map = items_map

        msg += "\n🛒 *To order, reply with item number or name!*\n"
        msg += "Examples:\n"
        msg += "• \"3\" to add item #3\n"
        msg += "• \"1 Margherita and 2 Garlic Bread\"\n"
        msg += "• \"Show me veg items only\""
        return msg

    async def _handle_show_menu(self, user_id: str, entities: dict, message: str) -> str:
        session = session_service.get_session(user_id)
        if not session.selected_restaurant_id:
            return "🍽️ You haven't selected a restaurant yet. Try searching for restaurants first!\n\nExample: \"Show me restaurants in Madhapur\""

        restaurant = restaurant_service.get_restaurant_by_id(session.selected_restaurant_id)
        if not restaurant:
            return "❌ Restaurant not found. Please search again."

        return self._format_menu(restaurant, user_id=user_id)

    async def _handle_show_category(self, user_id: str, entities: dict, message: str) -> str:
        session = session_service.get_session(user_id)
        if not session.selected_restaurant_id:
            return "🍽️ Please select a restaurant first."

        restaurant = restaurant_service.get_restaurant_by_id(session.selected_restaurant_id)
        category = entities.get("category", "")
        return self._format_menu(restaurant, category=category, user_id=user_id)

    async def _handle_filter_veg(self, user_id: str, entities: dict, message: str) -> str:
        session = session_service.get_session(user_id)
        if not session.selected_restaurant_id:
            return "🍽️ Please select a restaurant first."

        restaurant = restaurant_service.get_restaurant_by_id(session.selected_restaurant_id)
        return self._format_menu(restaurant, veg_only=True, user_id=user_id)

    async def _handle_add_to_cart(self, user_id: str, entities: dict, message: str) -> str:
        session = session_service.get_session(user_id)
        if not session.selected_restaurant_id:
            return "🍽️ Please select a restaurant first before ordering.\n\nTry: \"Show me restaurants in Madhapur\""

        items_to_add = entities.get("items", [])
        if not items_to_add:
            return "🤔 I couldn't understand what you'd like to order. Could you please specify the item name and quantity?\n\nExample: \"2 Margherita Pizza\" or \"1 Garlic Bread\" or just type an item number from the menu"

        added_items = []
        not_found = []

        for item_request in items_to_add:
            item_name = item_request.get("name", "")
            quantity = item_request.get("quantity", 1)
            size = item_request.get("size")

            # first check if it's a menu number (e.g. user typed "3" or "5")
            msg_stripped = message.strip()
            if msg_stripped.isdigit() and session.menu_items_map:
                item_data = session.menu_items_map.get(msg_stripped)
                if item_data:
                    cart_item = CartItem(
                        item_id=item_data["id"],
                        name=item_data["name"],
                        size=item_data.get("size"),
                        price=item_data["price"],
                        quantity=1,
                        is_veg=item_data["is_veg"],
                    )
                    session_service.add_to_cart(user_id, cart_item)
                    added_items.append(f"1x {item_data['name']}")
                    continue
                else:
                    not_found.append(f"Item #{msg_stripped}")
                    continue

            # search for the item by name in restaurant menu
            matches = restaurant_service.find_menu_item(session.selected_restaurant_id, item_name)

            if matches:
                if size:
                    size_matches = [m for m in matches if m.get("size", "").lower() == size.lower()]
                    if size_matches:
                        matches = size_matches

                best_match = matches[0]
                cart_item = CartItem(
                    item_id=best_match["id"],
                    name=best_match["name"],
                    size=best_match.get("size"),
                    price=best_match["price"],
                    quantity=quantity,
                    is_veg=best_match["is_veg"],
                )
                session_service.add_to_cart(user_id, cart_item)
                added_items.append(f"{quantity}x {best_match['name']}")
            else:
                not_found.append(item_name)

        session_service.update_state(user_id, ConversationState.ORDERING)

        response = ""
        if added_items:
            response += f"✅ Added to cart: {', '.join(added_items)}\n\n"

        if not_found:
            response += f"❌ Couldn't find: {', '.join(not_found)}\n\n"

        # Show current cart
        response += self._format_cart(user_id)
        response += "\n\n💡 You can:\n• Add more items\n• Say \"checkout\" to place your order\n• Say \"remove [item]\" to remove an item"

        return response

    async def _handle_remove_from_cart(self, user_id: str, entities: dict, message: str) -> str:
        items = entities.get("items", [])
        item_name = entities.get("item_query", "")
        if items:
            item_name = items[0].get("name", item_name)

        if not item_name:
            return "🤔 Which item would you like to remove? Please specify the item name."

        removed = session_service.remove_from_cart(user_id, item_name)
        if removed:
            response = f"✅ Removed from cart.\n\n"
            cart = session_service.get_cart(user_id)
            if cart:
                response += self._format_cart(user_id)
            else:
                response += "🛒 Your cart is now empty."
            return response
        return f"❌ Couldn't find \"{item_name}\" in your cart."

    async def _handle_show_cart(self, user_id: str, entities: dict, message: str) -> str:
        cart = session_service.get_cart(user_id)
        if not cart:
            return "🛒 Your cart is empty. Browse a restaurant menu and add some items!"

        return self._format_cart(user_id) + "\n\n💡 Say \"checkout\" to place your order or add more items."

    async def _handle_clear_cart(self, user_id: str, entities: dict, message: str) -> str:
        session_service.clear_cart(user_id)
        return "🗑️ Cart cleared. You can start adding items again!"

    def _format_cart(self, user_id: str) -> str:
        """Format cart for display"""
        session = session_service.get_session(user_id)
        cart = session.cart
        if not cart:
            return "🛒 Your cart is empty."

        restaurant = restaurant_service.get_restaurant_by_id(session.selected_restaurant_id)
        rest_name = restaurant["name"] if restaurant else "Restaurant"
        delivery_fee = restaurant["delivery_fee"] if restaurant else 0

        subtotal = sum(i.price * i.quantity for i in cart)
        tax = round(subtotal * 0.05)
        total = subtotal + tax + delivery_fee

        msg = f"🛒 *Your Order from {rest_name}:*\n\n"
        for item in cart:
            veg_icon = "🟢" if item.is_veg else "🔴"
            size_info = f" ({item.size})" if item.size else ""
            item_total = item.price * item.quantity
            msg += f"{veg_icon} {item.name}{size_info} × {item.quantity} — ₹{item_total}\n"

        msg += f"\n━━━━━━━━━━━━━━━\n"
        msg += f"Subtotal: ₹{subtotal}\n"
        msg += f"GST (5%): ₹{tax}\n"
        msg += f"Delivery Fee: ₹{delivery_fee}\n"
        msg += f"━━━━━━━━━━━━━━━\n"
        msg += f"*Total: ₹{total}*"

        return msg

    async def _handle_checkout(self, user_id: str, entities: dict, message: str) -> str:
        cart = session_service.get_cart(user_id)
        if not cart:
            return "🛒 Your cart is empty! Add some items first."

        session_service.update_state(user_id, ConversationState.AWAITING_ADDRESS)

        response = self._format_cart(user_id)
        response += "\n\n📍 *Please share your delivery address.*\n"
        response += "You can type your address or share your location."
        return response

    async def _handle_provide_address(self, user_id: str, entities: dict, message: str) -> str:
        address = entities.get("address", message)
        if not address or len(address.strip()) < 5:
            return "📍 Please provide a valid delivery address (e.g., \"Plot 42, Madhapur, Hyderabad\")"

        session_service.set_address(user_id, address)
        session_service.update_state(user_id, ConversationState.CONFIRMING_ORDER)

        session = session_service.get_session(user_id)
        restaurant = restaurant_service.get_restaurant_by_id(session.selected_restaurant_id)

        response = self._format_cart(user_id)
        response += f"\n\n📍 *Delivery Address:*\n{address}\n\n"
        response += f"💳 *Payment Method:* Cash on Delivery\n\n"
        response += f"Shall I place this order? Reply *Yes* to confirm or *No* to cancel."
        return response

    async def _handle_confirm_order(self, user_id: str, entities: dict, message: str) -> str:
        session = session_service.get_session(user_id)

        if not session.cart:
            return "🛒 Your cart is empty. Nothing to confirm!"

        if not session.pending_address:
            session_service.update_state(user_id, ConversationState.AWAITING_ADDRESS)
            return "📍 Please provide your delivery address first."

        restaurant = restaurant_service.get_restaurant_by_id(session.selected_restaurant_id)
        if not restaurant:
            return "❌ Restaurant not found. Please start over."

        # Place the order
        order = order_service.place_order(
            user_id=user_id,
            restaurant_id=session.selected_restaurant_id,
            restaurant_name=restaurant["name"],
            items=session.cart,
            address=session.pending_address,
            delivery_fee=restaurant["delivery_fee"],
        )

        session_service.set_current_order(user_id, order.order_id)
        session_service.clear_cart(user_id)
        session_service.update_state(user_id, ConversationState.ORDER_PLACED)

        response = (
            f"✅ *Order Placed Successfully!*\n\n"
            f"📦 *Order ID:* `{order.order_id}`\n"
            f"🏪 *Restaurant:* {order.restaurant_name}\n"
            f"🕐 *Estimated Delivery:* {order.estimated_delivery}\n"
            f"💰 *Total:* ₹{order.total}\n"
            f"💳 *Payment:* {order.payment_method}\n"
            f"📍 *Delivery to:* {order.address}\n\n"
            f"📱 I'll keep you updated on your order status!\n"
            f"💡 You can ask \"order status\" anytime to check."
        )

        return response

    async def _handle_cancel_order(self, user_id: str, entities: dict, message: str) -> str:
        session = session_service.get_session(user_id)

        # If in confirming state, just cancel the checkout
        if session.state == ConversationState.CONFIRMING_ORDER:
            session_service.update_state(user_id, ConversationState.ORDERING)
            return "❌ Order cancelled. Your cart items are still saved.\n\n💡 You can modify your cart or say \"checkout\" when ready."

        # If there's an active order, try to cancel it
        if session.current_order_id:
            order = order_service.cancel_order(session.current_order_id)
            if order:
                return f"❌ Order {order.order_id} has been cancelled."
            return "⚠️ Sorry, this order can't be cancelled at this stage."

        return "🤔 There's no active order to cancel."

    async def _handle_track_order(self, user_id: str, entities: dict, message: str) -> str:
        session = session_service.get_session(user_id)

        order = None
        if session.current_order_id:
            order = order_service.get_order(session.current_order_id)

        if not order:
            order = order_service.get_latest_order(user_id)

        if not order:
            return "📦 You don't have any active orders. Would you like to order something?"

        status_icons = {
            "placed": "📦",
            "confirmed": "✅",
            "preparing": "👨‍🍳",
            "out_for_delivery": "🚴",
            "delivered": "🎉",
            "cancelled": "❌",
        }

        status_texts = {
            "placed": "Order Placed",
            "confirmed": "Order Confirmed",
            "preparing": "Being Prepared",
            "out_for_delivery": "Out for Delivery",
            "delivered": "Delivered",
            "cancelled": "Cancelled",
        }

        steps = ["confirmed", "preparing", "out_for_delivery", "delivered"]
        current_idx = steps.index(order.status.value) if order.status.value in steps else -1

        msg = f"📦 *Order Status - {order.order_id}*\n\n"
        msg += f"🏪 {order.restaurant_name}\n"
        msg += f"💰 Total: ₹{order.total}\n\n"

        for i, step in enumerate(steps):
            emoji = "🟢" if i <= current_idx else "⚪"
            text = status_texts.get(step, step)
            current = " ← Current" if i == current_idx else ""
            msg += f"{emoji} {text}{current}\n"

        if order.delivery_partner and order.status.value in ["out_for_delivery"]:
            msg += f"\n🏍️ *Delivery Partner:* {order.delivery_partner}\n"
            msg += f"📞 *Contact:* {order.delivery_partner_phone}\n"

        if order.status.value == "delivered":
            msg += f"\n🎉 *Your order has been delivered! Enjoy your meal!*"

        return msg

    async def _handle_help(self, user_id: str, entities: dict, message: str) -> str:
        return (
            "🤖 *Swiggy Order Bot - Help*\n\n"
            "Here's what I can do for you:\n\n"
            "🔍 *Find Restaurants*\n"
            "• \"Show restaurants in Madhapur\"\n"
            "• \"Pizza places near me\"\n"
            "• \"Find biryani restaurants\"\n"
            "• \"Search for Domino's\"\n\n"
            "📋 *Browse Menu*\n"
            "• Select a restaurant to see its menu\n"
            "• \"Show veg items only\"\n"
            "• \"What's the bestseller?\"\n\n"
            "🛒 *Place Orders*\n"
            "• \"Order 2 Margherita pizzas\"\n"
            "• \"Add garlic bread to my order\"\n"
            "• \"Remove chicken wings\"\n"
            "• \"Show my cart\"\n\n"
            "📦 *Track Orders*\n"
            "• \"Order status\"\n"
            "• \"Track my order\"\n\n"
            "❓ *Other*\n"
            "• \"Help\" - Show this message\n"
            "• \"Start over\" - Reset and start fresh\n"
            "• \"Cancel order\" - Cancel current order"
        )

    async def _handle_start_over(self, user_id: str, entities: dict, message: str) -> str:
        session_service.reset_session(user_id)
        return (
            "🔄 *Fresh start!*\n\n"
            "Your previous session has been cleared.\n"
            "What would you like to order today? 🍽️\n\n"
            "Try: \"Show me restaurants in Madhapur\" or \"I want pizza\""
        )

    async def _handle_ask_about_item(self, user_id: str, entities: dict, message: str) -> str:
        session = session_service.get_session(user_id)
        if not session.selected_restaurant_id:
            return "🍽️ Please select a restaurant first to ask about items."

        item_query = entities.get("item_query", message)
        matches = restaurant_service.find_menu_item(session.selected_restaurant_id, item_query)

        if not matches:
            return f"😕 I couldn't find \"{item_query}\" in the menu. Try browsing the full menu."

        item = matches[0]
        veg_icon = "🟢 Veg" if item["is_veg"] else "🔴 Non-Veg"
        size_info = f" ({item.get('size', '')})" if item.get("size") else ""
        bestseller = " ⭐ Bestseller!" if item.get("bestseller") else ""

        return (
            f"*{item['name']}*{size_info} {veg_icon}{bestseller}\n\n"
            f"💰 Price: ₹{item['price']}\n"
            f"⭐ Rating: {item.get('rating', 'N/A')}\n"
            f"📝 {item['description']}\n\n"
            f"Would you like to add this to your cart?"
        )

    async def _handle_unknown(self, user_id: str, entities: dict, message: str) -> str:
        session = session_service.get_session(user_id)

        if session.state == ConversationState.IDLE:
            return (
                "🤔 I'm not sure what you're looking for. Here are some things you can try:\n\n"
                "• \"Show me restaurants in Madhapur\"\n"
                "• \"I want pizza\"\n"
                "• \"Find biryani near HITEC City\"\n\n"
                "Type *help* for more options."
            )

        return (
            "🤔 I didn't quite understand that. Could you try again?\n\n"
            "💡 Tip: Be specific with what you'd like, e.g.:\n"
            "• \"Add 2 margherita pizza\"\n"
            "• \"Show menu\"\n"
            "• \"Checkout\""
        )


# Singleton instance
gemini_agent = GeminiAgent()
