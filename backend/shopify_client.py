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
            shopify.Session.setup(
                api_key=os.getenv('SHOPIFY_API_KEY'),
                secret=os.getenv('SHOPIFY_API_SECRET')
            )
            self.session = shopify.Session(shop_url, '2024-01', access_token)
            shopify.ShopifyResource.activate_session(self.session)
            self.client = shopify.GraphQL()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Shopify session: {str(e)}"
            )

    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GraphQL query and return parsed result."""
        try:
            result = self.client.execute(query, variables=variables)
            
            # Handle different response types
            if isinstance(result, str):
                result = json.loads(result)
            elif hasattr(result, 'parsed'):
                result = result.parsed
                
            # Check for GraphQL errors
            if 'errors' in result:
                error_messages = '; '.join(error.get('message', 'Unknown error') for error in result['errors'])
                raise HTTPException(
                    status_code=400,
                    detail=f"GraphQL Error: {error_messages}"
                )
                
            return result['data'] if 'data' in result else result
            
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid GraphQL response: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"GraphQL query failed: {str(e)}"
            )

    def fetch_products(self, limit: int = 250) -> List[Dict[str, Any]]:
        """Fetch products using GraphQL."""
        query = '''
        query ($limit: Int!) {
            products(first: $limit) {
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
        '''
        
        result = self.execute_query(query, variables={"limit": limit})
        products = []
        
        for edge in result['products']['edges']:
            product = edge['node']
            products.append({
                "id": int(product['id'].split('/')[-1]),
                "title": product['title'],
                "variants": [{
                    "id": int(variant['node']['id'].split('/')[-1]),
                    "title": variant['node']['title'],
                    "price": float(variant['node']['price']),
                    "sku": variant['node']['sku'],
                    "inventory_quantity": variant['node']['inventoryQuantity']
                } for variant in product['variants']['edges']],
                "vendor": product['vendor']
            })
            
        return products

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
        
        return self.execute_query(mutation, variables={"input": order_data})

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
        
        return self.execute_query(mutation, variables=variables)

    def get_inventory_item_id(self, variant_id: str) -> str:
        """Get inventory item ID for a variant."""
        query = '''
        query getInventoryItem($id: ID!) {
            productVariant(id: $id) {
                inventoryItem {
                    id
                }
            }
        }
        '''
        
        result = self.execute_query(query, variables={"id": variant_id})
        if not result.get('productVariant', {}).get('inventoryItem', {}).get('id'):
            raise HTTPException(
                status_code=404,
                detail=f"No inventory item found for variant {variant_id}"
            )
            
        return result['productVariant']['inventoryItem']['id']

    def get_location_id(self) -> str:
        """Get the first location ID."""
        query = '''
        query {
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
        if not result.get('locations', {}).get('edges'):
            raise HTTPException(
                status_code=404,
                detail="No locations found in the store"
            )
            
        return result['locations']['edges'][0]['node']['id']

    def __del__(self):
        """Clean up Shopify session."""
        shopify.ShopifyResource.clear_session() 