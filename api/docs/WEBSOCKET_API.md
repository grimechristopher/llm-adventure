# WebSocket API Specification

## Connection

**Endpoint:** `ws://localhost:5000/ws/conversations/{conversation_id}`

**Parameters:**
- `conversation_id` (UUID): Conversation identifier

**Connection Flow:**
1. Client initiates WebSocket connection
2. Server accepts and logs connection
3. Server sends welcome message: `{"type": "connected", "conversation_id": "..."}`
4. Client can now send messages

## Message Format

### Client → Server

**User Message:**
```json
{
  "type": "user_message",
  "content": "What's the weather in San Francisco?"
}
```

**Ping (Heartbeat):**
```json
{
  "type": "ping"
}
```

### Server → Client

**Token (Real-time Streaming):**
```json
{
  "type": "token",
  "content": "The",
  "timestamp": "2026-01-19T10:30:00Z"
}
```

**Tool Call Started:**
```json
{
  "type": "tool_call_start",
  "tool": "web_search",
  "args": {"query": "San Francisco weather"},
  "timestamp": "2026-01-19T10:30:00Z"
}
```

**Tool Call Result:**
```json
{
  "type": "tool_result",
  "tool": "web_search",
  "result": "Currently 65°F and sunny",
  "timestamp": "2026-01-19T10:30:01Z"
}
```

**Message Complete:**
```json
{
  "type": "done",
  "message_id": "msg_123",
  "timestamp": "2026-01-19T10:30:05Z"
}
```

**Error:**
```json
{
  "type": "error",
  "error": "Tool execution failed",
  "details": "Connection timeout to weather API",
  "timestamp": "2026-01-19T10:30:02Z"
}
```

**Pong (Heartbeat Response):**
```json
{
  "type": "pong",
  "timestamp": "2026-01-19T10:30:00Z"
}
```

## Conversation Flow Example

```
Client → {"type": "user_message", "content": "Search for Python tutorials"}
Server → {"type": "tool_call_start", "tool": "web_search", ...}
Server → {"type": "tool_result", "tool": "web_search", ...}
Server → {"type": "token", "content": "I"}
Server → {"type": "token", "content": " found"}
Server → {"type": "token", "content": " several"}
...
Server → {"type": "token", "content": " tutorials"}
Server → {"type": "done", "message_id": "msg_123"}
```

## Connection Management

**Heartbeat:**
- Server sends ping every 30 seconds
- Client should respond with pong
- Missing 3 consecutive pongs → Connection closed

**Reconnection:**
- Client can reconnect with same conversation_id
- Previous messages/state automatically loaded from checkpoints
- Conversation continues seamlessly

**Graceful Shutdown:**
```json
{
  "type": "disconnect",
  "reason": "Server shutting down",
  "timestamp": "2026-01-19T10:30:00Z"
}
```

## Error Handling

**Client-Side Errors:**
- Invalid JSON → Server sends error event
- Missing required fields → Server sends error event
- Unknown message type → Server logs warning, ignores

**Server-Side Errors:**
- LLM failure → Error event streamed, conversation state preserved
- Tool failure → Error event streamed, agent can retry
- Checkpoint save failure → Logged, state held in memory

**Network Errors:**
- Connection drop → Client reconnects, resume from checkpoint
- Timeout → Server closes connection after 5 minutes idle

## Rate Limiting

**Per Connection:**
- Max 10 messages per minute
- Max message size: 10KB

**Enforcement:**
- Exceeded → Error event: `{"type": "error", "error": "Rate limit exceeded"}`
- Connection remains open, client waits

## Testing

**Test Client Example (Python):**
```python
import asyncio
import websockets
import json

async def chat():
    uri = "ws://localhost:5000/ws/conversations/123e4567-e89b-12d3-a456-426614174000"

    async with websockets.connect(uri) as websocket:
        # Send message
        await websocket.send(json.dumps({
            "type": "user_message",
            "content": "Hello!"
        }))

        # Receive tokens
        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "token":
                print(data["content"], end="", flush=True)
            elif data["type"] == "done":
                print("\n[Done]")
                break

asyncio.run(chat())
```

**Test Client Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:5000/ws/conversations/123e4567-e89b-12d3-a456-426614174000');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'user_message',
    content: 'Hello!'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'token') {
    document.body.textContent += data.content;
  }
};
```
