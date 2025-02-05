"""
Shopify GraphQL client for standardized API operations.
"""
from typing import Dict, Any, Optional, List
import shopify
import json
from fastapi import HTTPException
import os

class ShopifyGraphQLClient:
    def __init__(self, shop_url: str, access_token: str):
        """Initialize Shopify GraphQL client."""
        try:
            self.session = shopify.Session(shop_url, '2024-01', access_token)
            shopify.ShopifyResource.activate_session(self.session)
            self.client = shopify.GraphQL()
            
            # Verify connection by making a simple query
            result = self.execute_query("""
                {
                    shop {
                        name
                    }
                }
            """)
            if not result or 'shop' not in result:
                raise Exception("Failed to verify shop connection")
                
        except Exception as e:
            shopify.ShopifyResource.clear_session()
            raise HTTPException(
                status_code=401,
                detail=f"Failed to authenticate with Shopify: {str(e)}"
            )

    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GraphQL query and return parsed result."""
        try:
            result = self.client.execute(query, variables=variables if variables else None)
            
            # Handle string responses (usually errors)
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    raise Exception(f"Invalid response format: {result}")
            
            # Check for GraphQL errors
            if isinstance(result, dict):
                if 'errors' in result:
                    error_messages = '; '.join(error.get('message', 'Unknown error') for error in result['errors'])
                    raise HTTPException(status_code=400, detail=f"GraphQL Error: {error_messages}")
                return result.get('data', {})
            
            raise Exception(f"Unexpected response format: {type(result)}")
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"GraphQL query failed: {str(e)}")

    def fetch_products(self, limit: int = 250) -> List[Dict[str, Any]]:
        """Fetch products using GraphQL."""
        query = '''
        {
            products(first: %d) {
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
                                    inventoryQuantity
                                }
                            }
                        }
                    }
                }
            }
        }
        ''' % limit
        
        result = self.execute_query(query)
        
        if not result or 'products' not in result:
            return []
            
        return [{
            "id": product['node']['id'].split('/')[-1],  # Extract ID from GID
            "title": product['node']['title'],
            "variants": [{
                "id": variant['node']['id'].split('/')[-1],  # Extract ID from GID
                "title": variant['node']['title'],
                "price": float(variant['node']['price']),
                "sku": variant['node']['sku'],
                "inventory_quantity": variant['node']['inventoryQuantity']
            } for variant in product['node']['variants']['edges']],
            "vendor": product['node']['vendor']
        } for product in result['products']['edges']]

    def create_regular_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a regular order using GraphQL."""
        mutation = '''
        mutation orderCreate($input: OrderInput!) {
            orderCreate(input: $input) {
                order {
                    id
                    totalPrice
                    createdAt
                    customer {
                        firstName
                        lastName
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        
        result = self.execute_query(mutation, variables={"input": order_data})
        
        if not result or 'orderCreate' not in result:
            raise HTTPException(status_code=500, detail="Failed to create order")
            
        user_errors = result['orderCreate'].get('userErrors', [])
        if user_errors:
            error_messages = '; '.join(error.get('message', 'Unknown error') for error in user_errors)
            raise HTTPException(status_code=400, detail=f"Failed to create order: {error_messages}")
            
        return result['orderCreate']

    def get_inventory_item_id(self, variant_id: str) -> str:
        """Get inventory item ID for a variant."""
        query = '''
        {
            productVariant(id: "%s") {
                inventoryItem {
                    id
                }
            }
        }
        ''' % variant_id
        
        result = self.execute_query(query)
        
        if not result or 'productVariant' not in result or not result['productVariant'].get('inventoryItem'):
            raise HTTPException(status_code=404, detail=f"No inventory item found for variant {variant_id}")
            
        return result['productVariant']['inventoryItem']['id']

    def get_location_id(self) -> str:
        """Get the first location ID."""
        query = '''
        {
            locations(first: 1) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
        '''
        
        result = self.execute_query(query)
        
        if not result or 'locations' not in result or not result['locations'].get('edges'):
            raise HTTPException(status_code=404, detail="No locations found in the store")
            
        return result['locations']['edges'][0]['node']['id']

    def adjust_inventory(self, inventory_item_id: str, location_id: str, delta: int, reason: str) -> Dict[str, Any]:
        """Adjust inventory quantity using GraphQL."""
        mutation = '''
        mutation inventoryAdjustQuantity($input: InventoryAdjustQuantityInput!) {
            inventoryAdjustQuantity(input: $input) {
                inventoryLevel {
                    id
                    available
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        
        variables = {
            "input": {
                "inventoryItemId": inventory_item_id,
                "locationId": location_id,
                "availableDelta": delta,
                "reason": reason.upper()
            }
        }
        
        result = self.execute_query(mutation, variables=variables)
        
        if not result or 'inventoryAdjustQuantity' not in result:
            raise HTTPException(status_code=500, detail="Failed to adjust inventory")
            
        user_errors = result['inventoryAdjustQuantity'].get('userErrors', [])
        if user_errors:
            error_messages = '; '.join(error.get('message', 'Unknown error') for error in user_errors)
            raise HTTPException(status_code=400, detail=f"Failed to adjust inventory: {error_messages}")
            
        return result['inventoryAdjustQuantity']

    def delete_ai_generated_orders(self) -> Dict[str, Any]:
        """Delete all orders tagged as AI_GENERATED."""
        # First query for AI generated orders
        query = '''
        {
            orders(first: 250, query: "tag:AI_GENERATED") {
                edges {
                    node {
                        id
                    }
                }
            }
        }
        '''
        
        result = self.execute_query(query)
        deleted_count = 0
        
        if result and 'orders' in result:
            for order in result['orders']['edges']:
                mutation = '''
                mutation orderDelete($input: OrderDeleteInput!) {
                    orderDelete(input: $input) {
                        deletedId
                        userErrors {
                            field
                            message
                        }
                    }
                }
                '''
                
                delete_result = self.execute_query(mutation, variables={
                    "input": {"id": order['node']['id']}
                })
                
                if delete_result and 'orderDelete' in delete_result:
                    if delete_result['orderDelete'].get('deletedId'):
                        deleted_count += 1
                    elif delete_result['orderDelete'].get('userErrors'):
                        errors = delete_result['orderDelete']['userErrors']
                        error_messages = '; '.join(error.get('message', 'Unknown error') for error in errors)
                        print(f"Error deleting order {order['node']['id']}: {error_messages}")
        
        return {"deleted_count": deleted_count}

    def reset_inventory_levels(self) -> Dict[str, Any]:
        """Reset inventory levels for all products to a base level."""
        # First get all products with their inventory
        products = self.fetch_products()
        location_id = self.get_location_id()
        adjusted_count = 0
        
        for product in products:
            for variant in product['variants']:
                try:
                    # Reset to a reasonable base level (e.g., 10)
                    current_quantity = variant['inventory_quantity']
                    if current_quantity != 10:
                        inventory_item_id = self.get_inventory_item_id(f"gid://shopify/ProductVariant/{variant['id']}")
                        adjustment = 10 - current_quantity
                        
                        self.adjust_inventory(
                            inventory_item_id=inventory_item_id,
                            location_id=location_id,
                            delta=adjustment,
                            reason="RESET"
                        )
                        adjusted_count += 1
                except Exception as e:
                    print(f"Error resetting inventory for variant {variant['id']}: {e}")
                    continue
        
        return {"adjusted_count": adjusted_count}

    def __del__(self):
        """Clean up Shopify session."""
        try:
            shopify.ShopifyResource.clear_session()
        except:
            pass 