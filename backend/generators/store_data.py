"""
Store data operations for generating related synthetic data.
"""
import shopify
from typing import List, Dict, Any
import random
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

def fetch_store_products() -> List[Dict[str, Any]]:
    """Fetch all products from the store using cursor-based pagination."""
    products = []
    
    try:
        # Get first page of products
        logger.info("Counting total products in store...")
        product_count = shopify.Product.count()
        logger.info(f"Found {product_count} products in store")
        
        if product_count == 0:
            logger.warning("No products found in store")
            return []

        # Use Shopify's recommended pagination
        logger.info("Initializing GraphQL query...")
        query = shopify.GraphQL()
        products_query = '''
        query {
          products(first: 250) {
            edges {
              node {
                id
                title
                vendor
                variants(first: 250) {
                  edges {
                    node {
                      id
                      title
                      price
                      sku
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        '''
        
        logger.debug("Executing GraphQL query...")
        result = query.execute(products_query)
        logger.debug(f"GraphQL response type: {type(result)}")
        
        # Handle both string and object responses
        if isinstance(result, str):
            logger.debug("Parsing string response as JSON")
            try:
                result = json.loads(result)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.debug(f"Response content: {result[:200]}...")  # Log first 200 chars
                raise
        elif hasattr(result, 'parsed'):
            logger.debug("Using parsed attribute from response")
            result = result.parsed
        elif not isinstance(result, dict):
            error_msg = f"Unexpected response type: {type(result)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Process products from GraphQL response
        if 'data' in result and 'products' in result['data']:
            logger.info("Processing products from GraphQL response")
            for edge in result['data']['products']['edges']:
                product = edge['node']
                try:
                    # Extract numeric ID from the GraphQL ID (format: gid://shopify/Product/123)
                    product_id = int(product['id'].split('/')[-1])
                    processed_product = {
                        "id": product_id,
                        "title": product['title'],
                        "variants": [{
                            "id": int(variant['node']['id'].split('/')[-1]),
                            "title": variant['node']['title'],
                            "price": float(variant['node']['price']),
                            "sku": variant['node']['sku']
                        } for variant in product['variants']['edges']],
                        "vendor": product['vendor']
                    }
                    products.append(processed_product)
                    logger.debug(f"Processed product {product_id}: {product['title']}")
                except (KeyError, ValueError, IndexError) as e:
                    logger.error(f"Error processing product {product.get('id', 'unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Successfully processed {len(products)} products")
        else:
            logger.error("Invalid GraphQL response structure")
            if 'errors' in result:
                logger.error(f"GraphQL errors: {result['errors']}")
            logger.debug(f"Response content: {result}")
            raise ValueError("Invalid GraphQL response structure")
        
        return products
        
    except Exception as e:
        logger.exception(f"Error fetching products: {str(e)}")
        return []

def generate_synthetic_order(products: List[Dict[str, Any]], date_range_days: int = 30) -> Dict[str, Any]:
    """Generate a synthetic order using real products from the store."""
    if not products:
        raise ValueError("No products available to generate orders")
        
    # Select 1-3 random products for the order
    order_products = random.sample(products, k=random.randint(1, min(3, len(products))))
    
    # Calculate total and create line items
    line_items = []
    total_price = 0
    
    for product in order_products:
        variant = random.choice(product["variants"])
        quantity = random.randint(1, 3)
        item_price = float(variant["price"])
        total_price += item_price * quantity
        
        line_items.append({
            "variant_id": variant["id"],
            "product_id": product["id"],
            "title": product["title"],
            "variant_title": variant["title"],
            "quantity": quantity,
            "price": item_price,
            "sku": variant["sku"]
        })
    
    # Generate random date within range
    current_time = datetime.now()
    earliest_date = current_time - timedelta(days=date_range_days)
    time_diff = current_time - earliest_date
    random_seconds = random.randint(0, int(time_diff.total_seconds()))
    order_date = current_time - timedelta(seconds=random_seconds)
    
    # Generate customer data
    customer = generate_synthetic_customer()
    
    return {
        "created_at": order_date.isoformat(),
        "customer": customer,
        "line_items": line_items,
        "total_price": round(total_price, 2),
        "financial_status": random.choice(["paid", "pending", "refunded"]),
        "fulfillment_status": random.choice([None, "fulfilled", "partial"]),
        "shipping_address": customer["default_address"]
    }

def generate_synthetic_customer() -> Dict[str, Any]:
    """Generate synthetic customer data."""
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego"]
    states = ["NY", "CA", "IL", "TX", "AZ", "PA"]
    
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
        "default_address": {
            "address1": f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Maple', 'Cedar'])} St",
            "city": random.choice(cities),
            "province_code": random.choice(states),
            "zip": f"{random.randint(10000, 99999)}",
            "country_code": "US",
            "name": f"{first_name} {last_name}",
            "phone": f"+1{random.randint(2000000000, 9999999999)}"
        }
    }

def generate_inventory_adjustment(product: Dict[str, Any]) -> Dict[str, Any]:
    """Generate synthetic inventory adjustment for a product."""
    variant = random.choice(product["variants"])
    adjustment = random.randint(-10, 20)  # Allow both positive and negative adjustments
    
    return {
        "variant_id": variant["id"],
        "product_id": product["id"],
        "adjustment": adjustment,
        "sku": variant["sku"],
        "reason": random.choice(["recount", "received", "damaged", "sold"]),
        "timestamp": (datetime.now() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )).isoformat()
    } 