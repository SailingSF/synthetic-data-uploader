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
        """Create a regular order using GraphQL via draft order process."""
        # First create a draft order
        create_mutation = '''
        mutation draftOrderCreate($input: DraftOrderInput!) {
            draftOrderCreate(input: $input) {
                draftOrder {
                    id
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        
        # Convert the order data to draft order format with all necessary fields
        draft_input = {
            "email": order_data.get("email"),
            "tags": order_data.get("tags", []),
            "lineItems": order_data.get("lineItems", []),
            "note": "Created via Synthetic Data Generator",
            "customAttributes": [{"key": "source", "value": "synthetic_data"}],
            "useCustomerDefaultAddress": False,
            "appliedDiscount": None  # No discount by default
        }
        
        result = self.execute_query(create_mutation, variables={"input": draft_input})
        
        if not result or 'draftOrderCreate' not in result:
            raise HTTPException(status_code=500, detail="Failed to create draft order")
            
        user_errors = result['draftOrderCreate'].get('userErrors', [])
        if user_errors:
            error_messages = '; '.join(error.get('message', 'Unknown error') for error in user_errors)
            raise HTTPException(status_code=400, detail=f"Failed to create draft order: {error_messages}")
        
        draft_order_id = result['draftOrderCreate']['draftOrder']['id']
        
        # Complete the draft order with more comprehensive response fields
        complete_mutation = '''
        mutation draftOrderComplete($id: ID!) {
            draftOrderComplete(id: $id) {
                draftOrder {
                    order {
                        id
                        name
                        totalPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        subtotalPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        totalTaxSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        createdAt
                        processedAt
                        displayFulfillmentStatus
                        displayFinancialStatus
                        customer {
                            firstName
                            lastName
                            email
                        }
                        shippingAddress {
                            address1
                            city
                            province
                            country
                            zip
                        }
                        tags
                        lineItems(first: 10) {
                            edges {
                                node {
                                    title
                                    quantity
                                    originalUnitPriceSet {
                                        shopMoney {
                                            amount
                                            currencyCode
                                        }
                                    }
                                    variant {
                                        id
                                        sku
                                        inventoryQuantity
                                        product {
                                            vendor
                                            productType
                                        }
                                    }
                                }
                            }
                        }
                        customAttributes {
                            key
                            value
                        }
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        
        complete_result = self.execute_query(complete_mutation, variables={"id": draft_order_id})
        
        if not complete_result or 'draftOrderComplete' not in complete_result:
            raise HTTPException(status_code=500, detail="Failed to complete draft order")
            
        user_errors = complete_result['draftOrderComplete'].get('userErrors', [])
        if user_errors:
            error_messages = '; '.join(error.get('message', 'Unknown error') for error in user_errors)
            raise HTTPException(status_code=400, detail=f"Failed to complete draft order: {error_messages}")
            
        return complete_result['draftOrderComplete']

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
                        displayFinancialStatus
                        displayFulfillmentStatus
                    }
                }
            }
        }
        '''
        
        result = self.execute_query(query)
        deleted_count = 0
        
        if result and 'orders' in result:
            for order in result['orders']['edges']:
                try:
                    order_id = order['node']['id']
                    print(f"Processing order: {order_id}")
                    print(f"Status - Financial: {order['node']['displayFinancialStatus']}, Fulfillment: {order['node']['displayFulfillmentStatus']}")
                    
                    # Cancel the order
                    cancel_mutation = '''
                    mutation cancelOrder(
                        $orderId: ID!,
                        $reason: OrderCancelReason!,
                        $refund: Boolean!,
                        $restock: Boolean!,
                        $notifyCustomer: Boolean!,
                        $staffNote: String
                    ) {
                        orderCancel(
                            orderId: $orderId,
                            reason: $reason,
                            refund: $refund,
                            restock: $restock,
                            notifyCustomer: $notifyCustomer,
                            staffNote: $staffNote
                        ) {
                            job {
                                id
                            }
                            userErrors {
                                field
                                message
                            }
                        }
                    }
                    '''
                    
                    cancel_result = self.execute_query(cancel_mutation, variables={
                        "orderId": order_id,
                        "reason": "OTHER",
                        "refund": True,
                        "restock": True,
                        "notifyCustomer": False,
                        "staffNote": "Cancelled via Synthetic Data Generator"
                    })
                    
                    if cancel_result.get('orderCancel', {}).get('userErrors'):
                        errors = cancel_result['orderCancel']['userErrors']
                        error_messages = '; '.join(error.get('message', 'Unknown error') for error in errors)
                        print(f"Error cancelling order {order_id}: {error_messages}")
                        continue
                    
                    # Get the job ID and poll for completion
                    job_id = cancel_result['orderCancel']['job']['id']
                    print(f"Cancellation job started with ID: {job_id}")
                    
                    # Poll for job completion
                    job_query = '''
                    query getJob($id: ID!) {
                        job(id: $id) {
                            id
                            done
                        }
                    }
                    '''
                    
                    import time
                    max_attempts = 10
                    attempt = 0
                    
                    while attempt < max_attempts:
                        job_result = self.execute_query(job_query, variables={"id": job_id})
                        if job_result.get('job', {}).get('done'):
                            deleted_count += 1
                            print(f"Successfully cancelled order {order_id}")
                            break
                        
                        attempt += 1
                        if attempt < max_attempts:
                            time.sleep(1)  # Wait 1 second before polling again
                        else:
                            print(f"Timeout waiting for order {order_id} cancellation to complete")
                
                except Exception as e:
                    print(f"Error processing order {order_id}: {str(e)}")
                    continue
        
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