"""
AI-powered synthetic data generation using OpenAI.
"""
from typing import List, Dict, Any
from base_agent import OpenAIAgent
import json
from datetime import datetime, timedelta
import random
import yaml
from pathlib import Path

class AIDataGenerator:
    def __init__(self):
        # Load prompts from YAML
        prompts_path = Path(__file__).parent.parent / "prompts.yaml"
        with open(prompts_path) as f:
            self.prompts = yaml.safe_load(f)
            # Load response schemas
            self.order_response_schema = json.loads(self.prompts["order_response_schema"])
            self.inventory_response_schema = json.loads(self.prompts["inventory_response_schema"])

    def generate_orders(
        self,
        store_products: List[Dict[str, Any]],
        count: int = 5,
        date_range_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Generate synthetic orders."""
        if not store_products:
            raise ValueError("No products found in store. Please add products before generating orders.")

        agent = OpenAIAgent(
            instructions=self.prompts["order_instructions"],
            structured_output=self.order_response_schema
        )
        
        # Format products for the prompt with complete details
        products_preview = []
        for p in store_products[:5]:  # Limit to 5 products for prompt clarity
            variants = []
            for v in p['variants']:
                if v.get('id') and v.get('price'):  # Only include valid variants
                    variants.append({
                        'id': v['id'],
                        'title': v.get('title', 'Default Variant'),
                        'price': v['price'],
                        'sku': v.get('sku', ''),
                        'inventory_quantity': v.get('inventory_quantity', 0)
                    })
            if variants:  # Only include products with valid variants
                products_preview.append({
                    'id': p['id'],
                    'title': p['title'],
                    'variants': variants
                })
        
        if not products_preview:
            raise ValueError("No valid products with variants found in store.")
        
        # Create a detailed example using real product data
        example_variant = products_preview[0]['variants'][0]
        
        # Show prices in the product list for reference
        product_list = json.dumps([{
            'title': p['title'],
            'variants': [{
                'id': v['id'],
                'title': v['title'],
                'price': v['price']  # Reference price for the AI
            } for v in p['variants']]
        } for p in products_preview], indent=2)
        
        current_date = datetime.utcnow()
        example_format = f"""
        Example order format using a real product from your store:
        {{
            "email": "customer@example.com",
            "tags": ["AI_GENERATED"],
            "lineItems": [
                {{
                    "variantId": "gid://shopify/ProductVariant/{example_variant['id']}",
                    "quantity": 1,
                    "taxable": true
                }}
            ],
            "shippingAddress": {{
                "address1": "123 Main St",
                "city": "Toronto",
                "province": "ON",
                "country": "CA",
                "zip": "M5V 2T6",
                "firstName": "John",
                "lastName": "Doe"
            }},
            "note": "Created via Synthetic Data Generator",
            "customAttributes": [
                {{"key": "source", "value": "synthetic_data"}},
                {{"key": "generated_at", "value": "{current_date.isoformat()}Z"}}
            ]
        }}

        Available products and variants:
        {product_list}
        """
        
        prompt = self.prompts["order_generation"].format(
            count=count,
            date_range_days=date_range_days,
            products_json=json.dumps(products_preview, indent=2)
        ) + example_format
        
        response = agent.run_message(prompt)
        orders = response.get('orders', [])
        
        # Validate and ensure each order has valid line items
        valid_orders = []
        for order in orders:
            # Ensure AI_GENERATED tag is present
            if 'tags' not in order:
                order['tags'] = ["AI_GENERATED"]
            elif "AI_GENERATED" not in order['tags']:
                order['tags'].append("AI_GENERATED")

            if not order.get('lineItems'):
                # Create a line item using a random valid product variant
                product = random.choice(products_preview)
                variant = random.choice(product['variants'])
                order['lineItems'] = [{
                    "variantId": f"gid://shopify/ProductVariant/{variant['id']}",
                    "quantity": random.randint(1, 3),
                    "taxable": True
                }]
            else:
                # Validate that all line items reference real products
                valid_line_items = []
                for item in order['lineItems']:
                    variant_id = str(item['variantId']).split('/')[-1] if isinstance(item.get('variantId'), str) else item.get('variantId')
                    # Check if this variant exists in our products
                    for product in products_preview:
                        for variant in product['variants']:
                            if str(variant['id']) == str(variant_id):
                                valid_line_items.append({
                                    "variantId": f"gid://shopify/ProductVariant/{variant['id']}",
                                    "quantity": int(item.get('quantity', 1)),
                                    "taxable": True
                                })
                                break
                order['lineItems'] = valid_line_items or [{
                    "variantId": f"gid://shopify/ProductVariant/{products_preview[0]['variants'][0]['id']}",
                    "quantity": 1,
                    "taxable": True
                }]
            
            # Distribute order dates evenly across the date range
            days_ago = random.uniform(0, date_range_days)
            hours_ago = random.uniform(0, 24)
            minutes_ago = random.uniform(0, 60)
            order_time = current_date - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            # Update generated_at to distributed time
            order["customAttributes"] = [
                {"key": "source", "value": "synthetic_data"},
                {"key": "generated_at", "value": order_time.isoformat() + "Z"}
            ]
            
            if order['lineItems']:  # Only add orders with valid line items
                valid_orders.append(order)
        
        # Ensure we have enough orders
        while len(valid_orders) < count and valid_orders:
            new_order = valid_orders[-1].copy()
            # Modify the line items slightly for variety
            for item in new_order['lineItems']:
                item['quantity'] = random.randint(1, 3)
            
            # Distribute new order dates evenly as well
            days_ago = random.uniform(0, date_range_days)
            hours_ago = random.uniform(0, 24)
            minutes_ago = random.uniform(0, 60)
            order_time = current_date - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            new_order["customAttributes"] = [
                {"key": "source", "value": "synthetic_data"},
                {"key": "generated_at", "value": order_time.isoformat() + "Z"}
            ]
            valid_orders.append(new_order)
        
        return valid_orders[:count]

    def generate_inventory_adjustments(
        self,
        store_products: List[Dict[str, Any]],
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate synthetic inventory adjustments."""
        agent = OpenAIAgent(
            instructions=self.prompts["inventory_instructions"],
            structured_output=self.inventory_response_schema
        )
        
        # Format products for the prompt
        products_preview = [{
            'id': p['id'],
            'title': p['title'],
            'variants': p['variants']
        } for p in store_products[:5]]
        
        prompt = self.prompts["inventory_generation"].format(
            count=count,
            products_json=json.dumps(products_preview, indent=2)
        )
        
        response = agent.run_message(prompt)
        adjustments = response.get('adjustments', [])
        
        # Ensure we have enough adjustments
        while len(adjustments) < count and adjustments:
            new_adj = adjustments[-1].copy()
            new_adj["timestamp"] = (
                datetime.fromisoformat(new_adj["timestamp"].replace("Z", "+00:00"))
                + timedelta(hours=random.randint(1, 24))
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            new_adj["adjustment"] = random.randint(-5, 10)
            adjustments.append(new_adj)
        
        return adjustments[:count] 