# Test Suite for Shopify Synthetic Data Generator

This test suite verifies the functionality of the FastAPI backend for generating synthetic Shopify data.

## Setup

1. Create a `.env` file in the `backend` directory with your test shop credentials:
```env
TEST_SHOP_URL=your-dev-store.myshopify.com
TEST_ACCESS_TOKEN=your_access_token
OPENAI_API_KEY=your_openai_api_key
SHOPIFY_API_KEY=your_shopify_api_key
SHOPIFY_API_SECRET=your_shopify_api_secret
```

2. Install test dependencies:
```bash
pip install pytest pytest-env httpx
```

## Running Tests

### Run all tests:
```bash
pytest
```

### Run specific test file:
```bash
pytest tests/test_main.py
```

### Run tests excluding slow tests:
```bash
pytest -m "not slow"
```

### Run tests with detailed output:
```bash
pytest -v
```

## Test Categories

1. **Basic Functionality Tests**
   - Health check endpoint
   - Preview data generation
   - Error handling

2. **Synthetic Data Generation Tests** (marked as slow)
   - Order generation
   - Inventory adjustment generation
   - AI-powered data generation

## Important Notes

1. Tests use real Shopify API calls and OpenAI API calls - ensure you have sufficient API quotas.
2. Use a development store for testing to avoid affecting production data.
3. Some tests are marked as "slow" due to API calls - use the `-m "not slow"` flag to skip them during development.
4. The test suite does not mock any external services to ensure full integration testing.

## Adding New Tests

When adding new tests:
1. Follow the existing pattern of using fixtures from `conftest.py`
2. Add appropriate markers for slow/resource-intensive tests
3. Include proper validation of response structures
4. Handle potential API rate limits

## Troubleshooting

1. **API Rate Limits**
   - If you hit Shopify API rate limits, wait a few minutes before retrying
   - Consider reducing the number of items generated in tests

2. **OpenAI API Issues**
   - Ensure your API key has sufficient credits
   - Check for any model-specific limitations

3. **Test Shop Access**
   - Verify your test shop credentials
   - Ensure the shop has at least some products for testing 