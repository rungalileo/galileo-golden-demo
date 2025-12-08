import random
from typing import List, Dict, Any

def search_products(query: str, max_price: float = None, category: str = None) -> Dict[str, Any]:
    # Mock search returning sample products
    results = [
        {"sku": "001", "name": "egg carton", "price": 6.00, "category": "food"},
        {"sku": "002", "name": "milk", "price": 5.00, "category": "dairy"},
        {"sku": "003", "name": "flour", "price": 4.00, "category": "baking"},
        {"sku": "004", "name": "sugar", "price": 3.00, "category": "baking"},
        {"sku": "005", "name": "butter", "price": 2.00, "category": "dairy"},
        {"sku": "006", "name": "chocolate", "price": 2.00, "category": "food"},
        {"sku": "007", "name": "vanilla extract", "price": 4.00, "category": "baking"},
        {"sku": "008", "name": "salt", "price": 2.00, "category": "food"},
        {"sku": "009", "name": "baking soda", "price": 1.00, "category": "baking"},
        {"sku": "010", "name": "baking powder", "price": 1.00, "category": "baking"}
    ]
    filtered = [
        r for r in results
        if (max_price is None or r["price"] <= max_price)
        and (category is None or r["category"].lower() == category.lower())
    ]
    return {
        "query": query,
        "results": filtered or results,  # fall back to all if filters remove everything
        "source": "mock-catalog"
    }

def create_cart(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Simple cart builder that echoes items and computes a mock total
    total = 0.0
    cart_items = []
    for item in items:
        price = round(random.uniform(10, 200), 2)
        line_total = round(price * item.get("quantity", 1), 2)
        total += line_total
        cart_items.append({**item, "price": price, "line_total": line_total})
    return {
        "cart_id": f"CART-{random.randint(1000,9999)}",
        "items": cart_items,
        "currency": "USD",
        "total": round(total, 2),
        "note": "Mock cart created for demo purposes"
    }

def check_order_status(order_id: str) -> Dict[str, Any]:
    # Returns a deterministic but mock status
    statuses = ["processing", "shipped", "out_for_delivery", "delivered"]
    status = random.choice(statuses)
    return {
        "order_id": order_id,
        "status": status,
        "eta": "2-4 business days" if status != "delivered" else "delivered",
        "carrier": "Galileo Logistics",
        "source": "mock-order-system"
    }

TOOLS = [search_products, create_cart, check_order_status]