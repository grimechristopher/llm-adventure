# Setup Guide

## Prerequisites

1. PostgreSQL installed and running
2. Python 3.8+
3. (Optional) LM Studio running if using local LLM

## Database Setup

### Create PostgreSQL Database

```bash
# Login to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE llm_adventure;

# Exit
\q
```

### Run Database Migrations

The application uses Alembic for database migrations. After installing dependencies, run:

```bash
cd api

# Run all migrations to create tables
alembic upgrade head
```

This will:
1. Enable the PostGIS extension
2. Create the `worlds`, `locations`, and `facts` tables
3. Create the `chat_message_history` table (for chat functionality)

## Installation

### Using uv (Recommended - Fast!)

1. Install dependencies:

```bash
cd api
uv sync
```

### Using pip (Alternative)

1. Install dependencies:

```bash
cd api
pip install -r requirements.txt
```

2. Configure environment variables:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your actual values
# At minimum, set your PostgreSQL credentials
```

3. Run the application:

```bash
python run.py
```

## Testing the Streaming Chat

### Using curl (streaming):

```bash
curl -X POST http://127.0.0.1:5000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me a short story",
    "session_id": "user123"
  }' \
  --no-buffer
```


### Using Python requests:

```python
import requests

# Streaming
response = requests.post(
    'http://127.0.0.1:5000/chat/',
    json={
        'message': 'Tell me a story',
        'session_id': 'user123'
    },
    stream=True
)

for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
    if chunk:
        print(chunk, end='', flush=True)
```

## Testing World-Building Endpoints

### Create a World

```bash
curl -X POST http://127.0.0.1:5000/world-building/worlds \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Aethoria",
    "description": "A fantasy world of magic and mystery",
    "created_by_user": "testuser"
  }'
```

### Describe the World (LLM Extraction)

```bash
curl -X POST http://127.0.0.1:5000/world-building/describe \
  -H "Content-Type: application/json" \
  -d '{
    "world_id": 1,
    "description": "There is a bustling port city called Seawatch on the eastern coast. It sits at the mouth of the Serpent River. The city has a population of 8,000 people and is controlled by the Merchant Guild. North of Seawatch, about two days travel, lies the ancient forest of Eldergrove."
  }'
```

### Query Locations

```bash
curl http://127.0.0.1:5000/world-building/worlds/1/locations
```

### Query Facts

```bash
curl http://127.0.0.1:5000/world-building/worlds/1/facts
```

## Conversation History

- Each session_id maintains its own conversation history
- History is automatically saved to PostgreSQL after each exchange
- The LLM has access to previous messages in the conversation
- To start a fresh conversation, use a different session_id

## Database Migrations

### Create a New Migration

If you modify the database models, create a new migration:

```bash
cd api
alembic revision --autogenerate -m "description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migrations

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```
