"""
Tests for the FastAPI application endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

def test_health_check(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_preview_data(test_client, shop_credentials):
    """Test the preview data endpoint."""
    response = test_client.post(
        "/preview",
        json={
            "shop_url": shop_credentials["shop_url"],
            "access_token": shop_credentials["access_token"],
            "num_items": 2,
            "date_range_days": 30
        }
    )
    
    # Handle no products case
    if response.status_code == 400:
        assert "No products found" in response.json()["detail"]
        return
        
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "sample_data" in data
    assert "available_products" in data
    assert len(data["sample_data"]) > 0

def test_generate_orders(test_client, shop_credentials):
    """Test order generation endpoint."""
    response = test_client.post(
        "/generate-orders",
        json={
            "shop_url": shop_credentials["shop_url"],
            "access_token": shop_credentials["access_token"],
            "num_items": 2,
            "date_range_days": 7
        }
    )
    
    # Handle no products case
    if response.status_code == 400:
        assert "No products found" in response.json()["detail"]
        return
        
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "items" in data
    
    # Verify orders structure
    for order in data["items"]:
        assert "customer" in order
        assert "email" in order["customer"]
        assert "line_items" in order
        for item in order["line_items"]:
            assert "variant_id" in item
            assert "quantity" in item

def test_generate_inventory(test_client, shop_credentials):
    """Test inventory adjustment generation endpoint."""
    response = test_client.post(
        "/generate-inventory",
        json={
            "shop_url": shop_credentials["shop_url"],
            "access_token": shop_credentials["access_token"],
            "num_items": 2,
            "date_range_days": 30
        }
    )
    
    # Handle no products case
    if response.status_code == 400:
        assert "No products found" in response.json()["detail"]
        return
        
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "items" in data
    
    # Verify adjustments structure
    for adjustment in data["items"]:
        assert "variant_id" in adjustment
        assert "adjustment" in adjustment
        assert -5 <= adjustment["adjustment"] <= 10
        assert "reason" in adjustment
        assert adjustment["reason"] in ["recount", "received", "damaged", "sold"]

def test_error_handling(test_client):
    """Test error handling with invalid credentials."""
    response = test_client.post(
        "/generate-orders",
        json={
            "shop_url": "invalid-store.myshopify.com",
            "access_token": "invalid_token",
            "num_items": 1,
            "date_range_days": 30
        }
    )
    assert response.status_code in [400, 401, 403, 500]
    assert "detail" in response.json()

def test_clear_orders(test_client, shop_credentials):
    """Test clearing AI-generated orders."""
    # First create some orders
    create_response = test_client.post(
        "/generate-orders",
        json={
            "shop_url": shop_credentials["shop_url"],
            "access_token": shop_credentials["access_token"],
            "num_items": 2,
            "date_range_days": 7
        }
    )
    
    # Handle permission errors or no products case
    if create_response.status_code == 400:
        if "No products found" in create_response.json()["detail"]:
            pytest.skip("No products found in store")
        elif "Access denied" in create_response.json()["detail"]:
            pytest.skip("Test shop missing required permissions")
        return
    
    # Then clear them
    response = test_client.request(
        "DELETE",
        "/clear-orders",
        json={
            "shop_url": shop_credentials["shop_url"],
            "access_token": shop_credentials["access_token"],
            "num_items": 0,  # Not used but required by model
            "date_range_days": 0  # Not used but required by model
        }
    )
    
    # Handle permission errors for deletion
    if response.status_code == 400 and "Access denied" in response.json()["detail"]:
        pytest.skip("Test shop missing required permissions for deleting orders")
        
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "deleted_count" in data
    assert isinstance(data["deleted_count"], int)
    assert data["deleted_count"] >= 0

def test_reset_inventory(test_client, shop_credentials):
    """Test resetting inventory levels."""
    # First make some inventory adjustments
    test_client.post(
        "/generate-inventory",
        json={
            "shop_url": shop_credentials["shop_url"],
            "access_token": shop_credentials["access_token"],
            "num_items": 2,
            "date_range_days": 7
        }
    )
    
    # Then reset inventory
    response = test_client.post(
        "/reset-inventory",
        json={
            "shop_url": shop_credentials["shop_url"],
            "access_token": shop_credentials["access_token"],
            "num_items": 0,  # Not used but required by model
            "date_range_days": 0  # Not used but required by model
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "adjusted_count" in data
    assert isinstance(data["adjusted_count"], int)
    assert data["adjusted_count"] >= 0

def test_clear_orders_invalid_auth(test_client):
    """Test clear orders with invalid credentials."""
    response = test_client.request(
        "DELETE",
        "/clear-orders",
        json={
            "shop_url": "invalid-store.myshopify.com",
            "access_token": "invalid_token",
            "num_items": 0,
            "date_range_days": 0
        }
    )
    assert response.status_code in [400, 401, 403, 500]
    assert "detail" in response.json()

def test_reset_inventory_invalid_auth(test_client):
    """Test reset inventory with invalid credentials."""
    response = test_client.post(
        "/reset-inventory",
        json={
            "shop_url": "invalid-store.myshopify.com",
            "access_token": "invalid_token",
            "num_items": 0,
            "date_range_days": 0
        }
    )
    assert response.status_code in [400, 401, 403, 500]
    assert "detail" in response.json()