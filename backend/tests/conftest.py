"""
Test configuration and shared fixtures.
"""
import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from dotenv import load_dotenv
import logging
import logging.handlers
import atexit
import shutil
import tempfile

# Configure logging with a more robust setup
def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # File handler with RotatingFileHandler
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'test.log',
        maxBytes=1024*1024,  # 1MB
        backupCount=3,
        delay=True
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Cleanup function to properly close handlers
    def cleanup():
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
    
    # Register cleanup
    atexit.register(cleanup)
    
    return root_logger

# Setup logging
logger = setup_logging()

# Add the backend directory to Python path
backend_dir = str(Path(__file__).parent.parent.absolute())
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load environment variables before importing app
load_dotenv()

# Verify required environment variables
REQUIRED_ENV_VARS = [
    "SHOPIFY_API_KEY",
    "SHOPIFY_API_SECRET",
    "TEST_SHOP_URL",
    "TEST_ACCESS_TOKEN",
    "OPENAI_API_KEY"
]

missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    logger.error("Please ensure all required variables are set in your .env file")
    raise RuntimeError(f"Missing environment variables: {', '.join(missing_vars)}")

# Now we can import from the backend package
try:
    from main import app
    logger.info("Successfully imported FastAPI app")
except Exception as e:
    logger.error(f"Error importing FastAPI app: {str(e)}")
    raise

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def shop_credentials():
    """Get Shopify credentials from environment variables."""
    shop_url = os.getenv("TEST_SHOP_URL")
    access_token = os.getenv("TEST_ACCESS_TOKEN")
    
    if not shop_url or not access_token:
        pytest.skip("Shopify test credentials not configured")
    
    # Log the shop URL (but not the access token for security)
    logger.info(f"Using test shop: {shop_url}")
    
    return {
        "shop_url": shop_url,
        "access_token": access_token
    }

@pytest.fixture(autouse=True)
def verify_env():
    """Automatically verify environment before each test."""
    # Verify Shopify API credentials
    if not all([
        os.getenv("SHOPIFY_API_KEY"),
        os.getenv("SHOPIFY_API_SECRET"),
        os.getenv("TEST_SHOP_URL"),
        os.getenv("TEST_ACCESS_TOKEN")
    ]):
        pytest.skip("Shopify credentials not properly configured")
    
    # Verify OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OpenAI API key not configured")

class TestClientWithLogging:
    """Enhanced test client with error logging."""
    def __init__(self, client):
        self.client = client
    
    def request(self, method, url, **kwargs):
        try:
            response = self.client.request(method, url, **kwargs)
            if response.status_code >= 400:
                logger.error(f"Request failed: {method} {url}")
                logger.error(f"Status code: {response.status_code}")
                logger.error(f"Response body: {response.text}")
            return response
        except Exception as e:
            logger.exception(f"Error during request {method} {url}: {str(e)}")
            raise
    
    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)
    
    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

@pytest.fixture
def test_client(client):
    """Fixture that provides an enhanced test client with logging."""
    return TestClientWithLogging(client)

@pytest.fixture
def test_client():
    """Create a test client."""
    from main import app
    return TestClient(app)

@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def valid_order_data():
    """Get valid order data for testing."""
    return {
        "created_at": "2024-03-14T12:00:00Z",
        "customer": {
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
            "default_address": {
                "address1": "123 Test St",
                "city": "Test City",
                "province_code": "ON",
                "zip": "12345",
                "country_code": "US",
                "phone": "123-456-7890"
            }
        },
        "line_items": [
            {
                "variant_id": 123,
                "product_id": 456,
                "title": "Test Product",
                "variant_title": "Test Variant",
                "quantity": 1,
                "price": 10.99,
                "sku": "TEST-123"
            }
        ],
        "total_price": 10.99,
        "financial_status": "paid",
        "fulfillment_status": "fulfilled",
        "shipping_address": {
            "address1": "123 Test St",
            "city": "Test City",
            "province_code": "ON",
            "zip": "12345",
            "country_code": "US",
            "phone": "123-456-7890"
        }
    }

@pytest.fixture
def valid_adjustment_data():
    """Get valid inventory adjustment data for testing."""
    return {
        "variant_id": 123,
        "product_id": 456,
        "adjustment": 5,
        "sku": "TEST-123",
        "reason": "received",
        "timestamp": "2024-03-14T12:00:00Z"
    } 