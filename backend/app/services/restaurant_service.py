"""
Restaurant Service - Handles restaurant search, menu retrieval, and filtering
Acts as a Mock Swiggy MCP Server / API client
"""
from typing import Optional
from app.mock_data.swiggy_data import RESTAURANTS, LOCATIONS, CUISINE_TYPES


class RestaurantService:
    """Service to interact with mock Swiggy data (simulating MCP/API integration)"""

    def __init__(self):
        self.restaurants = RESTAURANTS
        self.locations = LOCATIONS
        self.cuisine_types = CUISINE_TYPES

    def search_restaurants(self, query: str = "", location: str = "", cuisine: str = "", veg_only: bool = False) -> list:
        """
        Search restaurants by query, location, cuisine, or dietary preference.
        Simulates Swiggy's restaurant search API.
        """
        results = list(self.restaurants)
        query_lower = query.lower().strip() if query else ""
        location_lower = location.lower().strip() if location else ""
        cuisine_lower = cuisine.lower().strip() if cuisine else ""

        # Filter by location
        if location_lower:
            location_matches = [r for r in results if location_lower in r["location"].lower()]
            if location_matches:
                results = location_matches
            # If no exact location match, check address
            else:
                results = [r for r in results if location_lower in r["address"].lower()]

        # Filter by cuisine
        if cuisine_lower:
            results = [
                r for r in results
                if any(cuisine_lower in c.lower() for c in r["cuisine"])
            ]

        # Filter by query (name, cuisine, or general)
        if query_lower:
            query_results = []
            for r in results:
                name_match = query_lower in r["name"].lower()
                cuisine_match = any(query_lower in c.lower() for c in r["cuisine"])
                if name_match or cuisine_match:
                    query_results.append(r)
            if query_results:
                results = query_results

        # Filter veg only
        if veg_only:
            results = [r for r in results if r["is_veg"]]

        # Only return open restaurants
        results = [r for r in results if r["is_open"]]

        # Sort by rating (descending)
        results.sort(key=lambda x: x["rating"], reverse=True)

        return results

    def get_restaurant_by_id(self, restaurant_id: str) -> Optional[dict]:
        """Get a specific restaurant by ID"""
        for r in self.restaurants:
            if r["id"] == restaurant_id:
                return r
        return None

    def get_restaurant_by_name(self, name: str) -> Optional[dict]:
        """Get restaurant by name (fuzzy match)"""
        name_lower = name.lower().strip()
        for r in self.restaurants:
            if name_lower in r["name"].lower() or r["name"].lower() in name_lower:
                return r
        return None

    def get_restaurant_by_index(self, index: int, restaurant_list: list) -> Optional[dict]:
        """Get restaurant by index from a search result list"""
        if 0 <= index < len(restaurant_list):
            return restaurant_list[index]
        return None

    def get_menu(self, restaurant_id: str, category: str = None, veg_only: bool = False) -> Optional[dict]:
        """
        Get menu for a restaurant, optionally filtered by category or dietary preference.
        Simulates Swiggy's menu API.
        """
        restaurant = self.get_restaurant_by_id(restaurant_id)
        if not restaurant:
            return None

        menu = restaurant["menu"]

        if category:
            category_lower = category.lower()
            for cat_name, items in menu.items():
                if category_lower in cat_name.lower():
                    menu = {cat_name: items}
                    break

        if veg_only:
            filtered_menu = {}
            for cat_name, items in menu.items():
                veg_items = [item for item in items if item["is_veg"]]
                if veg_items:
                    filtered_menu[cat_name] = veg_items
            menu = filtered_menu

        return menu

    def find_menu_item(self, restaurant_id: str, item_query: str) -> list:
        """
        Find menu items matching a query within a restaurant.
        Returns list of matching items with their categories.
        """
        restaurant = self.get_restaurant_by_id(restaurant_id)
        if not restaurant:
            return []

        query_lower = item_query.lower().strip()
        matches = []

        for category, items in restaurant["menu"].items():
            for item in items:
                item_name_lower = item["name"].lower()
                # Check for exact or partial name match
                if query_lower in item_name_lower or item_name_lower in query_lower:
                    matches.append({**item, "category": category})

        return matches

    def get_bestsellers(self, restaurant_id: str) -> list:
        """Get bestseller items from a restaurant"""
        restaurant = self.get_restaurant_by_id(restaurant_id)
        if not restaurant:
            return []

        bestsellers = []
        for category, items in restaurant["menu"].items():
            for item in items:
                if item.get("bestseller"):
                    bestsellers.append({**item, "category": category})

        return bestsellers

    def get_available_locations(self) -> list:
        """Get list of available delivery locations"""
        return self.locations

    def get_cuisine_types(self) -> list:
        """Get list of available cuisine types"""
        return self.cuisine_types


# Singleton instance
restaurant_service = RestaurantService()
