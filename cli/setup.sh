#!/bin/bash

# Setup script for LLM Adventure CLI

echo "Setting up LLM Adventure CLI..."

# Check if we're in the right directory
if [ ! -f "adventure_cli.py" ]; then
    echo "Error: Please run this script from the cli directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete! 🎉"
echo ""
echo "To use the CLI:"
echo "1. Activate the virtual environment: source .venv/bin/activate"
echo "2. Run the CLI: python adventure_cli.py --help"
echo "3. Try: python adventure_cli.py status"
echo ""
echo "Make sure your API server is running first!"