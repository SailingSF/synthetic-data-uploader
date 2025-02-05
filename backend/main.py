from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from generators.ai_generator import AIDataGenerator
from shopify_client import ShopifyGraphQLClient
from models import GenerationRequest, GenerationResponse, PreviewResponse
import shopify

# Load environment variables
load_dotenv()

app = FastAPI(title="Shopify Synthetic Data Generator")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize generator
ai_generator = AIDataGenerator()

def get_shopify_client(request: GenerationRequest) -> ShopifyGraphQLClient:
    """Create Shopify client from request."""
    try:
        shopify.Session.setup(
            api_key=os.getenv('SHOPIFY_API_KEY'),
            secret=os.getenv('SHOPIFY_API_SECRET')
        )
        return ShopifyGraphQLClient(request.shop_url, request.access_token)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Shopify session: {str(e)}"
        )

@app.post("/generate-orders", response_model=GenerationResponse)
async def generate_orders(request: GenerationRequest):
    """Generate and create synthetic orders."""
    client = get_shopify_client(request)
    
    # Fetch store products
    products = client.fetch_products()
    if not products:
        raise HTTPException(status_code=400, detail="No products found in store")
    
    # Generate orders
    generated_orders = ai_generator.generate_orders(
        store_products=products,
        count=request.num_items,
        date_range_days=request.date_range_days
    )
    
    # Create orders in Shopify
    created_orders = []
    failed_orders = []
    
    for order in generated_orders:
        try:
            # Debug: Print the order structure
            print("Generated order structure:", order)
            
            # Ensure line items are properly formatted
            if "lineItems" not in order:
                print("Warning: lineItems not found in order")
                continue
            
            result = client.create_regular_order(order)
            if result.get("draftOrder", {}).get("order"):
                order_details = result["draftOrder"]["order"]
                created_orders.append({
                    "id": order_details["id"],
                    "name": order_details["name"],
                    "email": order_details["customer"]["email"],
                    "total": order_details["totalPriceSet"]["shopMoney"]["amount"],
                    "status": {
                        "financial": order_details["displayFinancialStatus"],
                        "fulfillment": order_details["displayFulfillmentStatus"]
                    },
                    "items": len(order["lineItems"])
                })
            else:
                failed_orders.append({
                    "email": order["email"],
                    "items": len(order["lineItems"]),
                    "error": "Failed to complete draft order"
                })
        except Exception as e:
            print(f"Error creating order: {str(e)}")
            print(f"Order data: {order}")
            failed_orders.append({
                "email": order.get("email", "unknown"),
                "items": len(order.get("lineItems", [])),
                "error": str(e)
            })
            continue
    
    return GenerationResponse(
        message=f"Successfully created {len(created_orders)} orders, {len(failed_orders)} failed",
        items=created_orders,
        failed_items=failed_orders,
        success=len(created_orders) > 0
    )

@app.post("/generate-inventory", response_model=GenerationResponse)
async def generate_inventory(request: GenerationRequest):
    """Generate and apply inventory adjustments."""
    client = ShopifyGraphQLClient(request.shop_url, request.access_token)
    
    # Fetch store products
    products = client.fetch_products()
    if not products:
        raise HTTPException(status_code=400, detail="No products found in store")
    
    # Generate adjustments
    adjustments = ai_generator.generate_inventory_adjustments(
        store_products=products,
        count=request.num_items
    )
    
    # Apply adjustments
    applied = []
    failed = []
    location_id = client.get_location_id()
    
    for adj in adjustments:
        try:
            variant_id = f"gid://shopify/ProductVariant/{adj['variant_id']}"
            inventory_item_id = client.get_inventory_item_id(variant_id)
            
            result = client.adjust_inventory(
                inventory_item_id=inventory_item_id,
                location_id=location_id,
                delta=adj["adjustment"],
                reason=adj["reason"]
            )
            
            if result.get("inventoryAdjustQuantity", {}).get("inventoryLevel"):
                applied.append(adj)
            else:
                failed.append({
                    "variant_id": adj["variant_id"],
                    "error": "Failed to adjust inventory"
                })
        except Exception as e:
            print(f"Error applying adjustment: {e}")
            failed.append({
                "variant_id": adj["variant_id"],
                "error": str(e)
            })
            continue
    
    return GenerationResponse(
        message=f"Applied {len(applied)} inventory adjustments",
        items=applied,
        success=len(applied) > 0,
        failed_items=failed if failed else None
    )

@app.post("/preview", response_model=PreviewResponse)
async def preview_data(request: GenerationRequest):
    """Preview synthetic data without applying it."""
    client = ShopifyGraphQLClient(request.shop_url, request.access_token)
    
    # Fetch store products
    products = client.fetch_products()
    if not products:
        raise HTTPException(status_code=400, detail="No products found in store")
    
    # Generate sample data
    sample_orders = ai_generator.generate_orders(
        store_products=products,
        count=2
    )
    
    sample_adjustments = ai_generator.generate_inventory_adjustments(
        store_products=products,
        count=2
    )
    
    return PreviewResponse(
        message="Generated preview data",
        sample_data=sample_orders + sample_adjustments,
        available_products=len(products)
    )

@app.post("/clear-orders", response_model=GenerationResponse)
@app.delete("/clear-orders", response_model=GenerationResponse)
async def clear_synthetic_orders(request: GenerationRequest):
    """Delete all AI-generated orders."""
    try:
        print("Clear orders request:", request.dict())  # Log the incoming request
        client = get_shopify_client(request)
        
        # Log before deletion attempt
        print("Attempting to delete AI-generated orders...")
        result = client.delete_ai_generated_orders()
        print("Deletion result:", result)  # Log the result
        
        response = GenerationResponse(
            message=f"Successfully deleted {result['deleted_count']} AI-generated orders",
            items=[],
            success=True,
            failed_items=None
        )
        print("Sending response:", response.dict())  # Log the response
        return response
    except Exception as e:
        print(f"Error in clear_synthetic_orders: {str(e)}")  # Log any errors
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear orders: {str(e)}"
        )

@app.post("/reset-inventory", response_model=GenerationResponse)
async def reset_inventory(request: GenerationRequest):
    """Reset inventory levels to base level."""
    client = get_shopify_client(request)
    result = client.reset_inventory_levels()
    return GenerationResponse(
        message=f"Reset inventory for {result['adjusted_count']} variants",
        items=[],
        success=True,
        failed_items=None
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 