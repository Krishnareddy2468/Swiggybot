"""
Restaurant Service - Stubbed out (Moved to Zomato Realtime MCP)
Acts as a fallback for the frontend API routes.
"""
from typing import Optional


class RestaurantService:
    """Stubbed service to prevent frontend API from crashing"""

    def __init__(self):
        self.restaurants = []
        self.locations = ["Hyderabad", "Bangalore", "Mumbai"]
        self.cuisine_types = ["Pizza", "Biryani", "Chinese"]

    def search_restaurants(self, query: str = "", location: str = "", cuisine: str = "", veg_only: bool = False) -> list:
        return []

    def get_restaurant_by_id(self, restaurant_id: str) -> Optional[dict]:
        return None

    def get_restaurant_by_name(self, name: str) -> Optional[dict]:
        return None

    def get_restaurant_by_index(self, index: int, restaurant_list: list) -> Optional[dict]:
        return None

    def get_menu(self, restaurant_id: str, category: str = None, veg_only: bool = False) -> Optional[dict]:
        return {}

    def find_menu_item(self, restaurant_id: str, item_query: str) -> list:
        return []

    def get_bestsellers(self, restaurant_id: str) -> list:
        return []

    def get_available_locations(self) -> list:
        return self.locations

    def get_cuisine_types(self) -> list:
        return self.cuisine_types


# Singleton instance
restaurant_service = RestaurantService()
