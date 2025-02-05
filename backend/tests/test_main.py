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