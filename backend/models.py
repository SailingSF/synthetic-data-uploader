"""
Simple data models for the synthetic data generator API.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class GenerationRequest(BaseModel):
    """Basic request structure for data generation."""
    shop_url: str
    access_token: str
    num_items: int = 10
    date_range_days: int = 30

class GenerationResponse(BaseModel):
    """Basic response structure for generated data."""
    message: str
    items: List[Dict[str, Any]]

class PreviewResponse(BaseModel):
    """Preview of generated data."""
    message: str
    sample_data: List[Dict[str, Any]]
    available_products: int 