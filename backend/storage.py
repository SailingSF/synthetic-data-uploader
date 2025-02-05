"""
Storage utilities for persisting generated data.
"""
from typing import Dict, Any, List
import json
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DataStorage:
    def __init__(self, base_dir: str = "data/generated"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def save_generated_data(
        self,
        data_type: str,
        data: List[Dict[str, Any]],
        shop_url: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Save generated data with metadata.
        
        Args:
            data_type: Type of data (e.g., 'orders', 'inventory')
            data: List of generated items
            shop_url: Shop URL for organization
            metadata: Additional metadata about the generation
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shop_dir = self.base_dir / shop_url.replace('.', '_')
        shop_dir.mkdir(exist_ok=True)
        
        filename = f"{data_type}_{timestamp}.json"
        filepath = shop_dir / filename
        
        # Prepare data with metadata
        save_data = {
            "type": data_type,
            "timestamp": timestamp,
            "shop_url": shop_url,
            "metadata": metadata or {},
            "data": data
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(save_data, f, indent=2)
            logger.info(f"Saved {len(data)} {data_type} to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")
            raise
            
    def get_recent_generations(
        self,
        data_type: str,
        shop_url: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get most recent generations for a shop and data type."""
        shop_dir = self.base_dir / shop_url.replace('.', '_')
        if not shop_dir.exists():
            return []
            
        files = sorted(
            [f for f in shop_dir.glob(f"{data_type}_*.json")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        results = []
        for file in files[:limit]:
            try:
                with open(file) as f:
                    results.append(json.load(f))
            except Exception as e:
                logger.error(f"Error reading {file}: {str(e)}")
                continue
                
        return results 