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

    def create_draft_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a draft order using GraphQL."""
        mutation = '''
        mutation draftOrderCreate($input: DraftOrderInput!) {
            draftOrderCreate(input: $input) {
                draftOrder {
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
        
        if not result or 'draftOrderCreate' not in result:
            raise HTTPException(status_code=500, detail="Failed to create draft order")
            
        user_errors = result['draftOrderCreate'].get('userErrors', [])
        if user_errors:
            error_messages = '; '.join(error.get('message', 'Unknown error') for error in user_errors)
            raise HTTPException(status_code=400, detail=f"Failed to create draft order: {error_messages}")
            
        return result['draftOrderCreate']

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

    def __del__(self):
        """Clean up Shopify session."""
        try:
            shopify.ShopifyResource.clear_session()
        except:
            pass 