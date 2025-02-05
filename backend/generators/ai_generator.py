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
            # Load schemas directly since they are now valid JSON
            self.order_schema = json.loads(self.prompts["order_schema"])
            self.inventory_schema = json.loads(self.prompts["inventory_schema"])

    def generate_orders(
        self,
        store_products: List[Dict[str, Any]],
        count: int = 5,
        date_range_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Generate synthetic orders."""
        # Define the expected response schema based on the YAML schema
        response_schema = {
            "type": "object",
            "properties": {
                "orders": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": self.order_schema,
                        "required": ["customer", "line_items", "created_at", "total_price"]
                    }
                }
            },
            "required": ["orders"]
        }

        agent = OpenAIAgent(
            instructions=self.prompts["order_instructions"],
            structured_output=response_schema
        )
        
        # Format products for the prompt
        products_preview = [{
            'id': p['id'],
            'title': p['title'],
            'variants': p['variants']
        } for p in store_products[:5]]
        
        prompt = self.prompts["order_generation"].format(
            count=count,
            date_range_days=date_range_days,
            products_json=json.dumps(products_preview, indent=2)
        )
        
        response = agent.run_message(prompt)
        orders = response.get('orders', [])
        
        # Ensure we have enough orders
        while len(orders) < count and orders:
            new_order = orders[-1].copy()
            new_order["created_at"] = (
                datetime.fromisoformat(new_order["created_at"].replace("Z", "+00:00"))
                + timedelta(hours=random.randint(1, 24))
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            orders.append(new_order)
        
        return orders[:count]

    def generate_inventory_adjustments(
        self,
        store_products: List[Dict[str, Any]],
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate synthetic inventory adjustments."""
        # Define the expected response schema based on the YAML schema
        response_schema = {
            "type": "object",
            "properties": {
                "adjustments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": self.inventory_schema,
                        "required": ["variant_id", "product_id", "adjustment", "reason", "timestamp"]
                    }
                }
            },
            "required": ["adjustments"]
        }

        agent = OpenAIAgent(
            instructions=self.prompts["inventory_instructions"],
            structured_output=response_schema
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