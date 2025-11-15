# LLM Adventure CLI

A command-line interface for interacting with the LLM Adventure API.

## Installation

1. Create a virtual environment and activate it:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Commands

1. **Check API Status:**
```bash
python adventure_cli.py status
```

2. **Get API Information:**
```bash
python adventure_cli.py info
```

3. **Interactive Mode:**
```bash
python adventure_cli.py interactive
```

4. **Custom API Requests:**
```bash
python adventure_cli.py request --endpoint "/health" --method GET
```

### Command Line Options

- `--api-url`: Specify a different API URL (default: http://127.0.0.1:5000)

Example:
```bash
python adventure_cli.py --api-url http://localhost:8080 status
```

### Interactive Mode Commands

Once in interactive mode, you can use:
- `status` - Check API status
- `info` - Get API information  
- `health` - Check health endpoint
- `welcome` - Get welcome message
- `help` - Show available commands
- `exit` - Exit interactive mode

## Environment Variables

Create a `.env` file in the CLI directory to set:
- `API_URL` - Base URL for the API (default: http://127.0.0.1:5000)

## Examples

1. **Quick status check:**
```bash
python adventure_cli.py status
```

2. **Use with different API URL:**
```bash
python adventure_cli.py --api-url http://production-api.com status
```

3. **Interactive session:**
```bash
python adventure_cli.py interactive
> status
> info
> exit
```