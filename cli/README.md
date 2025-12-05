# LLM Adventure CLI

Interactive command-line interface for the LLM Adventure world-building API.

## Features

- **Interactive menu system** - Easy navigation with numbered options
- **World management** - Create and select game worlds
- **World building** - Describe your world in natural language, LLM extracts locations and facts
- **Data viewing** - Browse locations and facts in formatted tables
- **Streaming chat** - Interactive conversations about your world with real-time responses
- **Session persistence** - Current world selection maintained throughout session

## Installation

### Using uv (Recommended - Fast!)

1. **Install dependencies:**
   ```bash
   cd cli
   uv sync
   ```

2. **Run the CLI:**
   ```bash
   uv run adventure_cli.py
   ```

### Using pip (Alternative)

1. **Install dependencies:**
   ```bash
   cd cli
   pip install -r requirements.txt
   ```

2. **Configure environment (optional):**
   ```bash
   cp .env.example .env
   # Edit .env if API is not at http://127.0.0.1:5000
   ```

3. **Ensure API server is running:**
   ```bash
   cd ../api
   python run.py
   ```

## Usage

Start the CLI:
```bash
python adventure_cli.py
```

Or make it executable (Unix/Linux/Mac):
```bash
chmod +x adventure_cli.py
./adventure_cli.py
```

## Workflow

### 1. Create a World

From the main menu, select **World Management → Create New World**:
- Enter a world name (required)
- Add optional description
- Optionally set as current world

### 2. Select a World

From the main menu, select **World Management → Select World**:
- Enter the world ID from when you created it
- Provide a display name for the menu header

### 3. Build Your World

With a world selected, choose **World Building**:
- Type or paste a natural language description of your world
- Press `Ctrl+D` (Unix) or `Ctrl+Z+Enter` (Windows) to finish
- LLM extracts locations and facts automatically
- Results display in formatted tables

**Example description:**
```
The capital city of Stromhaven lies in a valley between two mountain ranges.
It was founded 300 years ago and now has a population of 15,000.
The city is famous for its grand library.
South of the city, there's a small mining town called Ironforge nestled in the mountains.
```

### 4. View Your World

With a world selected, choose **View World Data**:
- **View Locations** - See all places in formatted table
- **View Facts** - See all extracted facts

### 5. Chat with Your World

With a world selected, choose **Chat with World**:
- Ask questions about your world
- Responses stream in real-time
- Chat history persists within session
- Type `exit` to return to main menu

## Configuration

Environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `http://127.0.0.1:5000` | API endpoint |
| `API_TIMEOUT` | `30` | Request timeout (seconds) |
| `STREAM_CHUNK_DISPLAY` | `true` | Show streaming chunks |
| `COLOR_THEME` | `default` | Terminal color theme |

## Menu Structure

```
Main Menu
├── 1. World Management
│   ├── Create New World
│   └── Select World
├── 2. World Building (requires world selection)
│   └── Describe World
├── 3. View World Data (requires world selection)
│   ├── View Locations
│   └── View Facts
├── 4. Chat with World (requires world selection)
│   └── Interactive chat loop
└── 5. Exit
```

## Examples

### Creating and Building a World

```
1. Main Menu → World Management → Create New World
   Name: Aethoria
   Description: A fantasy world of magic and mystery
   Set as current: y

2. Main Menu → World Building
   Description:
   There is a bustling port city called Seawatch on the eastern coast.
   It sits at the mouth of the Serpent River.
   The city has a population of 8,000 people and is controlled by the Merchant Guild.
   North of Seawatch, about two days travel, lies the ancient forest of Eldergrove.
   <Ctrl+D>

   Result: Created 2 locations and 5 facts

3. Main Menu → View World Data → View Locations
   (Shows table with Seawatch and Eldergrove)

4. Main Menu → Chat with World
   You: Tell me about Seawatch
   Assistant: Seawatch is a bustling port city...
```

## Troubleshooting

### Cannot connect to API
- Ensure API server is running: `cd ../api && python run.py`
- Check `API_BASE_URL` in `.env` matches server address
- Default API runs on `http://127.0.0.1:5000`

### Streaming not working
- Ensure API server supports streaming on `/chat/` endpoint
- Check network connectivity
- Try increasing `API_TIMEOUT` in `.env`

### World not found
- Select a world first via **World Management → Select World**
- Use the world ID displayed when you created it
- If you forgot the ID, check the API database or create a new world

### Multi-line input not working
- Unix/Linux/Mac: Press `Ctrl+D` to finish
- Windows: Press `Ctrl+Z` then `Enter` to finish
- Alternatively, type on a single line

### Import errors
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python version (3.8+ required)
- Try creating a virtual environment first

## Technical Details

**Architecture:**
- **httpx** - Async HTTP client with streaming
- **rich** - Terminal UI (tables, colors, formatting)
- **pydantic** - Data validation
- **python-dotenv** - Configuration management

**API Endpoints Used:**
- `POST /world-building/worlds` - Create world
- `POST /world-building/describe` - Add world content
- `GET /world-building/worlds/{id}/locations` - List locations
- `GET /world-building/worlds/{id}/facts` - List facts
- `POST /chat/` - Streaming chat

## Development

**File Structure:**
```
cli/
├── adventure_cli.py    # Main entry point
├── api_client.py       # HTTP client
├── display.py          # Terminal output
├── config.py           # Configuration
├── models.py           # Data models
├── state.py            # Session state
├── utils/
│   └── streaming.py    # Streaming handlers
├── requirements.txt
├── .env.example
└── README.md
```

**Adding Features:**
- New menu options → Add to `adventure_cli.py`
- New API endpoints → Add methods to `api_client.py`
- New display formats → Add functions to `display.py`

## License

Part of the LLM Adventure project.
