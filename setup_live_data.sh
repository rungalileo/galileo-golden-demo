#!/bin/bash

# Setup script for live stock data

echo "=================================="
echo "Live Stock Data Setup"
echo "=================================="
echo

# Check if in venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Recommended: source venv/bin/activate"
    echo
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install dependencies
echo "📦 Installing required packages..."
pip install yfinance alpha-vantage requests

echo
echo "✅ Dependencies installed!"
echo

# Check for secrets file
SECRETS_FILE=".streamlit/secrets.toml"

if [ ! -f "$SECRETS_FILE" ]; then
    echo "⚠️  Secrets file not found: $SECRETS_FILE"
    echo "   Creating from template..."
    mkdir -p .streamlit
    cp .streamlit/secrets.toml.template "$SECRETS_FILE" 2>/dev/null || touch "$SECRETS_FILE"
fi

# Prompt for setup method
echo "Choose setup method:"
echo "1. Quick Start (Yahoo Finance - No API key needed)"
echo "2. Full Setup (Alpha Vantage - Get API key)"
echo "3. Skip configuration"
echo
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo
        echo "🚀 Setting up Quick Start (Yahoo Finance)..."
        # Add USE_LIVE_DATA to secrets
        if grep -q "USE_LIVE_DATA" "$SECRETS_FILE"; then
            sed -i '' 's/USE_LIVE_DATA = .*/USE_LIVE_DATA = "true"/' "$SECRETS_FILE"
        else
            echo 'USE_LIVE_DATA = "true"' >> "$SECRETS_FILE"
        fi
        echo "✅ Live data enabled!"
        echo
        echo "No API key needed for Yahoo Finance."
        echo "You're ready to go!"
        ;;
        
    2)
        echo
        echo "📝 Full Setup (Alpha Vantage)"
        echo
        echo "1. Get your free API key: https://www.alphavantage.co/support/#api-key"
        echo "2. Enter it below"
        echo
        read -p "Alpha Vantage API Key: " api_key
        
        if [ -z "$api_key" ]; then
            echo "❌ No API key provided"
            exit 1
        fi
        
        # Add to secrets
        if grep -q "ALPHA_VANTAGE_API_KEY" "$SECRETS_FILE"; then
            sed -i '' "s/ALPHA_VANTAGE_API_KEY = .*/ALPHA_VANTAGE_API_KEY = \"$api_key\"/" "$SECRETS_FILE"
        else
            echo "ALPHA_VANTAGE_API_KEY = \"$api_key\"" >> "$SECRETS_FILE"
        fi
        
        if grep -q "USE_LIVE_DATA" "$SECRETS_FILE"; then
            sed -i '' 's/USE_LIVE_DATA = .*/USE_LIVE_DATA = "true"/' "$SECRETS_FILE"
        else
            echo 'USE_LIVE_DATA = "true"' >> "$SECRETS_FILE"
        fi
        
        echo
        echo "✅ Alpha Vantage configured!"
        echo "✅ Live data enabled!"
        ;;
        
    3)
        echo "Skipping configuration."
        ;;
        
    *)
        echo "Invalid choice."
        exit 1
        ;;
esac

echo
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo
echo "📋 Next steps:"
echo "   1. Start the app: streamlit run app.py"
echo "   2. Go to Chat tab"
echo "   3. Ask: 'What's the current price of AAPL?'"
echo "   4. Should return real-time data!"
echo
echo "📚 Documentation: LIVE_DATA_SETUP.md"
echo

