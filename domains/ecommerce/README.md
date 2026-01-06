# E-commerce Domain 🛒

An e-commerce shopping assistant for product discovery, recommendations, cart management, and order support with RAG capabilities for policy and product information.

## Available Tools

The e-commerce domain includes 4 tools (3 domain-specific + 1 RAG retrieval tool):

### 1. `search_products`
Search the product catalog with optional filters for price and category.

**Parameters:**
- `query` (string, required): Search query such as a product name or category
- `max_price` (number, optional): Maximum price filter
- `category` (string, optional): Product category filter

**Returns:**
- List of matching products with SKU, name, price, and category
- Source indicator (mock-catalog)

**Example queries:**
- "Search for baking ingredients under $5"
- "Find dairy products"
- "What products do you have for making chocolate chip cookies?"

### 2. `create_cart`
Create or update a shopping cart with items and quantities.

**Parameters:**
- `items` (array, required): List of items to add, each with:
  - `sku` (string, required): Product SKU
  - `quantity` (integer, required): Quantity to add
- `cart_id` (string, optional): Cart ID to update an existing cart. If not provided, a new cart will be created.

**Returns:**
- `cart_id`: Unique cart identifier (new or existing)
- `items`: List of items with prices and line totals
- `total`: Total cart value
- `currency`: Currency code (USD)

**Example queries:**
- "Add 2 eggs and 1 carton of milk to my cart"
- "Create a cart with 3 bags of flour and 2 sticks of butter"
- "Add 1 box of baking soda to my cart"
- "Update cart CART-1234 with 2 more eggs"

### 3. `check_order_status`
Check the status of an order by its ID. Statuses are randomly returned so response will be inconsistent.

**Parameters:**
- `order_id` (string, required): Order identifier

**Returns:**
- `order_id`: Order identifier
- `status`: Current order status (processing, shipped, out_for_delivery, delivered)
- `eta`: Estimated delivery timeframe
- `carrier`: Shipping carrier name
- `source`: Data source indicator

**Example queries:**
- "What is the status of order #12345?"
- "Check the status of order ORD-7890"
- "Has my order 2323 been delivered?"

### 4. `retrieve_ecommerce_documents` (RAG Tool)
Automatically added when RAG is enabled. Retrieves information from the e-commerce knowledge base.

**What it searches:**
- Shipping policies and delivery options (standard, expedited, free shipping thresholds)
- Return and refund policies (timeframes, eligibility, process)
- Payment and billing policies (accepted methods, processing, refunds, disputes)
- Billing information and payment security

This tool is invoked automatically by the agent when you ask questions about policies, billing, or general shopping guidance.

**Example queries that trigger the RAG tool:**
- "What's the minimum order amount for free shipping?"
- "How long does expedited shipping take?"
- "What is the return policy for unused items?"
- "What payment methods do you accept?"
- "How are refunds processed?"
- "What are your shipping options?"

## Mock Product Catalog

The domain includes a mock product catalog with baking and cooking essentials:
- **Dairy**: Eggs, milk, butter, cream cheese
- **Baking**: Flour, sugar, baking powder, baking soda, vanilla extract
- **Food**: Salt, chocolate, various ingredients
- Products are searchable by name, category, and price range via the search_products tool

## Knowledge Base Documents

The RAG system includes comprehensive documentation:
- **Shipping Policy**: Standard (3-5 days) and expedited (1-2 days) shipping options, free shipping threshold ($50+)
- **Return Policy**: 30-day return window, eligibility requirements, refund process, exchanges
- **Payment & Billing Policy**: Accepted payment methods, processing information, refund procedures, billing disputes, and payment security

## Galileo Project

Logs to: `galileo-demo-ecommerce` unless custom project is configured

## Try It Out!

Start the app and navigate to: `http://localhost:8501/ecommerce`

**Quick test queries:**

*Product search and cart (uses tools):*
1. "I want to make a cheesecake, what do I need?"
2. "Search for baking ingredients under $5"
3. "Add 2 eggs and 1 carton of milk to my cart"

*Policy and billing information (triggers RAG tool):*
1. "What's the minimum order amount for free shipping?"
2. "What is the return policy for unused items?"
3. "How long does expedited shipping take?"

> **Note:** This is a demo application designed to showcase Galileo's observability capabilities for e-commerce AI applications. It is NOT a real e-commerce platform and should NOT be used for actual purchases. All product data, orders, and transactions are simulated for demonstration purposes only.

