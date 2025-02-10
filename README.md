# Shopify Synthetic Data Generator

A Shopify app that generates realistic synthetic data for your store using AI. This tool helps developers and store owners create test data by generating realistic orders and inventory changes based on your existing products.

## Features

- 🤖 AI-powered data generation using OpenAI
- 📦 Creates realistic order patterns
- 📊 Generates inventory adjustments
- 🔄 Maintains data consistency with existing products
- 🎯 Perfect for testing and development environments

## Prerequisites

1. **Node.js**: [Download and install](https://nodejs.org/en/download/) version 18.20 or higher
2. **Python**: Version 3.8 or higher
3. **Shopify Partner Account**: [Create one here](https://partners.shopify.com/signup)
4. **Shopify CLI**: Install using npm:
   ```bash
   npm install -g @shopify/cli @shopify/theme
   ```
5. **OpenAI API Key**: [Get it here](https://platform.openai.com/api-keys)

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/shopify-synthetic-data-generator.git
   cd shopify-synthetic-data-generator
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the `backend` directory:
   ```env
   SHOPIFY_API_KEY=your_api_key
   SHOPIFY_API_SECRET=your_api_secret
   OPENAI_API_KEY=your_openai_api_key
   ```

5. Configure your Shopify app in the Partner Dashboard:
   - Create a new app
   - Set the App URL to your development URL (provided by Shopify CLI)
   - Configure the necessary scopes (read/write for products, orders, and inventory)

6. Link your local app to Shopify:
   ```bash
   npm run shopify app config link
   ```

## Running the App

1. Start the backend server:
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

2. In a new terminal, start the frontend:
   ```bash
   npm run dev
   ```

3. Press `p` in the terminal to open your app's URL

## Using the App

1. Install the app on your development store
2. Navigate to the app in your Shopify admin
3. Choose the type of data you want to generate:
   - Orders: Creates realistic customer orders
   - Inventory: Generates inventory adjustments
4. Configure generation parameters:
   - Number of items to generate
   - Date range for the data
5. Preview the data before generating
6. Confirm to create the synthetic data

## Development

The app consists of two main parts:
- Frontend: Built with Remix and Shopify App Bridge
- Backend: Python FastAPI server with AI integration

Key files:
```markdown:backend/main.py
startLine: 1
endLine: 10
```

```markdown:backend/generators/ai_generator.py
startLine: 1
endLine: 5
```

## Testing

Run backend tests:
```bash
cd backend
pytest
```

For frontend development, refer to the [Remix development guide](https://remix.run/docs/en/main/guides/development).

## Deployment

1. Deploy the backend to your preferred hosting service (e.g., Heroku, DigitalOcean)
2. Update the backend URL in your frontend configuration
3. Deploy the frontend using Shopify CLI:
   ```bash
   npm run deploy
   ```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Shopify App Template - Remix](https://github.com/Shopify/shopify-app-template-remix)
- Powered by OpenAI's GPT models
- Uses Shopify's Admin API

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.

## Security

Never commit your API keys or sensitive credentials. Always use environment variables for sensitive data.
